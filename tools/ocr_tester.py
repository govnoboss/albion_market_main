import sys
import os
import cv2
import numpy as np
import pytesseract
from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QSlider, QCheckBox, 
    QComboBox, QTextEdit, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

# Добавляем путь к src, чтобы использовать существующие утилиты если нужно
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.utils.ocr import init_ocr
    init_ocr()
except ImportError:
    pass

class OCRTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR Testing & Filter Configuration Tool")
        self.resize(1200, 800)

        self.original_image = None
        self.processed_image = None
        self.last_path = ""
        
        # Debounce timer for dynamic OCR
        self.ocr_timer = QTimer()
        self.ocr_timer.setSingleShot(True)
        self.ocr_timer.timeout.connect(self.run_ocr)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Sidebar (Controls) ---
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        
        load_btn = QPushButton("Загрузить изображение")
        load_btn.clicked.connect(self.load_image)
        sidebar_layout.addWidget(load_btn)

        # Scale
        sidebar_layout.addWidget(QLabel("Масштаб (Scale):"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(1, 10)
        self.scale_slider.setValue(1) # Default 1x
        self.scale_label = QLabel("1.0x")
        self.scale_slider.valueChanged.connect(self.update_params)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.scale_slider)
        h_layout.addWidget(self.scale_label)
        sidebar_layout.addLayout(h_layout)

        # Contrast
        sidebar_layout.addWidget(QLabel("Контраст (Contrast):"))
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(5, 30)
        self.contrast_slider.setValue(10)
        self.contrast_label = QLabel("1.0")
        self.contrast_slider.valueChanged.connect(self.update_params)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.contrast_slider)
        h_layout.addWidget(self.contrast_label)
        sidebar_layout.addLayout(h_layout)

        # Brightness
        sidebar_layout.addWidget(QLabel("Яркость (Brightness):"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_label = QLabel("0")
        self.brightness_slider.valueChanged.connect(self.update_params)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.brightness_slider)
        h_layout.addWidget(self.brightness_label)
        sidebar_layout.addLayout(h_layout)

        # Threshold Type
        sidebar_layout.addWidget(QLabel("Тип порога (Threshold):"))
        self.thresh_combo = QComboBox()
        self.thresh_combo.addItems(["None", "Binary", "Binary Inv", "Otsu", "Adaptive Mean", "Adaptive Gaussian"])
        self.thresh_combo.setCurrentIndex(0) # Default None
        self.thresh_combo.currentIndexChanged.connect(self.update_params)
        sidebar_layout.addWidget(self.thresh_combo)

        # Threshold Value
        self.thresh_val_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_val_slider.setRange(0, 255)
        self.thresh_val_slider.setValue(127)
        self.thresh_val_label = QLabel("127")
        self.thresh_val_slider.valueChanged.connect(self.update_params)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.thresh_val_slider)
        h_layout.addWidget(self.thresh_val_label)
        sidebar_layout.addLayout(h_layout)

        # Grayscale & Invert
        self.gray_check = QCheckBox("Grayscale (Ч/Б)")
        self.gray_check.setChecked(False) # Default False
        self.gray_check.stateChanged.connect(self.update_params)
        sidebar_layout.addWidget(self.gray_check)

        self.invert_check = QCheckBox("Invert (Инверсия)")
        self.invert_check.setChecked(False) # Default False
        self.invert_check.stateChanged.connect(self.update_params)
        sidebar_layout.addWidget(self.invert_check)

        # Blur
        sidebar_layout.addWidget(QLabel("Размытие (Median Blur size):"))
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 5) # 0, 1, 3, 5
        self.blur_slider.setValue(0)
        self.blur_slider.valueChanged.connect(self.update_params)
        sidebar_layout.addWidget(self.blur_slider)

        # OCR Options
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(QLabel("--- OCR Settings ---"))
        
        sidebar_layout.addWidget(QLabel("PSM (Page Segmentation Mode):"))
        self.psm_combo = QComboBox()
        for i in range(14):
            desc = f"{i}"
            if i == 3: desc += " (Default)"
            if i == 6: desc += " (Single Block)"
            if i == 7: desc += " (Single Line)"
            if i == 11: desc += " (Sparse Text)"
            self.psm_combo.addItem(desc, i)
        self.psm_combo.setCurrentIndex(6)
        self.psm_combo.currentIndexChanged.connect(self.update_params)
        sidebar_layout.addWidget(self.psm_combo)

        sidebar_layout.addWidget(QLabel("Язык (lang):"))
        self.lang_input = QComboBox()
        self.lang_input.addItems(["eng", "rus", "eng+rus"])
        self.lang_input.currentIndexChanged.connect(self.update_params)
        sidebar_layout.addWidget(self.lang_input)

        sidebar_layout.addWidget(QLabel("Whitelist characters:"))
        self.whitelist_input = QTextEdit()
        self.whitelist_input.setMaximumHeight(60)
        self.whitelist_input.setPlaceholderText("0123456789.,kKmMBb")
        self.whitelist_input.textChanged.connect(self.update_params) # Re-run OCR on text change
        sidebar_layout.addWidget(self.whitelist_input)

        ocr_btn = QPushButton("ЗАПУСТИТЬ OCR")
        ocr_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; height: 40px;")
        ocr_btn.clicked.connect(self.run_ocr)
        sidebar_layout.addWidget(ocr_btn)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # --- Viewport ---
        viewport = QSplitter(Qt.Orientation.Vertical)
        
        # Images area
        images_widget = QWidget()
        images_layout = QHBoxLayout(images_widget)
        
        self.orig_label = QLabel("Оригинал")
        self.orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orig_scroll = QScrollArea()
        self.orig_scroll.setWidget(self.orig_label)
        self.orig_scroll.setWidgetResizable(True)
        
        self.proc_label = QLabel("Результат обработки")
        self.proc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.proc_scroll = QScrollArea()
        self.proc_scroll.setWidget(self.proc_label)
        self.proc_scroll.setWidgetResizable(True)
        
        images_layout.addWidget(self.orig_scroll)
        images_layout.addWidget(self.proc_scroll)
        
        viewport.addWidget(images_widget)

        # OCR Output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFontFamily("Consolas")
        self.output_text.setFontPointSize(12)
        self.output_text.setPlaceholderText("Результат OCR появится здесь...")
        viewport.addWidget(self.output_text)
        
        viewport.setStretchFactor(0, 3)
        viewport.setStretchFactor(1, 1)
        
        main_layout.addWidget(viewport)

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", self.last_path, "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.last_path = os.path.dirname(path)
            self.original_image = cv2.imread(path)
            if self.original_image is not None:
                self.display_image(self.original_image, self.orig_label)
                self.process_image()

    def update_params(self):
        # Update labels
        self.scale_label.setText(f"{self.scale_slider.value()}x")
        self.contrast_label.setText(f"{self.contrast_slider.value()/10:.1f}")
        self.brightness_label.setText(str(self.brightness_slider.value()))
        self.thresh_val_label.setText(str(self.thresh_val_slider.value()))
        
        self.process_image()
        
        # Automatic Dynamic OCR
        self.ocr_timer.stop()
        self.ocr_timer.start(500) # Wait 500ms after last change to run OCR

    def process_image(self):
        if self.original_image is None:
            return

        img = self.original_image.copy()

        # 1. Scale
        scale = self.scale_slider.value()
        if scale != 1:
            width = int(img.shape[1] * scale)
            height = int(img.shape[0] * scale)
            img = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)

        # 2. Brightness & Contrast
        alpha = self.contrast_slider.value() / 10.0
        beta = self.brightness_slider.value()
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

        # 3. Grayscale
        if self.gray_check.isChecked():
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 4. Blur
        blur_val = self.blur_slider.value() * 2 - 1 # 1, 3, 5, 7, 9
        if blur_val > 0:
            img = cv2.medianBlur(img, blur_val)

        # 5. Threshold
        thresh_type = self.thresh_combo.currentText()
        thresh_val = self.thresh_val_slider.value()
        
        if thresh_type != "None":
            # Thresholding requires grayscale
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            if thresh_type == "Binary":
                _, img = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY)
            elif thresh_type == "Binary Inv":
                _, img = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY_INV)
            elif thresh_type == "Otsu":
                _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            elif thresh_type == "Adaptive Mean":
                img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
            elif thresh_type == "Adaptive Gaussian":
                img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # 6. Invert
        if self.invert_check.isChecked():
            img = cv2.bitwise_not(img)

        self.processed_image = img.copy()
        self.display_image(self.processed_image, self.proc_label)

    def display_image(self, img, label):
        if img is None:
            return

        # Handle color conversion for display (OpenCV BGR -> RGB)
        if len(img.shape) == 3:
            # OpenCV BGR to RGB
            display_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = display_img.shape
            bytes_per_line = ch * w
            q_img = QImage(display_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        else:
            # Grayscale
            h, w = img.shape
            bytes_per_line = w
            q_img = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8).copy()

        pixmap = QPixmap.fromImage(q_img)
        label.setPixmap(pixmap)

    def run_ocr(self):
        if self.processed_image is None:
            self.output_text.setText("Сначала загрузите изображение!")
            return

        self.output_text.setText("Распознавание...")
        QApplication.processEvents()

        try:
            # Prepare config
            psm = self.psm_combo.currentData()
            lang = self.lang_input.currentText()
            whitelist = self.whitelist_input.toPlainText().strip()
            
            config = f'--psm {psm}'
            if whitelist:
                config += f' -c tessedit_char_whitelist={whitelist}'

            # Run Tesseract
            # Convert to PIL for tesseract
            pil_img = Image.fromarray(self.processed_image)
            
            # Using image_to_data to get confidence scores and coordinates
            data = pytesseract.image_to_data(pil_img, lang=lang, config=config, output_type=pytesseract.Output.DICT)
            
            result_text = ""
            confidences = []
            
            # Reconstruct text and collect confidences
            for i in range(len(data['text'])):
                conf = int(data['conf'][i])
                text = data['text'][i]
                if conf != -1:
                    result_text += text + " "
                    confidences.append(conf)

            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            
            summary = f"--- OCR RESULTS ---\n"
            summary += f"Raw Text: {result_text.strip()}\n"
            summary += f"Avg Confidence: {avg_conf:.1f}%\n"
            summary += f"PSM: {psm}, Lang: {lang}\n"
            summary += f"Tesseract Path: {pytesseract.pytesseract.tesseract_cmd}\n"
            summary += f"-------------------\n\n"
            summary += "Detailed word confidence:\n"
            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    summary += f"'{data['text'][i]}': {data['conf'][i]}%\n"

            self.output_text.setText(summary)
            
        except Exception as e:
            self.output_text.setText(f"ОШИБКА OCR: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OCRTester()
    window.show()
    sys.exit(app.exec())
