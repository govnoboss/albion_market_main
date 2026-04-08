import pydivert
import sys
import json
import os
from datetime import datetime

# Добавляем путь к склонированной библиотеке, чтобы Python ее нашел
sys.path.insert(0, 'sniffer/photon-packet-parser')
from photon_packet_parser import PhotonPacketParser

from market_decoder import MarketDecoder
from market_db import MarketDB
from items_lookup import get_item_name

# Порт серверов Albion Online, по которому шлются игровые данные
ALBION_PORT = 5056
packet_count = 0
last_item_id = None # Для привязки графика истории к предмету

# Инициализация БД
db = MarketDB()

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

DUMP_UNKNOWN = False # Сохранять нераспознанные пакеты (в т.ч. для поиска новых OpCode)
TARGET_OPCODES = [] # Оставьте пустым для всех OpCode, или укажите нужные (например, [1])

class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        return super().default(obj)

def save_packet_log(packet_type, code, params):
    if TARGET_OPCODES and code not in TARGET_OPCODES:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = os.path.join(LOG_DIR, f"{packet_type}_{code}_{timestamp}.json")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "type": packet_type,
                "code": code,
                "params": params
            }, f, ensure_ascii=False, indent=4, cls=BytesEncoder)
    except Exception as e:
        pass

def print_market_data(decoded):
    if not decoded:
        return

    data_type = decoded["type"]
    data = decoded["data"]

    if data_type == "search_results":
        print(f"\n[РЫНОК] Обнаружены данные: {len(data)} строк")
        print(f"{'Предмет':<30} | {'Цена':<12} | {'Кол-во':<8}")
        print("-" * 60)
        # Показываем первые 10 для наглядности
        for item in data[:10]:
            raw_id = item.get('ItemTypeId', 'Unknown')
            name = get_item_name(raw_id, "ru") 
            # Ограничиваем длину названия для красивой таблицы
            if len(name) > 28:
                name = name[:25] + "..."
                
            price = item.get('UnitPriceSilver', 0)
            amount = item.get('Amount', 0)
            print(f"{name:<30} | {price:>12,.0f} | {amount:>8}")
        if len(data) > 10:
            print(f"... и еще {len(data)-10} строк")

    elif data_type == "market_history":
        print(f"\n[ИСТОРИЯ] Получен график цен ({len(data)} точек)")
        if data:
            print(f"   Последняя точка: {data[-1]['price']:,.0f} Silver | {data[-1]['timestamp']}")

    elif data_type == "gold_market":
        print(f"\n[ЗОЛОТО] Покупка: {data['buy_price']:,.0f} | Продажа: {data['sell_price']:,.0f}")

# Коллбеки для парсера Photon
def on_event(payload):
    global packet_count
    packet_count += 1
    if packet_count % 100 == 0:
        print(f"[*] Обработано {packet_count} сетевых пакетов...", end='\r')
        
    if DUMP_UNKNOWN:
        code = payload.code
        params = payload.parameters
        # Логируем события отдельно, так как у них свои OpCode (EventCodes)
        save_packet_log("EVENT", code, params)

def on_request(payload):
    global last_item_id
    code = payload.operation_code
    params = payload.parameters
    
    # 1. Сначала проверяем, не является ли это запросом клиента (фильтры)
    decoded_req = MarketDecoder.decode_request(code, params)
    if decoded_req:
         cat = decoded_req['filters'].get('category')
         last_item_id = cat
         cat_name = get_item_name(cat, "ru") if cat else ""
         print(f"\n[ЗАПРОС] Поиск категории: {cat_name} ({cat}) Tier {decoded_req['filters'].get('tier')}")
         return

    # 2. Парсер Photon мог перепутать направление (клиент/сервер), поэтому
    # пытаемся расшифровать данные как ОТВЕТ от сервера (сами рыночные списки/история).
    decoded_res = MarketDecoder.decode_response(code, params)
    if decoded_res:
        print_market_data(decoded_res)
        try:
            if decoded_res["type"] == "search_results":
                db.save_orders(decoded_res["data"])
            elif decoded_res["type"] == "market_history":
                db.save_history(last_item_id or "Unknown", decoded_res["data"])
            elif decoded_res["type"] == "gold_market":
                db.save_gold(decoded_res["data"])
        except Exception as e:
            print(f"[!] Ошибка записи в БД: {e}")
        return

    # 3. Если ничего не подошло - сохраняем пакет как неизвестный
    if DUMP_UNKNOWN:
        save_packet_log("REQUEST", code, params)

def on_response(payload):
    code = payload.operation_code
    params = payload.parameters
    
    # Пытаемся декодировать рыночные данные
    decoded = MarketDecoder.decode_response(code, params)
    if decoded:
        print_market_data(decoded)
        
        # Сохранение в базу данных
        try:
            if decoded["type"] == "search_results":
                db.save_orders(decoded["data"])
            elif decoded["type"] == "market_history":
                db.save_history(last_item_id or "Unknown", decoded["data"])
            elif decoded["type"] == "gold_market":
                db.save_gold(decoded["data"])
        except Exception as e:
            print(f"[!] Ошибка записи в БД: {e}")
            
    else:
        if DUMP_UNKNOWN:
            save_packet_log("RESPONSE", code, params)
            
        if code == 1:
            # ВРЕМЕННЫЙ ДЕБАГ: ловим пакеты, которые не распознал декодер
            # print(f"\n[DEBUG] Поймали OpCode 1, но декодер не узнал сигнатуру. Параметров: {len(params)}")
            pass



def main():
    print(f"[*] Запуск Сниффера-Исследователя (WinDivert)...")
    print(f"[*] Отслеживаем порт {ALBION_PORT} | Нажмите Ctrl+C для выхода")
    print("-" * 60)

    parser = PhotonPacketParser(on_event, on_request, on_response)

    try:
        # Отслеживаем и входящие (SrcPort), и исходящие (DstPort) пакеты
        with pydivert.WinDivert(f"udp and (udp.SrcPort == {ALBION_PORT} or udp.DstPort == {ALBION_PORT})", 
                                layer=pydivert.Layer.NETWORK, 
                                flags=pydivert.Flag.SNIFF) as w:
            for packet in w:

                parser.HandlePayload(packet.payload)
                
    except PermissionError:
        print("[ОШИБКА] Нужны права АДМИНИСТРАТОРА!")
        sys.exit(1)
    except Exception as e:
        print(f"[ОШИБКА]: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
