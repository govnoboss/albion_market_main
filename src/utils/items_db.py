"""
База данных предметов Albion Online (локализованная)
"""

# === РУССКИЕ НАЗВАНИЯ (оригинал) ===
_ITEMS_RU = [
    "Шлем Солдата",
    "Шлем Хранителя",
    "Шлем Рыцаря",
    "Капюшон Охотника",
    "Капюшон Убийцы",
    "Капюшон Наемника",
    "Колпак Ученого",
    "Колпак Клирика",
    "Колпак Чародея",
    "Броня Солдата",
    "Броня Хранителя",
    "Броня Рыцаря",
    "Куртка Наемника",
    "Куртка Охотника",
    "Куртка Убийцы",
    "Мантия Ученого",
    "Мантия Клирика",
    "Мантия Чародея",
    "Сапоги Солдата",
    "Сапоги Рыцаря",
    "Сапоги Хранителя",
    "Ботинки Наемника",
    "Ботинки Охотника",
    "Ботинки Убийцы",
    "Сандалии Ученого",
    "Сандалии Клирика",
    "Сандалии Чародея",
    "Лук",
    "Боевой Лук",
    "Длинный Лук",
    "Арбалет",
    "Тяжелый Арбалет",
    "Легкий Арбалет",
    "Боевой Топор",
    "Большой Топор",
    "Алебарда",
    "Кинжал",
    "Парные Кинжалы",
    "Когти",
    "Молот",
    "Чекан",
    "Большой Молот",
    "Перчатки Крушителя",
    "Боевые Наручи",
    "Шипастые Рукавицы",
    "Булава",
    "Тяжелая Булава",
    "Моргенштерн",
    "Боевой Шест",
    "Железный Посох",
    "Острый Шест",
    "Копье",
    "Пика",
    "Глефа",
    "Палаш",
    "Клеймор",
    "Парные Мечи",
    "Мистический Посох",
    "Большой Мистический Посох",
    "Загадочный Посох",
    "Проклятый Посох",
    "Большой Проклятый Посох",
    "Демонический Посох",
    "Огненный Посох",
    "Большой Огненный Посох",
    "Адский Посох",
    "Морозный Посох",
    "Большой Морозный Посох",
    "Ледяной Посох",
    "Священный Посох",
    "Большой Священный Посох",
    "Божественный Посох",
    "Древесный Посох",
    "Большой Древесный Посох",
    "Дикий Посох",
    "Авалонский Плащ",
    "Плащ Морганы",
    "Плащ Хранителей",
    "Плащ Еретиков",
    "Плащ Демонов",
    "Плащ Нежити",
    "Плащ Города Brecilien",
    "Плащ Города Caerleon",
    "Накидка Города Bridgewatch",
    "Накидка Города Lymhurst",
    "Накидка Города Fort Sterling",
    "Накидка Города Martlock",
    "Накидка Города Thetford",
    "Сумка",
    "Кошель интуиции",
    "Плащ"
]

