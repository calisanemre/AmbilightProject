import time
import serial
import json
import os
import subprocess
import threading
from tools.logger import setup_logger

logger = setup_logger("DeviceInterface")

class DeviceInterface:
    def __init__(self, port, baudrate, timeout=1, write_timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.serial = None
        self.expected_led_count = None
        self.read_thread = None
        self.should_read = False
        self.connection_stable = False
        self.should_write = False
        self.write_thread = None


    @classmethod
    def from_config(cls, config_path="config/config.json"):
        with open(config_path) as f:
            config = json.load(f)

        port = config.get("serial_port", "COM5")
        baudrate = config.get("baud_rate", 115200)
        instance = cls(port=port, baudrate=baudrate, write_timeout=0.5)
        instance.expected_led_count = sum(config.get("led_config", {}).values())

        logger.info(f"Expected LED count: {instance.expected_led_count}")
        return instance
    

    def start_reading_arduino_output(self):
        if not self.serial or not self.serial.is_open:
            return
        self.should_read = True
        self.read_thread = threading.Thread(target=self._read_arduino_messages, daemon=True)
        self.read_thread.start()
        logger.info("Started reading Arduino output.")


    def stop_reading_arduino_output(self):
            self.should_read = False
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=2)
            logger.info("Stopped reading Arduino output.")

            
    def _read_arduino_messages(self):
        buffer = ""
        while self.should_read and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            if line in ["READY", "ALIVE"] or line.startswith("ERR") or line.startswith("BRIGHTNESS"):
                                logger.info(f"[Arduino] {line}")
                            elif "Expected LEDs" in line or "Baud Rate" in line:
                                logger.info(f"[Arduino] {line}")
                            else:
                                logger.debug(f"[Arduino] {line}")
                time.sleep(0.05)
            except Exception as e:
                if self.should_read:
                    logger.error(f"Arduino read error: {e}")
                break


    def start_writing_loop(self, color_generator, interval=0.1):
        if not self.serial or not self.serial.is_open:
            logger.error("Cannot start writer loop: serial not open.")
            return

        def writer_loop():
            logger.info("Writer loop started.")
            while self.should_write:
                try:
                    colors = next(color_generator)
                    self.send_colors(colors)
                except StopIteration:
                    logger.info("Color generator exhausted. Exiting writer loop.")
                    break
                except Exception as e:
                    logger.error(f"Writer error: {e}")
                time.sleep(interval)
            logger.info("Writer loop ended.")

        self.should_write = True
        self.write_thread = threading.Thread(target=writer_loop, daemon=True)
        self.write_thread.start()


    def stop_writing_loop(self):
        self.should_write = False
        if hasattr(self, "write_thread") and self.write_thread is not None and self.write_thread.is_alive():
            self.write_thread.join(timeout=2)
            

    def send_colors(self, led_colors):
        if not self.serial or not self.serial.is_open:
            logger.error("Serial connection is not open.")
            return False

        try:
            if self.expected_led_count and len(led_colors) != self.expected_led_count:
                logger.warning(f"Expected {self.expected_led_count} LEDs, but received {len(led_colors)}.")

            data = bytearray()
            data.append(ord('d'))  # Header
            
            for r, g, b in led_colors:
                r = max(0, min(255, int(r)))
                g = max(0, min(255, int(g)))
                b = max(0, min(255, int(b)))
                data += bytes([r, g, b])

            self.serial.write(data)
            self.serial.flush()

            time.sleep(0.01)
            return True
            
        except Exception as e:
            logger.error(f"Data transmission error: {e}")
            return False


    def send_test_colors(self):
        logger.info("Sending test colors...")
        colors = {
            "red": [(255, 0, 0)],
            "green": [(0, 255, 0)],
            "blue": [(0, 0, 255)],
            "off": [(0, 0, 0)]
        }
        for color_name, color in colors.items():
            self.send_colors(color * (self.expected_led_count or 10))
            logger.debug(f"{color_name.capitalize()} color sent.")
            time.sleep(1)
        logger.info("Test colors completed.")


    def connect(self, max_wait=5):
        def wait_for_port(port, timeout=5):
            start = time.time()
            while time.time() - start < timeout:
                try:
                    s = serial.Serial(port, timeout=0.1)
                    s.close()
                    return True
                except serial.SerialException:
                    time.sleep(0.5)
            return False
        
        def wait_for_ready(timeout=10):
            buffer = ""
            start_time = time.time()
            ready_received = False
            while time.time() - start_time < timeout:
                if self.serial.in_waiting:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    if "READY" in buffer and not ready_received:
                        logger.info("Arduino ready message received.")
                        ready_received = True
                        return True
                time.sleep(0.1)
            logger.warning(f"Timeout waiting for Arduino READY message. Buffer: {buffer[-100:]}")
            return False

        try:
            if self.serial and self.serial.is_open:
                logger.info("Closing existing serial connection...")
                self.stop_reading_arduino_output()
                self.serial.close()
                time.sleep(1)
                
            logger.info(f"Waiting for port {self.port} to become available...")
            if not wait_for_port(self.port, timeout=max_wait):
                logger.error(f"Port {self.port} not available after {max_wait} seconds.")
                return False

            self.serial = serial.Serial()
            self.serial.port = self.port
            self.serial.baudrate = self.baudrate
            self.serial.timeout = self.timeout
            self.serial.write_timeout = self.write_timeout
            self.serial.dtr = False 
            self.serial.rts = False
            self.serial.open()
            logger.info(f"Serial port {self.port} opened successfully.")
            time.sleep(3)
            
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            if not wait_for_ready(timeout=10):
                logger.error("Arduino did not send READY message.")
                return False

            self.start_reading_arduino_output()
            time.sleep(0.5)

            if not self.check_arduino_health():
                logger.error("Arduino health check failed after connection.")
                return False
            self.connection_stable = True
            logger.info("Arduino communication established successfully.")
            #self.send_test_colors()
            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_stable = False
            return False


    def close_leds(self):
        off_colors = [(0,0,0)] * (self.expected_led_count or 1)
        self.send_colors(off_colors)
        time.sleep(0.1)    


    def disconnect(self):
        self.stop_reading_arduino_output()
        if self.serial and self.serial.is_open:
            try:
                self.close_leds()
            except:
                pass
                
            self.serial.close()
            self.serial = None
            logger.info("Serial port closed.")


    def check_arduino_health(self):
        if not self.serial or not self.serial.is_open:
            return False
        try:
            self.serial.reset_input_buffer()
            
            self.serial.write(b't')
            self.serial.flush()
            
            start_time = time.time()
            buffer = ""
            while time.time() - start_time < 3:
                if self.serial.in_waiting:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    if "ALIVE" in buffer:
                        logger.debug("Arduino health check passed.")
                        return True
                time.sleep(0.1)
            
            logger.warning(f"Arduino health check timeout. Received: '{buffer.strip()}'")
            if "READY" in buffer or len(buffer.strip()) == 0:
                logger.info("Arduino seems ready despite health check timeout.")
                return True
            return False
        except Exception as e:
            logger.error(f"Arduino health check failed: {e}")
            return False


    def generate_ino(self, config_path="config/config.json", template_path="arduino/arduino_template.tmpl", output_dir="arduino"):
        with open(config_path) as f:
            config = json.load(f)

        led_config = config["led_config"]
        num_leds = sum(led_config.values())
        led_pin = config.get("led_pin", 7)
        baud = config.get("baud_rate", 115200)

        with open(template_path, "r") as f:
            template = f.read()

        rendered = template.replace("{{LED_PIN}}", str(led_pin)) \
                           .replace("{{NUM_LEDS}}", str(num_leds)) \
                           .replace("{{BAUD_RATE}}", str(baud))

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "arduino.ino")
        with open(output_path, "w") as f:
            f.write(rendered)

        logger.info(f".ino file generated at: {output_path}")
        return output_path
    

    def upload_ino(self, sketch_dir="arduino", fqbn="arduino:avr:uno"):
        try:
            if self.serial and self.serial.is_open:
                self.stop_reading_arduino_output()
                self.serial.close()
                time.sleep(2)

            compile_cmd = ["arduino-cli", "compile", "--fqbn", fqbn, sketch_dir]
            upload_cmd = ["arduino-cli", "upload", "--fqbn", fqbn, "-p", self.port, sketch_dir]

            subprocess.run(compile_cmd, check=True)
            subprocess.run(upload_cmd, check=True)

            logger.info("Sketch uploaded successfully.")

            #self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(3)
            self.start_reading_arduino_output()

            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Sketch upload failed: {e}")
            return False
        

        