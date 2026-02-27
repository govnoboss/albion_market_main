"""
Управление локализацией приложения
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from .logger import get_logger
from .paths import get_app_root

logger = get_logger()

class LocalizationManager:
    """Менеджер для работы с переводами (Singleton)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.locales_dir = get_app_root() / "resources" / "locales"
        self.current_language = "en"
        self.translations: Dict[str, str] = {}
        self._initialized = True
        self.load_language(self.current_language)

    def load_language(self, lang_code: str):
        """Загрузка файла перевода"""
        file_path = self.locales_dir / f"{lang_code}.json"
        
        # Если файла нет, попробуем английский как запасной
        if not file_path.exists():
            logger.warning(f"Locale file not found: {file_path}. Falling back to 'en'.")
            file_path = self.locales_dir / "en.json"
            lang_code = "en"

        if not file_path.exists():
            logger.error(f"Fallback locale file 'en.json' not found in {self.locales_dir}")
            self.translations = {}
            self.current_language = lang_code
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
            self.current_language = lang_code
            logger.info(f"Loaded language: {lang_code}")
        except Exception as e:
            logger.error(f"Failed to load translations from {file_path}: {e}")
            self.translations = {}

    def get_text(self, key: str, default: Optional[str] = None) -> str:
        """Получить переведенный текст по ключу"""
        return self.translations.get(key, default if default is not None else key)

    def set_language(self, lang_code: str):
        """Смена языка"""
        if self.current_language != lang_code:
            self.load_language(lang_code)

# Глобальный экземпляр
_loc_manager = LocalizationManager()

def get_text(key: str, default: Optional[str] = None) -> str:
    """Удобная обертка для получения текста"""
    return _loc_manager.get_text(key, default)

def set_language(lang_code: str):
    """Удобная обертка для смены языка"""
    _loc_manager.set_language(lang_code)

def get_current_language() -> str:
    """Получить текущий код языка"""
    return _loc_manager.current_language
