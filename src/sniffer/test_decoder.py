import os
import json
import sys

# Добавляем текущую директорию в путь, чтобы импортировать MarketDecoder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sniffer.market_decoder import MarketDecoder
from sniffer.items_lookup import get_item_name

def test_decoder():
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(logs_dir):
        print("Папка с логами не найдена!")
        return

    print("=== ТЕСТИРОВАНИЕ ДЕКОДЕРА ===")
    
    files = [f for f in os.listdir(logs_dir) if f.startswith("RESPONSE_") or f.startswith("REQUEST_") or f.startswith("EVENT_")]
    
    for filename in files[:20]: # Тестируем первые 20 файлов
        path = os.path.join(logs_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            packet = json.load(f)
            code = packet["code"]
            params = packet["params"]
            
            # Восстанавливаем целочисленные ключи
            def fix_keys(obj):
                if isinstance(obj, dict):
                    return {int(k) if isinstance(k, str) and (k.isdigit() or (k.startswith('-') and k[1:].isdigit())) else k: fix_keys(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [fix_keys(i) for i in obj]
                return obj
            
            params = fix_keys(params)
            
            if packet["type"] == "RESPONSE":
                decoded = MarketDecoder.decode_response(code, params)
            elif packet["type"] == "REQUEST":
                decoded = MarketDecoder.decode_request(code, params)
                if not decoded:
                    # Fallback для криво размеченных парсером реквестов
                    decoded = MarketDecoder.decode_response(code, params)
            else:
                decoded = None # Декодер пока не умеет в Events
                
            if decoded:
                print(f"[OK] {filename}: {decoded['type']}")
                if decoded['type'] == "search_results":
                    print(f"   Найдено {len(decoded['data'])} лотов")
                    for item in decoded['data'][:3]:
                        raw_id = item.get('ItemTypeId', 'Unknown')
                        print(f"      - {get_item_name(raw_id)} ({raw_id}) : {item.get('UnitPriceSilver', 0):,.0f} silver")
            else:
                print(f"[-] {filename}: Не удалось декодировать")

if __name__ == "__main__":
    test_decoder()
