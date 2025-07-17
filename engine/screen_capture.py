import mss
import cv2
import numpy as np

class ScreenCapturer:
    def __init__(self, monitor_index = 1):
        """
        Monitor Index:
            0 = all screens combined
            1 = primary screen
            2 = secondary screen
            ...
        """
        self.monitor_index = monitor_index
        self.mss_instance = mss.mss()

    def capture(self):
        """
        Capture the screen as an RGB NumPy array.
        """
        try:
            monitor = self.mss_instance.monitors[self.monitor_index]
            screenshot = self.mss_instance.grab(monitor)
            img = np.array(screenshot)[:, :, :3]
            return img
        except Exception as e:
            print(f"[ScreenCapturer/capture] -> {e}")
            return None
        
    def preview(self):
        """
        Show the captured screen in a window (for debug/testing).
        """
        frame = self.capture()
        if frame is not None:
            cv2.imshow("Screenshot", frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("[ScreenCapturer/preview] Error!")
        