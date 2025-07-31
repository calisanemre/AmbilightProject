import cv2
import math
import numpy as np
import json
from tools.logger import setup_logger

logger = setup_logger("ColorProcessor")

class ColorProcessor: 

    def __init__(self, led_config, margin=40, order="clockwise", start_side="bottom", enable_corners=False, gamma=2.2, coef_r=1.0, coef_g=1.0, coef_b=1.0):
        self.coef_r = coef_r
        self.coef_g = coef_g
        self.coef_b = coef_b
        self.gamma_table = np.array([int((i / 255) ** (1 / gamma) * 255 + 0.5) for i in range(256)], dtype=np.uint8)
        self.led_config = led_config
        self.margin = max(1, int(margin))
        self.order = order.lower().replace("-", "").replace("_", "")
        self.start_side = start_side.lower()
        self.enable_corners = enable_corners

        total_leds = sum(self.led_config.values())
        logger.info(f"Initialized with {total_leds} LEDs, margin={self.margin}, order={self.order}")

    @classmethod
    def from_config(cls, config_path="config/config.json"):
        try:
            with open(config_path) as f:
                config = json.load(f)

            led_config = config.get("led_config", {"top": 10, "right": 6, "bottom": 10, "left": 6})
            margin = config.get("margin", 40)
            order = config.get("order", "clockwise")
            start_side = config.get("start_side", "bottom")
            enable_corners = config.get("enable_corners", False)
            coef_r = config.get("color_coefs", {}).get("coef_r", 1.0)
            coef_g = config.get("color_coefs", {}).get("coef_g", 1.0)
            coef_b = config.get("color_coefs", {}).get("coef_b", 1.0)


            logger.info(f"Configuration loaded from {config_path}: {led_config}")

            return cls(
                led_config=led_config, 
                margin=margin, 
                order=order, 
                start_side=start_side, 
                enable_corners=enable_corners,
                coef_r=coef_r,
                coef_g=coef_g,
                coef_b=coef_b
            )
        
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return cls({"top": 10, "right": 6, "bottom": 10, "left": 6})
    
    def get_led_colors(self, image):
        if image is None:
            logger.warning("Input image is None!")
            return []
            
        try:
            h, w, _ = image.shape
            logger.debug(f"Processing image of size: {w}x{h}")

            # Margin check
            if self.margin * 2 >= min(w, h):
                logger.warning(f"Margin {self.margin} is too large for image size {w}x{h}, reducing margin.")
                self.margin = min(w, h) // 4

            corner_margin = 0
            if self.enable_corners:
                corner_margin = self.margin

            colors = []

            def gaussian_weighted_average(image_region, sigma=1.0, kernel_size=None):
                
                if image_region.size == 0:
                    return np.array([0, 0, 0], dtype=np.uint8)
                
                try:
                    h, w = image_region.shape[:2]
                    
                    if kernel_size is None:
                        kernel_size = min(max(5, min(h, w) // 4), 15)
                        kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
                    
                    center = kernel_size // 2
                    kernel = np.zeros((kernel_size, kernel_size))
                    
                    for i in range(kernel_size):
                        for j in range(kernel_size):
                            x, y = i - center, j - center
                            kernel[i, j] = math.exp(-(x*x + y*y) / (2 * sigma * sigma))
                    
                    kernel = kernel / np.sum(kernel)
                    
                    kernel_resized = cv2.resize(kernel, (w, h))
                    
                    weighted_sum = np.zeros(3)
                    total_weight = np.sum(kernel_resized)
                    
                    for channel in range(3):  # R, G, B
                        channel_data = image_region[:, :, channel].astype(np.float32)
                        weighted_sum[channel] = np.sum(channel_data * kernel_resized)
                    
                    final_color = weighted_sum / total_weight
                    
                    return np.clip(final_color, 0, 255).astype(np.uint8)
                    
                except Exception as e:
                    logger.error(f"Gaussian weighted average failed: {e}")
                    return np.mean(image_region, axis=(0, 1)).astype(np.uint8)

                    
            def smart_segmentation(image_region, num_segments, overlap_ratio=0.1, blur_before_split=True):
                if image_region.size == 0 or num_segments <= 0:
                    return [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(num_segments)]
                
                try:
                    h, w = image_region.shape[:2]
                    
                    if blur_before_split and h > 5 and w > 5:
                        blur_size = max(3, min(h, w) // 10)
                        if blur_size % 2 == 0:
                            blur_size += 1
                        region = cv2.GaussianBlur(image_region, (blur_size, blur_size), 0)
                    else:
                        region = image_region.copy()
                    
                    split_horizontally = w > h
                    
                    segments = []
                    
                    if split_horizontally:
                        segment_width = w / num_segments
                        overlap_pixels = int(segment_width * overlap_ratio)
                        
                        for i in range(num_segments):
                            start = max(0, int(i * segment_width) - overlap_pixels)
                            end = min(w, int((i + 1) * segment_width) + overlap_pixels)
                            
                            if i == 0:
                                start = 0
                            if i == num_segments - 1:
                                end = w
                            
                            segment = region[:, start:end, :]
                            segments.append(segment)
                            
                    else:
                        segment_height = h / num_segments
                        overlap_pixels = int(segment_height * overlap_ratio)
                        
                        for i in range(num_segments):
                            start = max(0, int(i * segment_height) - overlap_pixels)
                            end = min(h, int((i + 1) * segment_height) + overlap_pixels)
                            
                            if i == 0:
                                start = 0
                            if i == num_segments - 1:
                                end = h
                            
                            segment = region[start:end, :, :]
                            segments.append(segment)
                    
                    valid_segments = []
                    for i, segment in enumerate(segments):
                        if segment.size > 0:
                            valid_segments.append(segment)
                    return valid_segments
                    
                except Exception as e:
                    logger.error(f"Smart segmentation failed: {e}")
                    axis = 1 if image_region.shape[1] > image_region.shape[0] else 0
                    return np.array_split(image_region, num_segments, axis=axis)

            # Extract regions with bounds checking
            try:
                top_region = image[0:self.margin, corner_margin:w-corner_margin, :]
                bottom_region = image[h-self.margin:h, corner_margin:w-corner_margin, :]
                left_region = image[corner_margin:h-corner_margin, 0:self.margin, :]
                right_region = image[corner_margin:h-corner_margin, w-self.margin:w, :]
                
                logger.debug(f"Regions extracted: top={top_region.shape}, right={right_region.shape}, bottom={bottom_region.shape}, left={left_region.shape}")
                
            except Exception as e:
                logger.error(f"Failed to extract image regions: {e}")
                return []

            # Process each side
            try:
                top_leds = [gaussian_weighted_average(r) for r in smart_segmentation(top_region, self.led_config['top'])]
                right_leds = [gaussian_weighted_average(r) for r in smart_segmentation(right_region, self.led_config['right'])]
                bottom_leds = [gaussian_weighted_average(r) for r in smart_segmentation(np.fliplr(bottom_region), self.led_config['bottom'])]
                left_leds = [gaussian_weighted_average(r) for r in smart_segmentation(np.flipud(left_region), self.led_config['left'])]
                
                logger.debug(f"LED segments computed: top={len(top_leds)}, right={len(right_leds)}, bottom={len(bottom_leds)}, left={len(left_leds)}")
            except Exception as e:
                logger.error(f"LED segment processing failed: {e}")
                return []

            sides = {
                "top": top_leds,
                "right": right_leds,
                "bottom": bottom_leds,
                "left": left_leds,
            }

            # Build final order
            orderings = {
                "clockwise": ["bottom", "right", "top", "left"],
                "counterclockwise": ["bottom", "left", "top", "right"]
            }

            if self.order not in orderings:
                logger.warning(f"Unknown order '{self.order}', defaulting to 'clockwise'.")
                self.order = "clockwise"
                
            if self.start_side not in orderings[self.order]:
                logger.warning(f"Invalid start side '{self.start_side}', defaulting to 'bottom'.")
                self.start_side = "bottom"

            start_index = orderings[self.order].index(self.start_side)
            final_order = orderings[self.order][start_index:] + orderings[self.order][:start_index]

            # Combine colors
            for side in final_order:
                colors.extend(sides[side])

            color_arrays = []
            for color in colors:
                if isinstance(color, np.ndarray):
                    color_arrays.append(color.astype(np.uint8))
                else:
                    color_arrays.append(np.array([0, 0, 0], dtype=np.uint8))  # Fallback

            logger.info(f"{len(color_arrays)} LED colors generated successfully.")
            logger.debug(f"First few LED colors: {color_arrays[:3]}")
            
            return color_arrays
            
        except Exception as e:
            logger.critical(f"Fatal error during LED color computation: {e}", exc_info=True)
            return []
        

    def adjust_and_correct_colors(self, colors, brightness=1.0, min_brightness_clip=28):
        corrected = []

        for color in colors:
            try:
                
                r = color[0] * brightness  * self.coef_r 
                g = color[1] * brightness  * self.coef_g
                b = color[2] * brightness  * self.coef_b
                scaled = np.array([r, g, b], dtype=np.float32)
                rgb = np.uint8([[scaled]])  
                hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[0][0]
                brightness_value = hsv[2] 

                if brightness_value < min_brightness_clip:
                    corrected.append((0, 0, 0)) 
                    continue

                scale_range = 255 - min_brightness_clip
                adjusted = (scaled - min_brightness_clip) / scale_range * 255
                adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)

                final = self.gamma_table[adjusted]
                corrected.append(tuple(final))

            except Exception as e:
                logger.error(f"Color correction failed: {e}")
                corrected.append((0, 0, 0))

        return corrected

