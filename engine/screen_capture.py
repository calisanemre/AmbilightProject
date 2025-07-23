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

    def capture_screen(self):
        """
        Capture the screen as an RGB NumPy array.
        """
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[self.monitor_index]
                screenshot = sct.grab(monitor)
                img_bgr = np.array(screenshot)[:, :, :3]
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                return img_rgb
        except Exception as e:
            print(f"[ScreenCapturer/capture_screen] -> {e}")
            return None
        
    def preview(self):
        """
        Show the captured screen in a window (for debug/testing).
        """
        frame = self.capture_screen()
        if frame is not None:
            cv2.imshow("Screenshot", frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("[ScreenCapturer/preview] Error!")
        