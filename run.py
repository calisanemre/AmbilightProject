import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'gui')))

from gui.tray_app import TrayApp

if __name__ == "__main__":
    TrayApp().start_tray_app()
