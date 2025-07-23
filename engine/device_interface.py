import time
import serial
import json
import os
import subprocess

class DeviceInterface:
    def __init__(self, port, baudrate, timeout = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None


    @classmethod
    def from_config(cls, config_path="config/config.json"):
        with open(config_path) as f:
            config = json.load(f)

        port = config.get("serial_port", "COM3")
        baudrate = config.get("baud_rate", 115200)
        return cls(port=port, baudrate=baudrate)


    def generate_ino(self, config_path="config/config.json", template_path="arduino/arduino_template.tmpl", output_dir="arduino"):
        with open(config_path) as f:
            config = json.load(f)

        led_config = config["led_config"]
        num_leds = sum(led_config.values())
        led_pin = config.get("led_pin", 6)
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

        print(f"[DeviceInterface] .ino file generated at {output_path}")
        return output_path


    def upload_ino(self, sketch_dir="arduino", fqbn="arduino:avr:uno"):
        try:
            compile_cmd = ["arduino-cli", "compile", "--fqbn", fqbn, sketch_dir]
            upload_cmd = ["arduino-cli", "upload", "--fqbn", fqbn, "-p", self.port, sketch_dir]

            subprocess.run(compile_cmd, check=True)
            subprocess.run(upload_cmd, check=True)

            print("[DeviceInterface] Sketch uploaded successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[DeviceInterface] Upload failed: {e}")


    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)
            print(f"[DeviceInterface] Connected: {self.port}")
        except Exception as e:
            print(f"[DeviceInterface] Connection error: {e}")


    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("[DeviceInterface] Serial port closed.")


    def send_colors(self, led_colors):
        if not self.serial or not self.serial.is_open:
            print("[DeviceInterface] Serial connection is not open.")
            return

        try:
            data = bytearray()
            for color in led_colors:
                r, g, b = color
                data += bytes([r, g, b])
            self.serial.write(data)
        except Exception as e:
            print(f"[DeviceInterface] Data transmission error: {e}")

    def send_brightness(self, brightness_level):
        if not self.serial or not self.serial.is_open:
            print("[DeviceInterface] Serial connection not open.")
            return

        try:
            # Protokol: b{value}\n → örn. b128
            command = f"b{brightness_level}\n"
            self.serial.write(command.encode())
            print(f"[DeviceInterface] Brightness command sent: {brightness_level}")
        except Exception as e:
            print(f"[DeviceInterface] Brightness command error: {e}")
