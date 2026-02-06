import sys
from PyQt6.QtWidgets import QApplication
from src.ui.launcher import LauncherWindow

# Simple entry point to test the UI flow
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # This will trigger the license check inside __init__
    window = LauncherWindow()
    
    # If license is present valid, Launcher shows itself.
    # If not, it hides itself and shows LoginWindow.
    # We must start the event loop in either case.
    
    sys.exit(app.exec())
