import sys
import os
import cv2
import numpy as np
import pytesseract
import shutil
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QScrollArea, QFrame, QGridLayout, 
                             QTextEdit, QCheckBox, QSlider, QComboBox, QGroupBox, QSpinBox,
                             QSplitter, QListWidget, QListWidgetItem, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPixmap, QImage, QIcon, QAction

# --- Tesseract Setup ---
TESSERACT_CMD = shutil.which("tesseract")
if not TESSERACT_CMD:
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\Student\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            TESSERACT_CMD = path
            break

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# --- Image Utils ---
def to_qimage(cv_img):
    if cv_img is None: return QImage()
    if len(cv_img.shape) == 2: # Grayscale
        height, width = cv_img.shape
        bytes_per_line = width
        return QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
    else: # RGB/BGR
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

# --- Processing Logic ---
class ImageProcessor:
    @staticmethod
    def process(image, settings):
        """
        Settings dict structure:
        {
            'scale': float,
            'grayscale': bool,
            'invert': bool,
            'denoise': bool,
            'threshold_type': str ('None', 'Simple', 'Otsu', 'Adaptive'),
            'thresh_val': int,
            'morph_type': str ('None', 'Erode', 'Dilate'),
            'morph_kernel': int,
            'morph_iter': int
        }
        """
        if image is None: return None
        
        img = image.copy()
        
        # 1. Scale
        if settings['scale'] != 1.0:
            width = int(img.shape[1] * settings['scale'])
            height = int(img.shape[0] * settings['scale'])
            img = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)
            
        # 2. Grayscale (Almost always required for others)
        if settings['grayscale']:
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
        # 3. Denoise
        if settings['denoise']:
            if len(img.shape) == 3:
                 img = cv2.bilateralFilter(img, 9, 75, 75)
            else:
                 # Bilateral requires 8-bit
                 img = cv2.bilateralFilter(img, 9, 75, 75)

        # 4. Invert (Pre-threshold)
        if settings['invert']:
            img = cv2.bitwise_not(img)

        # 5. Threshold
        t_type = settings['threshold_type']
        if len(img.shape) == 3 and t_type != 'None':
             img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if t_type == 'Simple':
            _, img = cv2.threshold(img, settings['thresh_val'], 255, cv2.THRESH_BINARY)
        elif t_type == 'Otsu':
            _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif t_type == 'Adaptive':
            # Block size must be odd
            bs = 11
            img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, bs, 2)

        # 6. Morphology
        m_type = settings['morph_type']
        if m_type != 'None':
            k_size = settings['morph_kernel']
            kernel = np.ones((k_size, k_size), np.uint8)
            iterations = settings['morph_iter']
            
            if m_type == 'Erode':
                img = cv2.erode(img, kernel, iterations=iterations)
            elif m_type == 'Dilate':
                img = cv2.dilate(img, kernel, iterations=iterations)
                
        return img

# --- Custom Widgets ---

class PresetWidget(QFrame):
    delete_requested = pyqtSignal()
    load_requested = pyqtSignal(dict) # Emits settings

    def __init__(self, name, settings, thumb_pixmap, result_text):
        super().__init__()
        self.settings = settings
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumb
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setPixmap(thumb_pixmap.scaled(80, 50, Qt.TransformationMode.KeepAspectRatio))
        self.lbl_thumb.setFixedSize(80, 50)
        self.lbl_thumb.setStyleSheet("border: 1px solid #ccc;")
        
        # Info
        info_layout = QVBoxLayout()
        self.lbl_name = QLabel(f"<b>{name}</b>")
        self.lbl_text = QLabel(f"Result: {result_text}")
        self.lbl_text.setStyleSheet("color: blue; font-family: Consolas;")
        
        # Desc string
        desc = []
        if settings['scale'] > 1: desc.append(f"x{settings['scale']}")
        if settings['invert']: desc.append("Inv")
        desc.append(settings['threshold_type'])
        if settings['morph_type'] != 'None': desc.append(settings['morph_type'])
        
        self.lbl_desc = QLabel(", ".join(desc))
        self.lbl_desc.setStyleSheet("color: gray; font-size: 10px;")
        
        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_text)
        info_layout.addWidget(self.lbl_desc)
        
        # Buttons
        btn_layout = QVBoxLayout()
        self.btn_load = QPushButton("Load")
        self.btn_load.clicked.connect(lambda: self.load_requested.emit(self.settings))
        self.btn_del = QPushButton("X")
        self.btn_del.setMaximumWidth(30)
        self.btn_del.setStyleSheet("color: red;")
        self.btn_del.clicked.connect(self.delete_requested.emit)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_del)
        
        layout.addWidget(self.lbl_thumb)
        layout.addLayout(info_layout)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

