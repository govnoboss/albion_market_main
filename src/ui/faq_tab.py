"""
Вкладка FAQ и Гайда по Черному Рынку
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from .styles import PANEL_STYLE

class FAQTab(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet(PANEL_STYLE)
        
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        self._init_content()
        self.setWidget(self.content_widget)

    def _init_content(self):
        guide_text = """
        <h2 style='color: #f0f6fc;'>📖 Руководство пользователя</h2>

        <h3 style='color: #58a6ff;'>1. Основная настройка</h3>
        <p style='color: #c9d1d9;'>Первым делом необходимо настроить координаты кнопок и области распознавания текста (OCR) во вкладке <b>"Координаты"</b>:</p>
        <ul style='color: #c9d1d9; line-height: 1.6;'>
            <li><b>Калибровка предметов:</b> Настраивать координаты и области лучше всего на предмете <b>"Алебарда"</b> (Halberd) — это один из самых длинных предметов, он поможет лучше сориентироваться.</li>
            <li><b>Подсказки:</b> Нажмите на иконку <b>"?"</b> рядом с заголовком каждой категории координат, чтобы увидеть скриншот-пример правильного выделения.</li>
            <li><b>Точность клика:</b> Указывайте координату строго в <b>центре</b> кнопок, чтобы бот не промахивался при кликах.</li>
            <li><b>Области OCR (Текст):</b> Делайте выбор области названия предмета <b>с запасом</b> по ширине, чтобы захватывать полное имя даже у длинных названий.</li>
            <li><b>Области OCR (Числа):</b> Выделяйте только сами цифры <b>без иконки Серебра</b>, как показано в подсказках.</li>
        </ul>

        <p style='color: #c9d1d9;'>После настройки координат перейдите во вкладку <b>"Настройки"</b>:</p>
        <ul style='color: #c9d1d9; line-height: 1.6;'>
            <li><b>Калибровка меню:</b> Настройте параметры <b>"Высота строки"</b> и <b>"Смещение списка"</b>. При их изменении на экране появятся красные точки — это места, куда будет кликать бот. Настройте их так, чтобы точки находились точно в <b>центре</b> каждого Тира в выпадающем меню.</li>
            <li><b>Настройки мыши:</b> Эти параметры влияют на реалистичность и скорость работы. Крайне <b>не рекомендуется</b> выставлять моментальное перемещение мыши (телепорт), так как это повышает риск обнаружения.</li>
        </ul>

        <hr style='border: 0; border-top: 1px solid #30363d; margin: 20px 0;'>

        <h3 style='color: #58a6ff;'>2. Черный рынок (Black Market)</h3>
        <p style='color: #c9d1d9;'>Раздел для автоматизации массового сканирования и продажи:</p>
        <ul style='color: #c9d1d9; line-height: 1.6;'>
            <li><b>Принцип работы:</b> Вещи, которые нужно оценить, должны быть в инвентаре. Первые 48 предметов в списке базы данных (Scanner -> База и исключения -> База предметов) должны соответствовать вашему инвентарю.</li>
            <li><b>Автоматизация:</b> Как только бот просканирует последний предмет из инвентаря, он автоматически переключит персонажа (если включено в настройках) и продолжит работу.</li>
            <li><b>Подготовка:</b> Все ваши персонажи должны заранее находиться у NPC Черного Рынка.</li>
            <li><b>Лимиты:</b> Если "Смена персонажа" выключена, бот просто остановится после завершения цикла по первому персонажу.</li>
        </ul>
        
        <hr style='border: 0; border-top: 1px solid #30363d; margin: 20px 0;'>
        <p style='color: #8b949e; font-style: italic; font-size: 11px;'>
            По любым вопросам всегда на связи в <a href="https://discordapp.com/users/dendidima228" style="color: #58a6ff; text-decoration: none;">Discord</a> или <a href="https://t.me/nobrainchel" style="color: #58a6ff; text-decoration: none;">Telegram</a>!
        </p>
        """
        
        label = QLabel(guide_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        label.setOpenExternalLinks(True)
        self.layout.addWidget(label)
        self.layout.addStretch()
