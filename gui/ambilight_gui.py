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
from tools.logger import setup_logger
import queue

logger = setup_logger("TrayApp")
CONFIG_FILE = "config/config.json"

class SettingsWindow:
    def __init__(self, on_save=None, on_brightness_change_cb = None, on_tolerance_change_cb = None):
        self.window = None
        self.notebook = None
        self.config = None
        self.config_file = CONFIG_FILE
        self.config_loaded = self.load_config_if_exists()
        self.on_save = on_save
        self.on_brightness_change_cb = on_brightness_change_cb
        self.last_sent_brightness = None
        self.on_tolerance_change_cb = on_tolerance_change_cb
        self.last_sent_tolerance = None

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

        self.notebook.add(self.tab_general, text="Light Settings",
                        state="normal" if self.config_loaded else "disabled")
        self.notebook.add(self.tab_configure, text="Configure")

        self.notebook.pack(fill='both', expand=True)

        self.setup_general_tab()
        self.setup_configure_tab()

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

        # Entry'leri tanımlarken DoubleVar bağla
        self.led_top_var = tk.StringVar(value="30")
        self.led_right_var = tk.StringVar(value="20")
        self.led_bottom_var = tk.StringVar(value="30")
        self.led_left_var = tk.StringVar(value="20")
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
        self.order_combo.set("Counter-Clockwise")
        self.order_combo.grid(row=row, column=1, sticky='w')

        # === Start Side ===
        row += 1
        ttk.Label(frame, text="Start Side:", width=label_width, anchor='w').grid(row=row, column=0, pady=5, sticky='w')
        self.start_side_combo = ttk.Combobox(frame, values=["Top", "Right", "Bottom", "Left"], state='readonly', width=entry_width)
        self.start_side_combo.set("Right")
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
            "start_side": self.start_side_combo.get().lower(),
            "enable_corners": self.enable_corners_var.get()
        }

        # JSON file save
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuration saved to file: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

        #self.config_loaded = True
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
            command=self.on_brightness_change
        )
        self.brightness_tolerance_slider.set(self.config.get("brightnes_tolerance",20))
        self.brightness_tolerance_slider.pack()


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

