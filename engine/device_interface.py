import time
import serial

class DeviceInterface:
    def __init__(self, port = "COM3", baudrate = 115200, timeout = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Arduino'nun yeniden başlama süresi
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