class TesTestLab(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR Laboratory")
        self.resize(1400, 900)
        
        self.current_image = None
        self.processed_image = None
        
        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # --- Left Panel: Controls ---
        left_panel = QFrame()
        left_panel.setFixedWidth(350)
        left_layout = QVBoxLayout(left_panel)
        
        # Load Btn
        self.btn_load = QPushButton("📁 Load Image")
        self.btn_load.clicked.connect(self.load_image)
        self.btn_load.setStyleSheet("padding: 10px; font-weight: bold;")
        left_layout.addWidget(self.btn_load)

        # Settings Group
        self.settings_group = QGroupBox("Filter Pipeline")
        sg_layout = QVBoxLayout()
        
        # 1. Scale
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale:"))
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(1, 5)
        self.spin_scale.setValue(3)
        self.spin_scale.valueChanged.connect(self.request_update)
        scale_layout.addWidget(self.spin_scale)
        sg_layout.addLayout(scale_layout)
        
        # 2. Boolean Ops
        self.chk_grayscale = QCheckBox("Grayscale")
        self.chk_grayscale.setChecked(True)
        self.chk_grayscale.toggled.connect(self.request_update)
        
        self.chk_invert = QCheckBox("Invert Colors")
        self.chk_invert.toggled.connect(self.request_update)
        
        self.chk_denoise = QCheckBox("Denoise (Bilateral)")
        self.chk_denoise.toggled.connect(self.request_update)
        
        sg_layout.addWidget(self.chk_grayscale)
        sg_layout.addWidget(self.chk_invert)
        sg_layout.addWidget(self.chk_denoise)
        
        # 3. Threshold
        sg_layout.addWidget(QLabel("Thresholding:"))
        self.combo_thresh = QComboBox()
        self.combo_thresh.addItems(["None", "Simple", "Otsu", "Adaptive"])
        self.combo_thresh.setCurrentText("Otsu")
        self.combo_thresh.currentTextChanged.connect(self.request_update)
        sg_layout.addWidget(self.combo_thresh)
        
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setRange(0, 255)
        self.slider_thresh.setValue(127)
        self.slider_thresh.setEnabled(False) # Only for Simple
        self.slider_thresh.valueChanged.connect(self.request_update)
        sg_layout.addWidget(self.slider_thresh)
        
        # 4. Morphology
        sg_layout.addWidget(QLabel("Morphology:"))
        self.combo_morph = QComboBox()
        self.combo_morph.addItems(["None", "Erode", "Dilate"])
        self.combo_morph.currentTextChanged.connect(self.request_update)
        sg_layout.addWidget(self.combo_morph)
        
        morph_params = QHBoxLayout()
        morph_params.addWidget(QLabel("Kernel:"))
        self.spin_kernel = QSpinBox()
        self.spin_kernel.setRange(1, 7)
        self.spin_kernel.setValue(2)
        self.spin_kernel.valueChanged.connect(self.request_update)
        morph_params.addWidget(self.spin_kernel)
        
        morph_params.addWidget(QLabel("Iter:"))
        self.spin_iter = QSpinBox()
        self.spin_iter.setRange(1, 5)
        self.spin_iter.setValue(1)
        self.spin_iter.valueChanged.connect(self.request_update)
        morph_params.addWidget(self.spin_iter)
        
        sg_layout.addLayout(morph_params)
        
        self.settings_group.setLayout(sg_layout)
        left_layout.addWidget(self.settings_group)
        
        left_layout.addStretch()
        
        # Save Preset
        self.btn_save_preset = QPushButton("💾 Save Preset")
        self.btn_save_preset.clicked.connect(self.save_preset)
        self.btn_save_preset.setStyleSheet("background-color: #dff0d8; padding: 10px;")
        left_layout.addWidget(self.btn_save_preset)
        
        main_layout.addWidget(left_panel)
        
        # --- Middle: Preview ---
        mid_panel = QFrame()
        mid_layout = QVBoxLayout(mid_panel)
        
        # OCR Result Display
        self.lbl_ocr_result = QLabel("OCR: Waiting...")
        self.lbl_ocr_result.setStyleSheet("font-size: 18px; font-weight: bold; background: #eee; padding: 10px; border-radius: 5px;")
        self.lbl_ocr_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ocr_result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mid_layout.addWidget(self.lbl_ocr_result)
        
        # Image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("background-color: #333;")
        self.scroll_area.setWidget(self.lbl_image)
        mid_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(mid_panel, stretch=2)
        
        # --- Right: Presets ---
        right_panel = QFrame()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("<b>Saved Presets</b>"))
        self.preset_list = QListWidget()
        self.preset_list.setSelectionMode(QListWidget.SelectionMode.NoSelection) # We use buttons
        right_layout.addWidget(self.preset_list)
        
        main_layout.addWidget(right_panel)
        
        # Debounce timer
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(200) # 200ms debounce
        self.update_timer.timeout.connect(self.run_processing)
        
    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            stream = open(path, "rb")
            bytes = bytearray(stream.read())
            numpyarray = np.asarray(bytes, dtype=np.uint8)
            img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            self.current_image = img
            self.run_processing()
            
    def get_settings(self):
        return {
            'scale': self.spin_scale.value(),
            'grayscale': self.chk_grayscale.isChecked(),
            'invert': self.chk_invert.isChecked(),
            'denoise': self.chk_denoise.isChecked(),
            'threshold_type': self.combo_thresh.currentText(),
            'thresh_val': self.slider_thresh.value(),
            'morph_type': self.combo_morph.currentText(),
            'morph_kernel': self.spin_kernel.value(),
            'morph_iter': self.spin_iter.value()
        }
        
    def apply_settings(self, settings):
        self.spin_scale.setValue(settings['scale'])
        self.chk_grayscale.setChecked(settings['grayscale'])
        self.chk_invert.setChecked(settings['invert'])
        self.chk_denoise.setChecked(settings['denoise'])
        self.combo_thresh.setCurrentText(settings['threshold_type'])
        self.slider_thresh.setValue(settings['thresh_val'])
        self.combo_morph.setCurrentText(settings['morph_type'])
        self.spin_kernel.setValue(settings['morph_kernel'])
        self.spin_iter.setValue(settings['morph_iter'])
        self.run_processing()

    def request_update(self):
        # Enable/Disable slider
        self.slider_thresh.setEnabled(self.combo_thresh.currentText() == 'Simple')
        
        if self.current_image is not None:
            self.update_timer.start()
            
    def run_processing(self):
        if self.current_image is None: return
        
        settings = self.get_settings()
        try:
            processed = ImageProcessor.process(self.current_image, settings)
            self.processed_image = processed
            
            # Show Image
            qimg = to_qimage(processed)
            pixmap = QPixmap.fromImage(qimg)
            self.lbl_image.setPixmap(pixmap)
            
            # Run OCR
            custom_config = r'--psm 6'
            try:
                data = pytesseract.image_to_data(processed, config=custom_config, output_type='dict')
                results = []
                for i in range(len(data['text'])):
                    conf = int(data['conf'][i])
                    txt = data['text'][i].strip()
                    if conf > -1 and txt:
                        results.append(f"{txt} [{conf}%]")
                
                if not results:
                    text = "<empty>"
                else:
                    text = " ".join(results)
            except Exception as ocr_err:
                text = f"OCR Error: {ocr_err}"
            
            self.lbl_ocr_result.setText(f"OCR: {text}")
            self.lbl_ocr_result.setStyleSheet("font-size: 18px; font-weight: bold; background: #e0f7fa; padding: 10px; border-radius: 5px;")
            
        except Exception as e:
            self.lbl_ocr_result.setText(f"Error: {e}")
            self.lbl_ocr_result.setStyleSheet("background: #ffcdd2; padding: 10px;")

    def save_preset(self):
        if self.processed_image is None: return
        
        settings = self.get_settings()
        ocr_text = self.lbl_ocr_result.text().replace("OCR: ", "")
        
        # Create thumbnail
        qimg = to_qimage(self.processed_image)
        thumb = QPixmap.fromImage(qimg)
        
        # Generate Name
        count = self.preset_list.count() + 1
        name = f"Preset #{count}"
        
        # Create Widget
        item_widget = PresetWidget(name, settings, thumb, ocr_text)
        item_widget.load_requested.connect(self.apply_settings)
        
        # Create List Item
        item = QListWidgetItem(self.preset_list)
        item.setSizeHint(item_widget.sizeHint())
        
        # Connect Delete
        item_widget.delete_requested.connect(lambda: self.remove_preset(item))
        
        self.preset_list.setItemWidget(item, item_widget)
        
    def remove_preset(self, item):
        row = self.preset_list.row(item)
        self.preset_list.takeItem(row)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TesTestLab()
    window.show()
    sys.exit(app.exec())