# === АНГЛИЙСКИЕ НАЗВАНИЯ (официальные из игры) ===
_ITEMS_EN = [
    "Soldier Helmet",
    "Guardian Helmet",
    "Knight Helmet",
    "Hunter Hood",
    "Assassin Hood",
    "Mercenary Hood",
    "Scholar Cowl",
    "Cleric Cowl",
    "Mage Cowl",
    "Soldier Armor",
    "Guardian Armor",
    "Knight Armor",
    "Mercenary Jacket",
    "Hunter Jacket",
    "Assassin Jacket",
    "Scholar Robe",
    "Cleric Robe",
    "Mage Robe",
    "Soldier Boots",
    "Knight Boots",
    "Guardian Boots",
    "Mercenary Shoes",
    "Hunter Shoes",
    "Assassin Shoes",
    "Scholar Sandals",
    "Cleric Sandals",
    "Mage Sandals",
    "Bow",
    "Warbow",
    "Longbow",
    "Crossbow",
    "Heavy Crossbow",
    "Light Crossbow",
    "Battleaxe",
    "Greataxe",
    "Halberd",
    "Dagger",
    "Dagger Pair",
    "Claws",
    "Hammer",
    "Polehammer",
    "Great Hammer",
    "Brawler Gloves",
    "Battle Bracers",
    "Spiked Gauntlets",
    "Mace",
    "Heavy Mace",
    "Morning Star",
    "Quarterstaff",
    "Iron-clad Staff",
    "Double Bladed Staff",
    "Spear",
    "Pike",
    "Glaive",
    "Broadsword",
    "Claymore",
    "Dual Swords",
    "Arcane Staff",
    "Great Arcane Staff",
    "Enigmatic Staff",
    "Cursed Staff",
    "Great Cursed Staff",
    "Demonic Staff",
    "Fire Staff",
    "Great Fire Staff",
    "Infernal Staff",
    "Frost Staff",
    "Great Frost Staff",
    "Glacial Staff",
    "Holy Staff",
    "Great Holy Staff",
    "Divine Staff",
    "Nature Staff",
    "Great Nature Staff",
    "Wild Staff",
    "Avalonian Cape",
    "Morgana Cape",
    "Keeper Cape",
    "Heretic Cape",
    "Demon Cape",
    "Undead Cape",
    "Brecilien Cape",
    "Caerleon Cape",
    "Bridgewatch Cape",
    "Lymhurst Cape",
    "Fort Sterling Cape",
    "Martlock Cape",
    "Thetford Cape",
    "Bag",
    "Satchel of Inside",
    "Cape"
]


def get_game_language() -> str:
    """Получить язык игры из конфига (не путать с языком интерфейса бота)"""
    try:
        from .config import get_config
        return get_config().get_setting("game_language", "ru")
    except Exception:
        return "ru"


def get_default_items() -> list:
    """Возвращает список предметов по умолчанию для текущего языка ИГРЫ"""
    lang = get_game_language()
    if lang == "en":
        return list(_ITEMS_EN)
    return list(_ITEMS_RU)


# === Таблицы перевода (строятся автоматически из параллельных списков) ===
_RU_TO_EN = dict(zip(_ITEMS_RU, _ITEMS_EN))
_EN_TO_RU = dict(zip(_ITEMS_EN, _ITEMS_RU))

# Дополнительные предметы из исключений, которых нет в основном списке
_EXTRA_TRANSLATIONS = {
    "Книга заклинаний": "Tome of Spells",
    "Щит": "Shield",
    "Факел": "Torch",
    "Боевой посох": "Battle Staff",
    "Посох бродяги": "Wanderlust",
}
for ru, en in _EXTRA_TRANSLATIONS.items():
    _RU_TO_EN[ru] = en
    _EN_TO_RU[en] = ru

# Lowercase версии для надежности
_RU_TO_EN_LOWER = {k.lower(): v for k, v in _RU_TO_EN.items()}
_EN_TO_RU_LOWER = {k.lower(): v for k, v in _EN_TO_RU.items()}


def translate_item(name: str, to_lang: str) -> str:
    """
    Перевести название предмета на указанный язык.
    Обрабатывает суффикс (знаток) для исключений.
    Если перевод не найден, возвращает оригинал.
    """
    original = name.strip()
    name_lower = original.lower()
    
    # Обработка суффикса "(знаток)" (RU -> EN)
    suffix = ""
    base_name = name_lower
    if "(знаток)" in name_lower:
        base_name = name_lower.replace("(знаток)", "").strip()
        suffix = " (знаток)" if to_lang == "ru" else ""  # При переводе на EN убираем суффикс
    
    if to_lang == "en":
        result = _RU_TO_EN_LOWER.get(base_name)
        if result:
            return result + suffix
        return original
    else:
        result = _EN_TO_RU_LOWER.get(base_name)
        if result:
            return result + suffix
        return original


def translate_items_list(items: list, to_lang: str) -> list:
    """Перевести список предметов на указанный язык"""
    return [translate_item(item, to_lang) for item in items]


# Обратная совместимость
DEFAULT_ITEMS = _ITEMS_RU
