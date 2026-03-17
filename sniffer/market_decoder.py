import json
from datetime import datetime, timedelta

class MarketDecoder:
    """
    Декодер для рыночных данных Albion Online.
    Определяет тип пакета по его сигнатуре и возвращает структурированный результат.
    """

    @staticmethod
    def identify_response_type(parameters):
        """Определяет тип рыночных данных в ответе без привязки к OpCode."""
        p = {str(k): v for k, v in parameters.items()}
        
        # 1. Поиск предметов (Search Results)
        if "0" in p and isinstance(p["0"], list) and len(p["0"]) > 0:
            first_item = p["0"][0]
            if isinstance(first_item, str) and (first_item.startswith('{"Id"') or first_item.startswith('{"UniqueName"')):
                return "search_results"

        # 2. История цен (Market History Graph)
        if "0" in p and "1" in p and isinstance(p["0"], list) and isinstance(p["1"], list):
            if len(p["0"]) == len(p["1"]) and len(p["0"]) > 0:
                # В истории цен обычно список чисел
                if isinstance(p["0"][0], (int, float)):
                    return "market_history"

        # 3. Рынок Золота (Gold Market)
        if "0" in p and "1" in p and "2" in p and "3" in p:
            if not isinstance(p["0"], list) and all(isinstance(p.get(k), (int, float)) for k in ["0", "1", "2", "3"]):
                return "gold_market"
        
        return None

    @staticmethod
    def identify_request_type(parameters):
        """Определяет тип рыночного запроса без привязки к OpCode."""
        p = {str(k): v for k, v in parameters.items()}
        # Запросы на поиск: 1 - категория (строка), 2 - подкатегория (строка)
        if "1" in p and "2" in p and isinstance(p["1"], str) and isinstance(p["2"], str):
             # Дополнительная проверка на пустые строки или null, характерные для маркета
             return "search_request"
        return None

    @staticmethod
    def decode_response(parameters, data_type=None):
        """Декодирует ответ, если тип данных уже известен или распознан."""
        p = {str(k): v for k, v in parameters.items()}
        
        target_type = data_type or MarketDecoder.identify_response_type(parameters)
        
        if target_type == "search_results":
            return MarketDecoder._parse_search_results(p["0"])
        elif target_type == "market_history":
            return MarketDecoder._parse_history(p["0"], p["1"])
        elif target_type == "gold_market":
            return MarketDecoder._parse_gold_market(p)
            
        return None

    @staticmethod
    def _parse_search_results(json_list):
        items = []
        for item_str in json_list:
            try:
                data = json.loads(item_str)
                # Нормализация цен
                if "UnitPriceSilver" in data:
                    data["UnitPriceSilver"] = data["UnitPriceSilver"] / 10000
                if "TotalPriceSilver" in data:
                    data["TotalPriceSilver"] = data["TotalPriceSilver"] / 10000
                items.append(data)
            except:
                continue
        return {"type": "search_results", "data": items}

    @staticmethod
    def _parse_history(prices, ticks):
        history = []
        for price, tick in zip(prices, ticks):
            # Конвертация Ticks в Datetime (Albion использует .NET Ticks: 100ns от 0001-01-01)
            # Приближенная формула: (ticks - 621355968000000000) / 10000000 -> Unix timestamp
            try:
                dt = datetime(1, 1, 1) + timedelta(microseconds=tick // 10)
                history.append({
                    "price": price / 10000,
                    "timestamp": dt.isoformat()
                })
            except:
                history.append({"price": price / 10000, "tick": tick})
        return {"type": "market_history", "data": history}

    @staticmethod
    def _parse_gold_market(params):
        return {
            "type": "gold_market",
            "data": {
                "buy_price": params.get("0", 0) / 10000,
                "sell_price": params.get("2", 0) / 10000,
                "volume": params.get("1", 0)
            }
        }

    @staticmethod
    def decode_request(parameters):
        """Декодирует запросы пользователя (фильтры поиска)"""
        p = {str(k): v for k, v in parameters.items()}
        
        if MarketDecoder.identify_request_type(parameters) == "search_request":
            return {
                "type": "search_request",
                "filters": {
                    "category": p.get("1"),
                    "subcategory": p.get("2"),
                    "tier": p.get("7"),
                    "enchantment": p.get("10"),
                    "quality": p.get("11")
                }
            }
        return None