class LEDPreviewHUD:
    def __init__(self, master, led_top_var, led_right_var, led_bottom_var, led_left_var, order_combo, start_side_combo, enable_corners_var):
        self.master = master
        self.led_top_var = led_top_var
        self.led_right_var = led_right_var
        self.led_bottom_var = led_bottom_var
        self.led_left_var = led_left_var
        self.order_combo = order_combo
        self.start_side_combo = start_side_combo
        self.enable_corners_var = enable_corners_var
        self.hud_window = None
        self.hud_canvas = None

    def open(self):
        self._open_hud()
        self.master.after(200, self._open_editor)

    def _open_hud(self):
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        self.hud_window = tk.Toplevel()
        self.hud_window.overrideredirect(True)
        self.hud_window.attributes("-topmost", True)
        self.hud_window.attributes("-transparentcolor", "white")
        self.hud_window.geometry(f"{screen_width}x{screen_height}+0+0")

        self.hud_canvas = tk.Canvas(self.hud_window, bg="white", highlightthickness=0)
        self.hud_canvas.pack(fill="both", expand=True)
        self.hud_window.bind("<Escape>", lambda e: self.close())
        self.hud_window.protocol("WM_DELETE_WINDOW", self.close)

        self.redraw()

    def _open_editor(self):
        config_popup = tk.Toplevel()
        config_popup.title("Edit LED Configuration")
        config_popup.geometry("340x260")
        config_popup.resizable(False, False)
        config_popup.bind("<Escape>", lambda e: self.close())
        config_popup.protocol("WM_DELETE_WINDOW", lambda: [config_popup.destroy(), self.close()])
        # LED yönleri için yapı
        labels = ["Top", "Right", "Bottom", "Left"]
        vars = [self.led_top_var, self.led_right_var, self.led_bottom_var, self.led_left_var]
        entries = []

        for i, (label, var) in enumerate(zip(labels, vars)):
            tk.Label(config_popup, text=f"{label}:").grid(row=i, column=0, padx=10, pady=5, sticky="w")

            entry = tk.Entry(config_popup, width=6)
            entry.insert(0, var.get())
            entry.grid(row=i, column=1)
            entries.append(entry)

            def make_stepper(e=entry, v=var, delta=1):
                def step():
                    try:
                        val = max(0, int(e.get()) + delta)
                        e.delete(0, tk.END)
                        e.insert(0, str(val))
                        v.set(str(val))
                        self.redraw()
                    except:
                        pass
                return step

            tk.Button(config_popup, text="–", width=2, command=make_stepper(delta=-1)).grid(row=i, column=2, padx=(5,0))
            tk.Button(config_popup, text="+", width=2, command=make_stepper(delta=1)).grid(row=i, column=3)

        corner_check = tk.Checkbutton(
            config_popup,
            text="Enable Corners",
            variable=self.enable_corners_var,
            command=self.redraw
        )
        corner_check.grid(row=5, column=0, columnspan=3, pady=(10, 5), sticky="w")


        def apply():
            for entry, var in zip(entries, vars):
                var.set(entry.get())
            self.redraw()
            config_popup.destroy()
            self.close()
            
        tk.Button(config_popup, text="Apply", command=apply).grid(row=6, column=0, columnspan=4, pady=10)

    
    def redraw(self):
        if not self.hud_canvas:
            return

        self.hud_canvas.delete("all")

        try:
            top = int(self.led_top_var.get())
            right = int(self.led_right_var.get())
            bottom = int(self.led_bottom_var.get())
            left = int(self.led_left_var.get())
        except:
            top = right = bottom = left = 0

        w = self.hud_window.winfo_screenwidth()
        h = self.hud_window.winfo_screenheight()
        thickness = 25
        enable_corners = self.enable_corners_var.get()

        order = self.order_combo.get().lower().replace("-", "")
        start = self.start_side_combo.get().lower()

        corners = ["top-right", "bottom-right", "bottom-left", "top-left"]
        edges = ["top", "right","bottom", "left"]
        sides = []
        for i , _ in enumerate(edges):
            sides.append(edges[i])
            sides.append(corners[i])

        if order == "counterclockwise":
            sides = sides[::-1]
        start_index = sides.index(start)
        draw_order = sides[start_index:] + sides[:start_index]

        led_counts = {"top": top, "right": right, "bottom": bottom, "left": left}
        index = 0

        for side in draw_order:
            if side in corners:
                if enable_corners:
                    if side == "top-right":
                        x1 = w - thickness
                        x2 = w
                        y1, y2 = 0, thickness
                    if side == "bottom-right":
                        x1 = w - thickness
                        x2 = w
                        y1, y2 = h-thickness, h
                    if side == "bottom-left":
                        x1 = 0
                        x2 = thickness
                        y1, y2 = h-thickness, h
                    if side == "top-left":
                        x1 = 0
                        x2 = thickness
                        y1, y2 = 0, thickness
                    self.hud_canvas.create_rectangle(x1, y1, x2, y2, fill="gray", outline="black")
                    self.hud_canvas.create_text((x1+x2)/2, (y1+y2)/2, text=str(index + 1), fill="#fffffe", font=("Arial", 14, "bold"))
                    index += 1
                continue
            
            count = led_counts[side]
            for i in range(count):
                i_normal = i

                if side == "bottom" or side == "left":
                    if order == "clockwise":
                        i_normal = count - 1 - i 
                else:
                    if order == "counterclockwise":
                        i_normal = count - 1 - i 

                if side == "top":
                    x1 = thickness + (w - 2 * thickness) * i_normal / count
                    x2 = thickness + (w - 2 * thickness) * (i_normal + 1) / count
                    y1, y2 = 0, thickness
                elif side == "bottom":
                    x1 = thickness + (w - 2 * thickness) * i_normal / count
                    x2 = thickness + (w - 2 * thickness) * (i_normal + 1) / count
                    y1, y2 = h - thickness, h
                elif side == "left":
                    y1 = thickness + (h - 2 * thickness) * i_normal / count
                    y2 = thickness + (h - 2 * thickness) * (i_normal + 1) / count
                    x1, x2 = 0, thickness
                elif side == "right":
                    y1 = thickness + (h - 2 * thickness) * i_normal / count
                    y2 = thickness + (h - 2 * thickness) * (i_normal + 1) / count
                    x1, x2 = w - thickness, w

                self.hud_canvas.create_rectangle(x1, y1, x2, y2, fill="gray", outline="black")
                self.hud_canvas.create_text((x1+x2)/2, (y1+y2)/2, text=str(index + 1), fill="#fffffe", font=("Arial", 14, "bold"))
                index += 1


    def close(self):
        if self.hud_canvas:
            self.hud_canvas.delete("all")
            self.hud_window.destroy()
            self.hud_window = None
            self.hud_canvas = None
            

