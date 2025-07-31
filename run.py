import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'gui')))

from gui.ambilight_gui import start_tray_app

if __name__ == "__main__":
    start_tray_app()
