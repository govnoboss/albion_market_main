from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from ..core.license import license_manager

class LicenseCheckThread(QThread):
    result = pyqtSignal(dict)
    
    def __init__(self, key):
        super().__init__()
        self.key = key
        
    def run(self):
        # Fake delay to look cool? No, requests are blocking
        res = license_manager.validate_key(self.key)
        self.result.emit(res)

class LoginWindow(QMainWindow):
    def __init__(self, on_success_callback):
        super().__init__()
        self.on_success = on_success_callback
        self.setWindowTitle("GBot - Activation")
        self.resize(400, 300)
        
        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; }
            QLabel { color: #f0f6fc; }
            QLineEdit { 
                padding: 10px; 
                border-radius: 5px; 
                border: 1px solid #30363d;
                background-color: #161b22;
                color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #238636;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:disabled { background-color: #30363d; color: #8b949e; }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("GBot Activation")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Subtitle
        sub = QLabel("Please enter your license key")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #8b949e;")
        layout.addWidget(sub)
        
        # Input
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.input_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Pre-fill if exists
        saved = license_manager.load_key()
        if saved:
            self.input_key.setText(saved)
            
        layout.addWidget(self.input_key)
        
        # Status
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #eb4034;")
        layout.addWidget(self.lbl_status)
        
        # Button
        self.btn_login = QPushButton("ACTIVATE")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self.start_check)
        layout.addWidget(self.btn_login)
        
        layout.addStretch()
        
        # HWID Label
        hwid = license_manager.get_hwid()
        lbl_hwid = QLabel(f"HWID: {hwid[:8]}...")
        lbl_hwid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hwid.setStyleSheet("color: #30363d; font-size: 10px;")
        layout.addWidget(lbl_hwid)

    def start_check(self):
        key = self.input_key.text().strip()
        if not key:
            self.lbl_status.setText("Enter key!")
            return
            
        self.btn_login.setText("Checking...")
        self.btn_login.setEnabled(False)
        self.lbl_status.setText("")
        self.input_key.setEnabled(False)
        
        self.worker = LicenseCheckThread(key)
        self.worker.result.connect(self.handle_result)
        self.worker.start()
        
    def handle_result(self, res):
        self.btn_login.setEnabled(True)
        self.input_key.setEnabled(True)
        self.btn_login.setText("ACTIVATE")
        
        if res['success']:
            self.lbl_status.setStyleSheet("color: #238636;")
            self.lbl_status.setText("Success! Loading...")
            self.close()
            self.on_success() # Open Launcher
        else:
            self.lbl_status.setStyleSheet("color: #eb4034;")
            self.lbl_status.setText(res['message'])