class TrayApp:
    def __init__(self):
        self.running = False
        self.is_device_connected = False
        self.config_path = CONFIG_FILE
        self.settings_ui = SettingsWindow(
            on_save=self._on_config_saved,
            on_brightness_change_cb=self.set_brightness,
            on_tolerance_change_cb=self.set_brightness_tolerance
            )
        
        if self.settings_ui.config_loaded:
            self._initialize_components()
        self.current_brightness = self.settings_ui.config.get("brightness", 75)
        self.current_brightness_tolerance = self.settings_ui.config.get("brightness_tolerance", 20)
        self.tray_icon = None
        self.on_icon_path = "assets/led_on.png"
        self.off_icon_path = "assets/led_off.png"

        self.color_queue = queue.Queue(maxsize=3) 
        self.capture_thread = None

        self.stats = {
            "frames_captured": 0,
            "frames_sent": 0,
            "capture_errors": 0,
            "send_errors": 0,
            "last_stats_time": time.time()
        }


    def _on_config_saved(self):
        logger.info("Configuration saved. Initializing components...")
        self._initialize_components()


    def set_brightness(self, brightness):
        self.current_brightness = brightness

    def set_brightness_tolerance(self, brightness_tolerance):
        self.current_brightness_tolerance = brightness_tolerance

        # Yeni toleransla birlikte parlaklık aralığını yeniden hesapla
        clip = self.current_brightness_tolerance
        scale_range = max(1, 255 - clip)

        # %'lik parlaklığı bu yeni aralığa göre normalize et
        brightness_percent = self.current_brightness / 100.0
        effective_brightness = clip + brightness_percent * scale_range
        effective_brightness_percent = (effective_brightness / 255) * 100

        # Güncel parlaklığı yeni skala ile tekrar uygula
        self.set_brightness(effective_brightness_percent)   


    def _initialize_components(self):
        logger.info("Initializing components...")
        
        try:
            self.color_processor = ColorProcessor.from_config(self.config_path)
            logger.info("Color processor initialized.")
            
            self.screen_capturer = ScreenCapturer()
            logger.info("Screen capturer initialized.")
            
            self.device = DeviceInterface.from_config(self.config_path)
            logger.info(f"Device interface created: {self.device.port}")
            
            # Generate INO
            ino_path = self.device.generate_ino()
            logger.info(f".ino file generated: {ino_path}")
            
            # Upload (optional, comment out if not needed)
            logger.info("Uploading sketch...")
            upload_success = self.device.upload_ino()
            logger.info("Sketch upload successful.") if upload_success else logger.error("Sketch upload failed.")
            
            # Connect
            logger.info("Connecting to device...")
            connect_success = self.device.connect()
            logger.info("Device connected successfully.") if connect_success else logger.error("Device connection failed.")
            
            self.is_device_connected = connect_success
            
            if self.is_device_connected:
                logger.info("System is ready.")
            else:
                logger.warning("System not ready - check device connection.")
                
        except Exception as e:
            logger.error(f"Component initialization error: {e}")
            self.is_device_connected = False


    def create_queue_color_generator(self):
        consecutive_empty = 0
        
        while self.running:
            try:
                colors = self.color_queue.get(timeout=0.05)
                self.color_queue.task_done()
                consecutive_empty = 0
                self.stats["frames_sent"] += 1
                yield colors
                
            except queue.Empty:
                consecutive_empty += 1
                if consecutive_empty == 1:
                    logger.debug("Color queue empty, sending black")
                yield [(0, 0, 0)] * (self.device.expected_led_count or 1)
                
            except Exception as e:
                logger.error(f"Queue generator error: {e}")
                self.stats["send_errors"] += 1
                yield [(0, 0, 0)] * (self.device.expected_led_count or 1)


    def screen_capture_worker(self):
        if not self.settings_ui.config:
            logger.error("No config available for capture worker")
            return
            
        update_rate = self.settings_ui.config.get("update_rate_hz", 30)
        interval = 1.0 / update_rate
        
        logger.info(f"Screen capture worker started at {update_rate} FPS (interval: {interval:.3f}s)")
        
        consecutive_errors = 0
        last_stats_log = time.time()
        
        while self.running:
            frame_start = time.time()
            
            try:
                # 1. Capture frame
                frame = self.screen_capturer.capture_screen()
                if frame is None:
                    logger.warning("Screen capture failed")
                    consecutive_errors += 1
                    time.sleep(interval)
                    continue
                
                # 2. Process colors
                raw_colors = self.color_processor.get_led_colors(frame)
                brightness_n = self.current_brightness / 100.0
                colors = self.color_processor.adjust_and_correct_colors(
                    colors=raw_colors, 
                    brightness=brightness_n,
                    min_brightness_clip=self.current_brightness_tolerance
                )
                
                if not colors:
                    colors = [(0, 0, 0)] * (self.device.expected_led_count or 1)
                
                # 3. Add to queue
                try:
                    while self.color_queue.qsize() >= self.color_queue.maxsize:
                        try:
                            self.color_queue.get_nowait()
                            self.color_queue.task_done()
                        except queue.Empty:
                            break
                    
                    self.color_queue.put_nowait(colors)
                    self.stats["frames_captured"] += 1
                    consecutive_errors = 0
                    
                except queue.Full:
                    logger.debug("Color queue full, dropping frame")
                
            except Exception as e:
                consecutive_errors += 1
                self.stats["capture_errors"] += 1
                logger.error(f"Screen capture worker error #{consecutive_errors}: {e}")
                
                if consecutive_errors > 10:
                    logger.error("Too many capture errors, stopping capture worker")
                    break
            
            current_time = time.time()
            if current_time - last_stats_log > 30:
                elapsed = current_time - self.stats["last_stats_time"]
                fps_captured = self.stats["frames_captured"] / elapsed if elapsed > 0 else 0
                fps_sent = self.stats["frames_sent"] / elapsed if elapsed > 0 else 0
                
                logger.info(f"Stats: Captured {fps_captured:.1f} FPS, Sent {fps_sent:.1f} FPS, "
                          f"Queue size: {self.color_queue.qsize()}, "
                          f"Errors: {self.stats['capture_errors']} capture, {self.stats['send_errors']} send")
                
                # Reset stats
                self.stats = {
                    "frames_captured": 0,
                    "frames_sent": 0,
                    "capture_errors": 0,
                    "send_errors": 0,
                    "last_stats_time": current_time
                }
                last_stats_log = current_time
            
            # Frame timing
            frame_time = time.time() - frame_start
            sleep_time = max(0, interval - frame_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif frame_time > interval * 1.5:
                logger.debug(f"Capture frame took {frame_time:.3f}s (target: {interval:.3f}s)")
        
        logger.info("Screen capture worker ended.")


    def start_system(self):
        if not self.is_device_connected:
            self.update_icon()
            logger.warning("Cannot start system: No device connected.")
            return
        logger.info("System started.")
        self.running = True
        self.update_icon()
        while not self.color_queue.empty():
            try:
                self.color_queue.get_nowait()
                self.color_queue.task_done()
            except queue.Empty:
                break
        
        self.capture_thread = threading.Thread(target=self.screen_capture_worker, daemon=True)
        self.capture_thread.start()
        
        color_generator = self.create_queue_color_generator()
        
        update_rate = self.settings_ui.config.get("update_rate_hz", 30)
        send_interval = 1.0 / (update_rate * 1.1)  # %10 faster (?)
        
        self.device.start_writing_loop(color_generator, interval=send_interval)
        
        logger.info(f"System started with {update_rate} Hz capture, {1/send_interval:.1f} Hz send rate")



    def stop_system(self):
        logger.info("System stopped.")
        self.running = False
        self.update_icon()
        if hasattr(self, "device") and self.device:
            self.device.stop_writing_loop()
            try:
                self.device.close_leds()
            except Exception as e:
                logger.error(f"Error closing LEDs: {e}")
        
        if self.capture_thread and self.capture_thread.is_alive():
            logger.info("Waiting for capture thread to stop...")
            self.capture_thread.join(timeout=3)
            if self.capture_thread.is_alive():
                logger.warning("Capture thread did not stop gracefully")
        
        while not self.color_queue.empty():
            try:
                self.color_queue.get_nowait()
                self.color_queue.task_done()
            except queue.Empty:
                break
                
        logger.info("System stopped.")


    def open_settings(self, _=None):
        self.root.after(0, self.settings_ui.show)


    def quit_app(self, _=None):
        logger.info("Quitting application...")
        self.running = False

        if hasattr(self, "device") and self.device:
            try:
                self.device.stop_writing_loop()
            except Exception as e:
                logger.error(f"Error stopping write loop: {e}")
                
            try:
                self.device.close_leds()
            except Exception as e:
                logger.error(f"Error closing LEDs during quit: {e}")
                
            try:
                self.device.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting device: {e}")

        if hasattr(self, "capture_thread") and self.capture_thread is not None and self.capture_thread.is_alive():
            logger.info("Waiting for capture thread to stop...")
            self.capture_thread.join(timeout=3)
            if self.capture_thread.is_alive():
                logger.warning("Capture thread did not stop gracefully")

        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception as e:
                logger.error(f"Error stopping tray icon: {e}")

        if hasattr(self, "root") and self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except Exception as e:
                logger.error(f"Error closing GUI: {e}")

        os._exit(0)


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
                if hasattr(self, "device") and self.device:
                    self.device.close_leds()
            else:
                self.start_system()
        else:
            logger.warning("Configuration not loaded. Please check your settings.")


if __name__ == "__main__":
    # (Optional) Hide console on Windows
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    logger.info("TrayApp started.")
    app = TrayApp()
    app.run()
