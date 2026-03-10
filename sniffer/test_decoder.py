import os
import json
import sys

# Добавляем текущую директорию в путь, чтобы импортировать MarketDecoder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sniffer.market_decoder import MarketDecoder

def test_decoder():
    logs_dir = "sniffer/logs"
    if not os.path.exists(logs_dir):
        print("Папка с логами не найдена!")
        return

    print("=== ТЕСТИРОВАНИЕ ДЕКОДЕРА ===")
    
    files = [f for f in os.listdir(logs_dir) if f.startswith("RESPONSE_1") or f.startswith("REQUEST_1")]
    
    for filename in files[:20]: # Тестируем первые 20 файлов
        path = os.path.join(logs_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            packet = json.load(f)
            code = packet["code"]
            params = packet["params"]
            
            if packet["type"] == "RESPONSE":
                decoded = MarketDecoder.decode_response(code, params)
            else:
                decoded = MarketDecoder.decode_request(code, params)
                
            if decoded:
                print(f"[OK] {filename}: {decoded['type']}")
                if decoded['type'] == "search_results":
                    print(f"   Найдено {len(decoded['data'])} лотов")
            else:
                pass # Некоторые пакеты OpCode 1 могут быть не рыночными

if __name__ == "__main__":
    test_decoder()
