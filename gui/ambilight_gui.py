import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.device_interface import DeviceInterface
from engine.screen_capture import ScreenCapturer
from engine.color_processor import ColorProcessor
import tkinter as tk
from tkinter import ttk
import threading
import pystray
from PIL import Image
import serial.tools.list_ports
import json
import time


CONFIG_FILE = "config/config.json"


class SettingsWindow:
    def __init__(self, on_save=None, on_brightness_change_cb = None):
        self.window = None
        self.notebook = None
        self.config = None
        self.config_file = CONFIG_FILE
        self.config_loaded = self.load_config_if_exists()
        self.on_save = on_save
        self.on_brightness_change_cb = on_brightness_change_cb


    def load_config_if_exists(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                return True
            except Exception as e:
                print("[SettingsWindow] Config couldn't opened:", e)
        return False


    def show(self):
        try:
            if self.window is not None and self.window.winfo_exists():
                self.window.lift()
                return
        except:
            self.window = None

        self.window = tk.Toplevel()
        self.window.title("Ambilight Settings")
        self.window.geometry("400x400")
        self.window.resizable(False, False)

        self.notebook = ttk.Notebook(self.window)

        self.tab_general = ttk.Frame(self.notebook)
        self.tab_advanced = ttk.Frame(self.notebook)
        self.tab_configure = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_general, text="General",
                        state="normal" if self.config_loaded else "disabled")
        self.notebook.add(self.tab_advanced, text="Advanced",
                        state="normal" if self.config_loaded else "disabled")
        self.notebook.add(self.tab_configure, text="Configure")

        self.notebook.pack(fill='both', expand=True)

        self.setup_general_tab()
        self.setup_configure_tab()

        if self.config_loaded:
            self.notebook.select(0)

        self.window = None


    def setup_configure_tab(self):
        frame = ttk.Frame(self.tab_configure)
        frame.pack(pady=10, padx=20, fill='both', expand=True)

        label_width = 20
        entry_width = 15

        row = 0

        # === LED Configuration ===
        ttk.Label(frame, text="LED Count:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')

        led_frame = ttk.Frame(frame)
        led_frame.grid(row=row, column=1, sticky='w')

        # Labels for directions
        for i, direction in enumerate(["Top", "Right", "Bottom", "Left"]):
            ttk.Label(led_frame, text=direction).grid(row=0, column=i, padx=2)

        # Entry boxes
        self.led_top = ttk.Entry(led_frame, width=4)
        self.led_right = ttk.Entry(led_frame, width=4)
        self.led_bottom = ttk.Entry(led_frame, width=4)
        self.led_left = ttk.Entry(led_frame, width=4)

        led_entries = [self.led_top, self.led_right, self.led_bottom, self.led_left]
        default_values = [10, 6, 10, 6]

        for i, (entry, val) in enumerate(zip(led_entries, default_values)):
            entry.insert(0, str(val))
            entry.grid(row=1, column=i, padx=2, pady=2)

        # === Serial Port ===
        row += 1
        ttk.Label(frame, text="Serial Port:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.serial_port_combo = ttk.Combobox(frame, values=self.get_serial_ports(), state='readonly', width=entry_width)
        self.serial_port_combo.set("COM3")
        self.serial_port_combo.grid(row=row, column=1, sticky='w')

        # === Baud Rate ===
        row += 1
        ttk.Label(frame, text="Baud Rate:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        baud_rates = [9600, 19200, 38400, 57600, 115200, 250000, 1000000]
        self.baud_rate_combo = ttk.Combobox(frame, values=baud_rates, state='readonly', width=entry_width)
        self.baud_rate_combo.set(115200)
        self.baud_rate_combo.grid(row=row, column=1, sticky='w')

        # === Margin ===
        row += 1
        ttk.Label(frame, text="Margin:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.margin_entry = ttk.Entry(frame, width=entry_width)
        self.margin_entry.insert(0, "40")
        self.margin_entry.grid(row=row, column=1, sticky='w')

        # === Update Rate ===
        row += 1
        ttk.Label(frame, text="Update Rate (Hz):", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.update_rate_combo = ttk.Combobox(frame, values=[10, 20, 30, 60], state='readonly', width=entry_width)
        self.update_rate_combo.set(30)
        self.update_rate_combo.grid(row=row, column=1, sticky='w')

        # === Order ===
        row += 1
        ttk.Label(frame, text="LED Order:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.order_combo = ttk.Combobox(frame, values=["Clockwise", "Counter-Clockwise"], state='readonly', width=entry_width)
        self.order_combo.set("Clockwise")
        self.order_combo.grid(row=row, column=1, sticky='w')

        # === Start Side ===
        row += 1
        ttk.Label(frame, text="Start Side:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.start_side_combo = ttk.Combobox(frame, values=["Top", "Right", "Bottom", "Left"], state='readonly', width=entry_width)
        self.start_side_combo.set("Bottom")
        self.start_side_combo.grid(row=row, column=1, sticky='w')

        # === Save Button ===
        row += 1
        ttk.Button(
            frame,
            text="Save Configuration",
            command=self.save_and_enable
        ).grid(row=row, column=0, columnspan=2, pady=20)


    # helper method to get serial ports
    def get_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports if ports else ["No Ports Found"]


    # Save handler
    def save_and_enable(self):
        config = {
            "led_config": {
                "top": int(self.led_top.get()),
                "right": int(self.led_right.get()),
                "bottom": int(self.led_bottom.get()),
                "left": int(self.led_left.get())
            },
            "serial_port": self.serial_port_combo.get(),
            "baud_rate": int(self.baud_rate_combo.get()),
            "margin": int(self.margin_entry.get()),
            "update_rate_hz": int(self.update_rate_combo.get()),
            "order": self.order_combo.get().lower().replace("-", ""),
            "start_side": self.start_side_combo.get().lower()
        }

        # JSON file save
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
            print("[SettingsWindow] Configuration saved to file:", self.config_file)
        except Exception as e:
            print("[SettingsWindow] Config save error:", e)

        #self.config_loaded = True
        self.enable_other_tabs()

        if self.on_save:
            self.on_save()


    def enable_other_tabs(self):
        self.notebook.tab(0, state="normal")
        self.notebook.tab(1, state="normal")
        self.notebook.select(0)


    def on_brightness_change(self, value):
        try:
            brightness = float(value)
            if hasattr(self, "on_brightness_change_cb") and self.on_brightness_change_cb:
                self.on_brightness_change_cb(brightness)
        except Exception as e:
            print("[SettingsWindow] Brightness change error:", e)


    def setup_general_tab(self):
        ttk.Label(self.tab_general, text="Brightness:").pack(pady=(10, 0))
        self.brightness_var = tk.DoubleVar()
        self.brightness_slider = ttk.Scale(
            self.tab_general,
            from_=0,
            to=100,
            orient='horizontal',
            variable=self.brightness_var,
            command=self.on_brightness_change
        )
        self.brightness_slider.set(75)
        self.brightness_slider.pack()


class TrayApp:
    def __init__(self):
        self.running = False
        self.is_device_connected = False
        self.config_path = CONFIG_FILE
        self.settings_ui = SettingsWindow(
            on_save=self._on_config_saved,
            on_brightness_change_cb=self.set_brightness
            )
        
        if self.settings_ui.config_loaded:
            self._initialize_components()

        self.tray_icon = None
        self.on_icon_path = "assets/led_on.png"
        self.off_icon_path = "assets/led_off.png"
    

    def _on_config_saved(self):
        print("[TrayApp] Config saved. Initializing components...")
        self._initialize_components()


    def set_brightness(self, brightness):
        if hasattr(self, "device") and self.device:
            self.device.send_brightness(brightness)


    def _initialize_components(self):
        self.color_processor = ColorProcessor.from_config(self.config_path)
        self.screen_capturer = ScreenCapturer()
        self.device = DeviceInterface.from_config(self.config_path)
        try:
            self.device.generate_ino()
            self.device.upload_ino()
            self.device.connect()
            self.is_device_connected = True
        except Exception as e:
            print("[TrayApp] Couldn't connected with the Device: ",e)

    def start_system(self):
        if not self.is_device_connected:
            self.update_icon()
            print("[TrayApp] Can't start: No device connected.")
            return
        print("[TrayApp] System started.")
        self.running = True
        self.update_icon()
        self.sender_threat = threading.Thread(target=self.color_sender_loop, daemon=True)
        self.sender_threat.start()


    def stop_system(self):
        print("[TrayApp] System stopped.")
        self.running = False
        self.update_icon()


    def color_sender_loop(self):
        if not self.is_device_connected:
            print("[TrayApp] There is no device connected.")
            return
        
        try:
            # Get update_rate
            update_rate = self.settings_ui.config.get("update_rate_hz", 30)
            interval = 1.0 / update_rate

            while self.running:
                color = self.color_processor.get_led_colors(self.screen_capturer.capture_screen())
                self.device.send_colors(color)
                time.sleep(interval)
        except Exception as e:
            print("[TrayApp] color_sender_loop error:", e)


    def open_settings(self, _=None):
        self.root.after(0, self.settings_ui.show)


    def quit_app(self, _=None):
        print("[TrayApp] Quitting...")
        if self.tray_icon:
            self.tray_icon.stop()

        if hasattr(self, "root") and self.root:
            self.root.destroy()


    def update_icon(self):
        icon_path = self.on_icon_path if self.running else self.off_icon_path
        self.tray_icon.icon = Image.open(icon_path)


    def run(self):
        self.root = tk.Tk()
        self.root.withdraw()

        threading.Thread(target=self.run_tray_icon, daemon=True).start()

        self.root.mainloop()


    def run_tray_icon(self):
        icon_image = Image.open(self.off_icon_path)

        menu = pystray.Menu(
            pystray.MenuItem("Toggle On/Off", self.on_left_click_toggle, default=True),
            pystray.MenuItem("Settings", self.open_settings),
            pystray.MenuItem("Quit", self.quit_app)
        )

        self.tray_icon = pystray.Icon("AmbilightTray", icon_image, "Ambilight Control", menu)
        self.tray_icon.run()


    def on_left_click_toggle(self):
        self.settings_ui.config_loaded = self.settings_ui.load_config_if_exists()

        if self.settings_ui.config_loaded:
            if self.running:
                self.stop_system()
            else:
                self.start_system()
        else:
            print("[TrayApp] Please enter your LED configurations.")


if __name__ == "__main__":
    # (Optional) Hide console on Windows
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    print("TrayApp started!")
    app = TrayApp()
    app.run()
