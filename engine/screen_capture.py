import mss
import cv2
import numpy as np
from tools.logger import setup_logger

logger = setup_logger("ScreenCapturer")

class ScreenCapturer:
    def __init__(self, monitor_index=1):
        """
        monitor_index:
            0 = all screens combined
            1 = primary screen
            2 = secondary screen
            ...
        """
        with mss.mss() as sct:
            available_monitors = len(sct.monitors) - 1
            if monitor_index > available_monitors:
                logger.warning(f"Monitor {monitor_index} does not exist. Available monitors: {available_monitors}. Defaulting to monitor 1.")
                monitor_index = 1
            elif monitor_index < 0:
                logger.warning("Negative monitor index is invalid. Defaulting to monitor 1.")
                monitor_index = 1

        self.monitor_index = monitor_index
        logger.info(f"Using monitor {self.monitor_index} for screen capture.")


    def capture_screen(self):
        """
        Capture the screen as an RGB NumPy array.
        """
        try:
            with mss.mss() as sct:
                if self.monitor_index >= len(sct.monitors):
                    logger.error(f"Monitor {self.monitor_index} is no longer available.")
                    return None

                monitor = sct.monitors[self.monitor_index]
                screenshot = sct.grab(monitor)

                img_bgra = np.array(screenshot)
                img_bgr = img_bgra[:, :, :3]
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

                return img_rgb

        except Exception as e:
            logger.exception(f"Failed to capture screen: {e}")
            return None

        
    def preview(self, duration=5000):
        """
        Show the captured screen in a window (for debug/testing).
        Args:
            duration: Display time in milliseconds. 0 = until key press.
        """
        frame = self.capture_screen()
        if frame is not None:
            h, w = frame.shape[:2]
            if w > 1200:
                scale = 1200 / w
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

            try:
                cv2.imshow(f"Monitor {self.monitor_index} Preview", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                cv2.waitKey(duration)
                cv2.destroyAllWindows()
            except Exception as e:
                logger.error(f"Failed to preview screen: {e}")
        else:
            logger.warning("Could not preview screen: No frame captured.")