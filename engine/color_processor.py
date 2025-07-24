import numpy as np
import json

class ColorProcessor: 

    def __init__(self, led_config, margin=40, order="clockwise", start_side="bottom", enable_corners = False):
        self.led_config = led_config
        self.margin = margin
        self.order = order
        self.start_side = start_side
        self.enable_corners = enable_corners

    @classmethod
    def from_config(cls, config_path="config/config.json"):
        with open(config_path) as f:
            config = json.load(f)

        led_config = config.get("led_config", {"top": 10,"right": 6,"bottom": 10,"left": 6})
        margin = config.get("margin", 40)
        order = config.get("order", "clockwise")
        start_side = config.get("start_side", "bottom")
        enable_corners = config.get("enable_corners", False)
        return cls(led_config=led_config, margin=margin, order=order, start_side=start_side, enable_corners=enable_corners) 
    
    
    def get_led_colors(self, image):
        
        h, w, _ = image.shape

        corner_margin = 0
        if self.enable_corners:
            corner_margin = self.margin

        colors = []

        def average_color(region):
            return region.mean(axis = (0,1)).astype(int)
                
        def split_edge(region, num_leds):

            return np.array_split(region, num_leds, axis=1 if region.shape[1] > region.shape[0] else 0)

        top_region = image[0:self.margin, corner_margin:w-corner_margin , :]
        bottom_region = image[h-self.margin:h, corner_margin:w-corner_margin , :]
        left_region = image[corner_margin:h-corner_margin, 0:self.margin, :]
        right_region = image[corner_margin:h-corner_margin, w - self.margin:w, :]

        top_leds = [average_color(r) for r in split_edge(top_region, self.led_config['top'])]
        right_leds = [average_color(r) for r in split_edge(right_region, self.led_config['right'])]
        bottom_leds = [average_color(r) for r in split_edge(np.fliplr(bottom_region), self.led_config['bottom'])]
        left_leds = [average_color(r) for r in split_edge(np.flipud(left_region), self.led_config['left'])]

        sides = {
            "top": top_leds,
            "right": right_leds,
            "bottom": bottom_leds,
            "left": left_leds,
        }

        orderings = {
            "clockwise": ["bottom", "right", "top", "left"],
            "counterclockwise": ["bottom", "left", "top", "right"]
        }

        start_index = orderings[self.order].index(self.start_side)
        final_order = orderings[self.order][start_index:] + orderings[self.order][:start_index]

        for side in final_order:
            colors.extend(sides[side])

        return colors