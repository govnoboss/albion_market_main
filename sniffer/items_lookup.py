import os
import json

class ItemLookup:
    _items_dict = {}
    _loaded = False
    
    @classmethod
    def load(cls):
        if cls._loaded:
            return
            
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for item in data:
                unique_name = item.get("UniqueName")
                if unique_name:
                    locales = item.get("LocalizedNames")
                    
                    if isinstance(locales, dict):
                        en_name = locales.get("EN-US", unique_name)
                        ru_name = locales.get("RU-RU", en_name)
                    else:
                        en_name = unique_name
                        ru_name = unique_name
                    
                    # Store both fallback variations just in case
                    cls._items_dict[unique_name] = {
                        "en": en_name,
                        "ru": ru_name
                    }
            cls._loaded = True
        except FileNotFoundError:
            print(f"[!] Файл {json_path} не найден! Названия будут на английском (ID). Выполните закчаку items.json")
        except Exception as e:
            print(f"[!] Ошибка загрузки items.json: {e}")

    @classmethod
    def get_name(cls, unique_name, lang="ru"):
        cls.load()
        
        # 1. Пробуем найти полное имя (для ресурсов типа T4_ROCK_LEVEL1@1 это важно)
        if unique_name in cls._items_dict:
            return cls._items_dict[unique_name].get(lang, unique_name)

        # 2. Если не нашли, пробуем отрезать зачарование (для оружия/брони типа T4_ARMOR@1)
        base_name = unique_name
        suffix = ""
        if "@" in base_name:
            parts = base_name.split("@")
            base_name = parts[0]
            suffix = f" .{parts[1]}" # Заменяем @ на точку для визуальной привычности (.1, .2)
            
        if base_name in cls._items_dict:
            return f"{cls._items_dict[base_name].get(lang, base_name)}{suffix}"
            
        return f"{unique_name}"
        
# Глобальный метод для удобства
def get_item_name(unique_name, lang="ru"):
    return ItemLookup.get_name(unique_name, lang)

if __name__ == "__main__":
    print(get_item_name("T1_HIDE", "ru"))
    print(get_item_name("T4_ROCK", "ru"))
    print(get_item_name("T4_ROCK_LEVEL1@1", "ru"))
    print(get_item_name("T4_2H_CROSSBOW@1", "ru"))
