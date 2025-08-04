import tkinter as tk
from tools.logger import setup_logger

logger = setup_logger("LEDPreviewHUD")

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