import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.device_interface import DeviceInterface
from engine.screen_capture import ScreenCapturer
from engine.color_processor import ColorProcessor
from gui.settings_window import SettingsWindow
import tkinter as tk
import threading
import pystray
from PIL import Image
import time
from tools.logger import setup_logger
import queue

logger = setup_logger("TrayApp")
CONFIG_FILE = "config/config.json"

class TrayApp:
    def __init__(self):
        self.running = False
        self.is_device_connected = False
        self.config_path = CONFIG_FILE
        self.settings_ui = SettingsWindow(
            config_file=self.config_path,
            on_save=self._on_config_saved,
            on_brightness_change_cb=self.set_brightness,
            on_tolerance_change_cb=self.set_brightness_tolerance,
            get_current_values_cb=self.get_current_values
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
        if hasattr(self, "settings_ui") and hasattr(self.settings_ui, "brightness_var"):
            self.settings_ui.brightness_var.set(brightness)


    def set_brightness_tolerance(self, brightness_tolerance):
        old_tolerance = self.current_brightness_tolerance
        new_tolerance = brightness_tolerance
        
        old_scale_range = 100 - old_tolerance
        current_brightness_in_old_scale = (self.current_brightness / 100.0) * old_scale_range
        actual_brightness_255 = old_tolerance + current_brightness_in_old_scale
        
        new_scale_range = 100 - new_tolerance
        
        if new_scale_range > 0:
            new_brightness_in_scale = max(0, actual_brightness_255 - new_tolerance)
            new_brightness_percentage = (new_brightness_in_scale / new_scale_range) * 100.0
            new_brightness_percentage = max(0, min(100, new_brightness_percentage))
        else:
            new_brightness_percentage = 0
        
        self.current_brightness_tolerance = brightness_tolerance
        self.set_brightness(int(new_brightness_percentage))
        
        if hasattr(self, "settings_ui"):
            if hasattr(self.settings_ui, "brightness_tolerance_var"):
                self.settings_ui.brightness_tolerance_var.set(brightness_tolerance)
            if hasattr(self.settings_ui, "update_brightness_slider_range"):
                self.settings_ui.update_brightness_slider_range()
    
    
    def get_current_values(self):
        return self.current_brightness, self.current_brightness_tolerance

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
            
            # Upload
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


    def start_tray_app(self):
        # (Optional) Hide console on Windows
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        logger.info("TrayApp started.")
        app = TrayApp()
        self.run()
