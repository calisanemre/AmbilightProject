import os
import tkinter as tk
from tkinter import ttk
import threading
import serial.tools.list_ports
import json
from gui.led_preview_hud import LEDPreviewHUD
from tools.logger import setup_logger

logger = setup_logger("SettingsWindow")

class SettingsWindow:
    def __init__(self, config_file, on_save=None, on_brightness_change_cb = None, on_tolerance_change_cb = None, get_current_values_cb=None):
        self.window = None
        self.notebook = None
        self.config = None
        self.config_file = config_file
        self.config_loaded = self.load_config_if_exists()
        self.on_save = on_save
        self.on_brightness_change_cb = on_brightness_change_cb
        self.last_sent_brightness = None
        self.on_tolerance_change_cb = on_tolerance_change_cb
        self.last_sent_tolerance = None
        self.get_current_values_cb = get_current_values_cb

    def load_config_if_exists(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                return True
            except Exception as e:
                logger.error(f"Failed to open config file: {e}")
        return False


    def show(self):
        try:
            if self.window is not None and self.window.winfo_exists():
                self.load_config_if_exists()
                self.sync_values_from_config()
                self.window.lift()
                return
        except:
            self.window = None

        self.window = tk.Toplevel()
        self.window.title("Ambilight Settings")
        self.window.geometry("400x400")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.notebook = ttk.Notebook(self.window)

        self.tab_general = ttk.Frame(self.notebook)
        self.tab_configure = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_general, text="Light Settings",
                        state="normal" if self.config_loaded else "disabled")
        self.notebook.add(self.tab_configure, text="Configure")

        self.notebook.pack(fill='both', expand=True)

        self.setup_general_tab()
        self.setup_configure_tab()
        
        self.sync_values_from_config()

        if self.config_loaded:
            self.notebook.select(0)


    def setup_configure_tab(self):
        frame = ttk.Frame(self.tab_configure)
        frame.pack(pady=10, padx=20, fill='both', expand=True)

        label_width = 20
        entry_width = 15

        row = 0

        # === LED Configuration ===
        ttk.Label(frame, text="LED Configuration:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')

        led_config_frame = ttk.Frame(frame)
        led_config_frame.grid(row=row, column=1, sticky='w')
        led_config = self.config.get("led_config", {})
        self.led_top_var = tk.StringVar(value=str(led_config.get("top", 30)))
        self.led_right_var = tk.StringVar(value=str(led_config.get("right", 20)))
        self.led_bottom_var = tk.StringVar(value=str(led_config.get("bottom", 30)))
        self.led_left_var = tk.StringVar(value=str(led_config.get("left", 20)))
        self.enable_corners_var = tk.BooleanVar(value=self.config.get("corners_enabled", True))

        self.led_top = ttk.Entry(led_config_frame, width=4, textvariable=self.led_top_var)
        self.led_right = ttk.Entry(led_config_frame, width=4, textvariable=self.led_right_var)
        self.led_bottom = ttk.Entry(led_config_frame, width=4, textvariable=self.led_bottom_var)
        self.led_left = ttk.Entry(led_config_frame, width=4, textvariable=self.led_left_var)

        # Change Button
        ttk.Button(led_config_frame, text="Change", command=self.show_led_preview_window).grid(row=2, column=0, columnspan=4, pady=(5, 0))


        # === Serial Port ===
        row += 1
        ttk.Label(frame, text="Serial Port:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.serial_port_combo = ttk.Combobox(frame, values=self.get_serial_ports(), state='readonly', width=entry_width)
        serial_port_var = tk.StringVar(value=str(self.config.get("serial_port", "COM3")))
        self.serial_port_combo.set(serial_port_var.get())
        self.serial_port_combo.grid(row=row, column=1, sticky='w')

        # === Baud Rate ===
        row += 1
        ttk.Label(frame, text="Baud Rate:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        baud_rates = [9600, 19200, 38400, 57600, 115200, 250000, 1000000]
        self.baud_rate_combo = ttk.Combobox(frame, values=baud_rates, state='readonly', width=entry_width)
        baud_rate_var = tk.IntVar(value=int(self.config.get("baud_rate", 250000)))
        self.baud_rate_combo.set(baud_rate_var.get())
        self.baud_rate_combo.grid(row=row, column=1, sticky='w')

        # === Margin ===
        row += 1
        ttk.Label(frame, text="Margin:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.margin_entry = ttk.Entry(frame, width=entry_width)
        margin_val = int(self.config.get("margin", 40))
        self.margin_entry.insert(0, str(margin_val))
        self.margin_entry.grid(row=row, column=1, sticky='w')

        # === Update Rate ===
        row += 1
        ttk.Label(frame, text="Update Rate (Hz):", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.update_rate_combo = ttk.Combobox(frame, values=[10, 20, 30, 60], state='readonly', width=entry_width)
        update_rate_val = int(self.config.get("update_rate_hz", 30))
        self.update_rate_combo.set(update_rate_val)
        self.update_rate_combo.grid(row=row, column=1, sticky='w')

        # === Order ===
        row += 1
        ttk.Label(frame, text="LED Order:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.order_combo = ttk.Combobox(frame, values=["Clockwise", "Counter-Clockwise"], state='readonly', width=entry_width)
        order_map = {
            "clockwise": "Clockwise",
            "counterclockwise": "Counter-Clockwise"
        }
        order_key = self.config.get("order", "clockwise")
        order_combo_var = tk.StringVar(value=str(order_map.get(order_key, "Counter-Clockwise")))
        self.order_combo.set(order_combo_var.get())
        self.order_combo.grid(row=row, column=1, sticky='w')

        # === Start Side ===
        row += 1
        ttk.Label(frame, text="Start Side:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.start_side_combo = ttk.Combobox(frame, values=["Top", "Right", "Bottom", "Left"], state='readonly', width=entry_width)
        side = str(self.config.get("start_side", "Bottom")).capitalize()
        start_side_combo_var = tk.StringVar(value=str(side))
        self.start_side_combo.set(start_side_combo_var.get())
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
    def _save_config_to_file(self):
        config = {
            "led_config": {
                "top": int(self.led_top.get()),
                "right": int(self.led_right.get()),
                "bottom": int(self.led_bottom.get()),
                "left": int(self.led_left.get())
            },
            "serial_port": self.serial_port_combo.get(),
            "led_pin": 7,
            "baud_rate": int(self.baud_rate_combo.get()),
            "margin": int(self.margin_entry.get()),
            "update_rate_hz": int(self.update_rate_combo.get()),
            "order": self.order_combo.get().lower().replace("-", ""),
            "start_side": self.start_side_combo.get().lower(),
            "enable_corners": self.enable_corners_var.get(),
            "color_coefs": {
                "coef_r": 1.0, #1.0
                "coef_g": 1.0, #0.67
                "coef_b": 0.9 #0.33
            },
            "brightness": int(self.brightness_var.get()) if hasattr(self, 'brightness_var') else 75,
            "brightness_tolerance": int(self.brightness_tolerance_var.get()) if hasattr(self, 'brightness_tolerance_var') else 20,
            "version": 1
    
        }

        # JSON file save
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
            self.config = config
            logger.info(f"Configuration saved to file: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")


    def save_and_enable(self):
        self._save_config_to_file()
        self.enable_other_tabs()

        if self.on_save:
            self.on_save()


    def enable_other_tabs(self):
        self.notebook.tab(0, state="normal")
        self.notebook.tab(1, state="normal")
        self.notebook.select(0)


    def on_brightness_change(self, value):
        def send():
            try:
                brightness = round(float(value))
                if getattr(self, "last_sent_brightness", None) != brightness:
                    self.last_sent_brightness = brightness
                    if callable(self.on_brightness_change_cb):
                        self.on_brightness_change_cb(brightness)
            except Exception as e:
                logger.error(f"Brightness change error: {e}")
        threading.Thread(target=send, daemon=True).start()
    
    
    def on_brightness_tolerance_change(self, value):
        def send():
            try:
                tolerance = round(float(value))
                if getattr(self, "last_sent_tolerance", None) != tolerance:
                    self.last_sent_tolerance = tolerance
                    self.update_brightness_slider_range()
                    if callable(self.on_tolerance_change_cb):
                        self.on_tolerance_change_cb(tolerance)
            except Exception as e:
                logger.error(f"Brightness Tolerance change error: {e}")
        threading.Thread(target=send, daemon=True).start()


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
        self.brightness_slider.set(self.config.get("brightness",75))
        self.brightness_slider.pack()

        ttk.Label(self.tab_general, text="Brightness Tolerance:").pack(pady=(10, 0))
        self.brightness_tolerance_var = tk.DoubleVar()
        self.brightness_tolerance_slider = ttk.Scale(
            self.tab_general,
            from_=0,
            to=100,
            orient='horizontal',
            variable=self.brightness_tolerance_var,
            command=self.on_brightness_tolerance_change
        )
        self.brightness_tolerance_slider.set(self.config.get("brightness_tolerance",20))
        self.brightness_tolerance_slider.pack()

        self.update_brightness_slider_range()


    def update_brightness_slider_range(self):
        if hasattr(self, 'brightness_slider') and hasattr(self, 'brightness_tolerance_var'):
            tolerance = int(self.brightness_tolerance_var.get())
            
            self.brightness_slider.configure(from_=tolerance)
            
            current_brightness = int(self.brightness_var.get())
            if current_brightness < tolerance:
                self.brightness_var.set(tolerance)

                
    def show_led_preview_window(self):
        hud = LEDPreviewHUD(
            self.window,
            self.led_top_var,
            self.led_right_var,
            self.led_bottom_var,
            self.led_left_var,
            self.order_combo,
            self.start_side_combo,
            self.enable_corners_var
        )
        hud.open()

        
    def _on_close(self):
        self._save_config_to_file()
        if self.window:
            self.window.destroy()
            self.window = None

    def sync_values_from_config(self):
        if not self.config:
                return
            
        brightness = self.config.get("brightness", 75)
        tolerance = self.config.get("brightness_tolerance", 20)
        
        if hasattr(self, 'brightness_var'):
            self.brightness_var.set(brightness)
            
        if hasattr(self, 'brightness_tolerance_var'):
            self.brightness_tolerance_var.set(tolerance)
            
        if hasattr(self, 'brightness_slider') and hasattr(self, 'brightness_tolerance_var'):
            self.update_brightness_slider_range()
            
        logger.info(f"Synced values from config - brightness: {brightness}, tolerance: {tolerance}")