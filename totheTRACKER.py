import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import customtkinter as ctk
import os
import sys
import json

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("system")

STATE_FILE = "tracker_state.json"

FONT_NORMAL = ("Fredoka", 14)
FONT_ZONES = ("Fredoka", 12)
FONT_BIG = ("Fredoka", 16, "bold")

BG_COLOR = "#181818"
TEXT_COLOR = "#ffffff"
TOOLBAR_BG = "#1f6feb"


def resize_by_width(img, target_width):
    w, h = img.size
    scale = target_width / w
    new_height = int(h * scale)
    return img.resize((target_width, new_height), Image.LANCZOS)


def resize_by_height(img, target_height):
    w, h = img.size
    scale = target_height / h
    new_width = int(w * scale)
    return img.resize((new_width, target_height), Image.LANCZOS)


def make_rounded(img, radius):
    """Return a copy of *img* (RGBA) with rounded corners of the given radius."""
    img = img.convert("RGBA")
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result


# -------------------------
# Clickable toggle image
# -------------------------
class ToggleImage(tk.Label):
    def __init__(self, parent, locked_img, unlocked_img, bg=BG_COLOR):
        self.locked = ImageTk.PhotoImage(resize_by_width(Image.open(locked_img), 20))
        self.unlocked = ImageTk.PhotoImage(resize_by_width(Image.open(unlocked_img), 20))
        super().__init__(parent, image=self.locked, cursor="hand2", bg=bg)
        self.active = False
        self.bind("<Button-1>", self.toggle)

    def toggle(self, _=None):
        self.active = not self.active
        self.config(image=self.unlocked if self.active else self.locked)

    def reset(self):
        self.active = False
        self.config(image=self.locked)


class ToggleCaptures(tk.Label):
    def __init__(self, parent, locked_img, unlocked_img, bg=BG_COLOR):
        self.locked = ImageTk.PhotoImage(resize_by_height(Image.open(locked_img), 40))
        self.unlocked = ImageTk.PhotoImage(resize_by_height(Image.open(unlocked_img), 40))
        super().__init__(parent, image=self.locked, cursor="hand2", bg=bg)
        self.active = False
        self.bind("<Button-1>", self.toggle)

    def toggle(self, _=None):
        self.active = not self.active
        self.config(image=self.unlocked if self.active else self.locked)

    def reset(self):
        self.active = False
        self.config(image=self.locked)


# -------------------------
# Moon Tracker Row
# -------------------------
class MoonRow(tk.Frame):
    def __init__(self, parent, kingdom_img_path, app):
        super().__init__(parent, bg=BG_COLOR)
        self.app = app
        self.count = 0
        self.max_val = None
        self._kingdom_img_path = kingdom_img_path

        self.lock_icon = ToggleImage(
            self,
            resource_path("assets/lock.png"),
            resource_path("assets/unlock.png")
        )
        self.lock_icon.grid(row=0, column=0, padx=2)

        self.peace_icon = ToggleImage(
            self,
            resource_path("assets/peace.png"),
            resource_path("assets/peace_unlock.png")
        )
        self.peace_icon.grid(row=0, column=1, padx=2)

        # Load base (colored) image
        self.kingdom_img = resize_by_width(Image.open(kingdom_img_path).convert("RGBA"), 40)
        self.kingdom_img_white = self._make_white(self.kingdom_img)
        self.kingdom_photo = ImageTk.PhotoImage(self.kingdom_img)
        self.kingdom_photo_white = ImageTk.PhotoImage(self.kingdom_img_white)

        self.kingdom_label = tk.Label(self, image=self.kingdom_photo, bg=BG_COLOR, fg=TEXT_COLOR)
        self.kingdom_label.grid(row=0, column=3)

        ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=6, padx=5)

        self.label = tk.Label(self, text="0 / ?", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.label.grid(row=0, column=7, padx=5)

        ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=8, padx=5)

        self.max_var = tk.StringVar()
        self.entry = ctk.CTkEntry(self, width=50, height=35, corner_radius=10, textvariable=self.max_var, placeholder_text="?", font=FONT_BIG)
        self.max_var.trace_add("write", self.on_max_change)
        self.entry.grid(row=0, column=9, padx=5)

    def _make_white(self, image):
        img = image.convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a > 0:
                    pixels[x, y] = (255, 255, 255, a)
        return img

    def apply_white_mode(self, white_on):
        photo = self.kingdom_photo_white if white_on else self.kingdom_photo
        self.kingdom_label.config(image=photo)

    def current_photo(self):
        """Return whichever photo is currently shown (for OBS sync)."""
        return self.kingdom_label.cget("image")

    def update_label(self):
        max_display = self.max_val if self.max_val is not None else "?"
        self.label.config(text=f"{self.count} / {max_display}")

    def increment(self):
        self.count += 1
        self.update_label()
        self.app.update_collective_tracker()
        self.app.save_state()

    def decrement(self):
        self.count = max(0, self.count - 1)
        self.update_label()
        self.app.update_collective_tracker()
        self.app.save_state()

    def on_max_change(self, *_):
        val = self.max_var.get()
        if val.isdigit():
            self.max_val = int(val)
        else:
            self.max_val = None
        self.update_label()
        self.app.save_state()

    def reset(self):
        self.count = 0
        self.max_val = None
        self.entry.delete(0, tk.END)
        self.update_label()
        self.lock_icon.reset()
        self.peace_icon.reset()


# -------------------------
# Simple Counter Row (Cap / Star)
# -------------------------
class SimpleCounterRow(tk.Frame):
    def __init__(self, parent, icon_path, app):
        super().__init__(parent, bg=BG_COLOR)
        self.app = app
        self.count = 0
        self._icon_path = icon_path

        # Load base and white versions
        self.base_img = resize_by_width(Image.open(icon_path).convert("RGBA"), 40)
        self.white_img = self._make_white(self.base_img)
        self.photo = ImageTk.PhotoImage(self.base_img)
        self.photo_white = ImageTk.PhotoImage(self.white_img)

        self.label_icon = tk.Label(self, image=self.photo, bg=BG_COLOR)
        self.label_icon.grid(row=0, column=0, padx=5)

        ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=1)
        self.count_label = tk.Label(self, text="0", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.count_label.grid(row=0, column=2, padx=5)
        ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=3)

    def _make_white(self, image):
        img = image.convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a > 0:
                    pixels[x, y] = (255, 255, 255, a)
        return img

    def apply_white_mode(self, white_on):
        photo = self.photo_white if white_on else self.photo
        self.label_icon.config(image=photo)

    def increment(self):
        self.count += 1
        self.count_label.config(text=str(self.count))
        self.app.update_collective_tracker()
        self.app.save_state()

    def decrement(self):
        self.count = max(0, self.count - 1)
        self.count_label.config(text=str(self.count))
        self.app.update_collective_tracker()
        self.app.save_state()

    def reset(self):
        self.count = 0
        self.count_label.config(text="0")


class CaptureRow(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)

        self.parabones_icon = ToggleCaptures(
            self,
            resource_path("assets/Parabones_Capture_Locked.png"),
            resource_path("assets/Parabones_Capture.png")
        )
        self.parabones_icon.grid(row=0, column=0, padx=2)

        self.banzai_icon = ToggleCaptures(
            self,
            resource_path("assets/Banzai_Bill_Capture_Locked.png"),
            resource_path("assets/Banzai_Bill_Capture.png")
        )
        self.banzai_icon.grid(row=0, column=1, padx=2)

        self.wire_icon = ToggleCaptures(
            self,
            resource_path("assets/Spark_pylon_Capture_Locked.png"),
            resource_path("assets/Spark_pylon_Capture.png")
        )
        self.wire_icon.grid(row=1, column=0, padx=2)

        self.bowser_icon = ToggleCaptures(
            self,
            resource_path("assets/Bowser_Capture_Locked.png"),
            resource_path("assets/Bowser_Capture.png")
        )
        self.bowser_icon.grid(row=1, column=1, padx=2)

    def reset(self):
        self.parabones_icon.reset()
        self.banzai_icon.reset()
        self.bowser_icon.reset()
        self.wire_icon.reset()


class AbilityRow(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_COLOR)
        self.app = app

        self.jump_icon = ToggleCaptures(
            self,
            resource_path("assets/Long_Jump_Locked.png"),
            resource_path("assets/Long_Jump.png")
        )
        self.jump_icon.grid(row=0, column=0, padx=2)

        self.cap_icon = ToggleCaptures(
            self,
            resource_path("assets/Cappy_Locked.png"),
            resource_path("assets/Cappy.png")
        )
        self.cap_icon.grid(row=0, column=1, padx=2)

        self.wall_icon = ToggleCaptures(
            self,
            resource_path("assets/Wall_Jump_Locked.png"),
            resource_path("assets/Wall_Jump.png")
        )
        self.wall_icon.grid(row=1, column=1, padx=2)

    def reset(self):
        self.jump_icon.reset()
        self.cap_icon.reset()
        self.wall_icon.reset()


class SidebarAbilityRow(tk.Frame):
    """Ability row for the right sidebar — non-clickable Dark icon + counter."""
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_COLOR)
        self.app = app
        self.count = 0

        # Non-clickable icon (plain Label, no cursor/bind)
        base = resize_by_height(Image.open(resource_path("assets/Dark.png")).convert("RGBA"), 40)
        white = self._make_white(base.copy())
        self._icon_img = ImageTk.PhotoImage(base)
        self._icon_img_white = ImageTk.PhotoImage(white)
        self.icon_label = tk.Label(self, image=self._icon_img, bg=BG_COLOR)
        self.icon_label.grid(row=0, column=0, padx=2)

        ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=1)
        self.count_label = tk.Label(self, text="0", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.count_label.grid(row=0, column=2, padx=5)
        ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=3)

    def _make_white(self, image):
        img = image.convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a > 0:
                    pixels[x, y] = (255, 255, 255, a)
        return img

    def apply_white_mode(self, white_on):
        photo = self._icon_img_white if white_on else self._icon_img
        self.icon_label.config(image=photo)

    def increment(self):
        self.count += 1
        self.count_label.config(text=str(self.count))

    def decrement(self):
        self.count = max(0, self.count - 1)
        self.count_label.config(text=str(self.count))

    def reset(self):
        self.count = 0
        self.count_label.config(text="0")


# -------------------------
# OBS Overlay Window
# -------------------------
class OBSMoonRow(tk.Frame):
    def __init__(self, parent, moon_row, bg_color, white_icons_ref=None):
        super().__init__(parent, bg=bg_color)
        self.moon_row = moon_row
        self.bg_color = bg_color
        self.white_icons_ref = white_icons_ref  # callable returning bool

        self.lock_label = tk.Label(self, image=moon_row.lock_icon.locked, bg=bg_color)
        self.lock_label.grid(row=0, column=0, padx=2)

        self.peace_label = tk.Label(self, image=moon_row.peace_icon.locked, bg=bg_color)
        self.peace_label.grid(row=0, column=1, padx=2)

        self.kingdom_label = tk.Label(self, image=moon_row.kingdom_photo, bg=bg_color)
        self.kingdom_label.grid(row=0, column=2, padx=2)

        self.text = tk.Label(self, text="0 / ?", fg=TEXT_COLOR, bg=bg_color, font=FONT_BIG, width=5, anchor="center")
        self.text.grid(row=0, column=4)

        self.update()

    def update(self):
        max_val = self.moon_row.max_val if self.moon_row.max_val is not None else "?"
        self.text.config(text=f"{self.moon_row.count} / {max_val}")

        self.lock_label.config(
            image=self.moon_row.lock_icon.unlocked if self.moon_row.lock_icon.active else self.moon_row.lock_icon.locked
        )
        self.peace_label.config(
            image=self.moon_row.peace_icon.unlocked if self.moon_row.peace_icon.active else self.moon_row.peace_icon.locked
        )

        # Sync white icon mode
        if self.white_icons_ref is not None:
            white_on = self.white_icons_ref()
            photo = self.moon_row.kingdom_photo_white if white_on else self.moon_row.kingdom_photo
            self.kingdom_label.config(image=photo)

        self.after(200, self.update)

    def set_bg(self, bg_color):
        self.bg_color = bg_color
        self.config(bg=bg_color)
        for widget in (self.lock_label, self.peace_label, self.kingdom_label, self.text):
            widget.config(bg=bg_color)


class OBSSimpleCounterRow(tk.Frame):
    """OBS row for SimpleCounterRow (Cap / Star)."""
    def __init__(self, parent, source_row, bg_color, white_icons_ref=None):
        super().__init__(parent, bg=bg_color)
        self.source_row = source_row
        self.white_icons_ref = white_icons_ref

        self.icon = tk.Label(self, image=source_row.photo, bg=bg_color)
        self.icon.grid(row=0, column=0, padx=4)

        self.label = tk.Label(self, text="0", fg=TEXT_COLOR, bg=bg_color, font=FONT_BIG)
        self.label.grid(row=0, column=1, padx=4)

        self.update()

    def update(self):
        if self.white_icons_ref is not None:
            white_on = self.white_icons_ref()
            photo = self.source_row.photo_white if white_on else self.source_row.photo
            self.icon.config(image=photo)
        else:
            self.icon.config(image=self.source_row.photo)
        self.label.config(text=str(self.source_row.count))
        self.after(200, self.update)

    def set_bg(self, bg):
        self.config(bg=bg)
        self.icon.config(bg=bg)
        self.label.config(bg=bg)


class OBSCaptureColumn(tk.Frame):
    def __init__(self, parent, capture_row, bg_color):
        super().__init__(parent, bg=bg_color)
        self.capture_row = capture_row
        self.bg_color = bg_color

        self.icons = [
            capture_row.parabones_icon,
            capture_row.banzai_icon,
            capture_row.wire_icon,
        ]

        self.labels = []
        for i, icon in enumerate(self.icons):
            lbl = tk.Label(self, image=icon.locked, bg=bg_color)
            lbl.grid(row=0, column=i, pady=4)
            self.labels.append(lbl)

        self.update()

    def update(self):
        for lbl, icon in zip(self.labels, self.icons):
            lbl.config(image=icon.unlocked if icon.active else icon.locked)
        self.after(200, self.update)

    def set_bg(self, bg_color):
        self.config(bg=bg_color)
        self.bg_color = bg_color
        for lbl in self.labels:
            lbl.config(bg=bg_color)


class OBSAbilityColumn(tk.Frame):
    def __init__(self, parent, ability_row, bg_color):
        super().__init__(parent, bg=bg_color)
        self.ability_row = ability_row
        self.bg_color = bg_color

        self.icons = [
            ability_row.jump_icon,
            ability_row.cap_icon,
            ability_row.wall_icon,
        ]

        self.labels = []
        for i, icon in enumerate(self.icons):
            lbl = tk.Label(self, image=icon.locked, bg=bg_color)
            lbl.grid(row=0, column=i, pady=4)
            self.labels.append(lbl)

        self.update()

    def update(self):
        for lbl, icon in zip(self.labels, self.icons):
            lbl.config(image=icon.unlocked if icon.active else icon.locked)
        self.after(200, self.update)

    def set_bg(self, bg_color):
        self.config(bg=bg_color)
        self.bg_color = bg_color
        for lbl in self.labels:
            lbl.config(bg=bg_color)


class OBSSidebarAbilityRow(tk.Frame):
    """OBS display of SidebarAbilityRow (non-clickable Dark icon + counter)."""
    def __init__(self, parent, sidebar_ability_row, bg_color, white_icons_ref=None):
        super().__init__(parent, bg=bg_color)
        self.sidebar_ability_row = sidebar_ability_row
        self.bg_color = bg_color
        self.white_icons_ref = white_icons_ref

        self.icon = tk.Label(self, image=sidebar_ability_row._icon_img, bg=bg_color)
        self.icon.grid(row=0, column=0, padx=4)

        self.label = tk.Label(self, text="0", fg=TEXT_COLOR, bg=bg_color, font=FONT_BIG)
        self.label.grid(row=0, column=1, padx=4)

        self.update()

    def update(self):
        self.label.config(text=str(self.sidebar_ability_row.count))
        if self.white_icons_ref is not None:
            white_on = self.white_icons_ref()
            photo = self.sidebar_ability_row._icon_img_white if white_on else self.sidebar_ability_row._icon_img
            self.icon.config(image=photo)
        self.after(200, self.update)

    def set_bg(self, bg):
        self.config(bg=bg)
        self.icon.config(bg=bg)
        self.label.config(bg=bg)


class OBSBowserRow(tk.Frame):
    def __init__(self, parent, capture_row, bg_color):
        super().__init__(parent, bg=bg_color)
        self.icon = capture_row.bowser_icon
        self.label = tk.Label(self, image=self.icon.locked, bg=bg_color)
        self.label.pack(pady=8)
        self.update()

    def update(self):
        self.label.config(image=self.icon.unlocked if self.icon.active else self.icon.locked)
        self.after(200, self.update)

    def set_bg(self, bg):
        self.config(bg=bg)
        self.label.config(bg=bg)


class SectionHeader(tk.Label):
    def __init__(self, parent, text):
        super().__init__(
            parent,
            text=text,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
            font=("Fredoka", 14, "bold"),
            anchor="center"
        )
        self.pack(fill="x", padx=8, pady=(10, 4))

    def set_bg(self, bg_color):
        self.config(bg=bg_color)


# -------------------------
# Fade helpers
# -------------------------
def fade_in(window, duration=200, steps=20, target_alpha=1.0):
    """Fade a Toplevel window in over `duration` ms."""
    window.attributes("-alpha", 0.0)
    window.deiconify()
    delay = max(1, duration // steps)

    def _step(i=0):
        if not window.winfo_exists():
            return
        if i <= steps:
            window.attributes("-alpha", min(target_alpha, target_alpha * i / steps))
            window.after(delay, _step, i + 1)

    _step()


def fade_out(window, duration=200, steps=20, on_done=None):
    """Fade a Toplevel window out over `duration` ms, then call on_done."""
    delay = max(1, duration // steps)

    def _step(i=steps):
        if not window.winfo_exists():
            return
        if i >= 0:
            window.attributes("-alpha", max(0.0, 1.0 * i / steps))
            window.after(delay, _step, i - 1)
        else:
            if on_done:
                on_done()

    _step()


class OBSWindow(tk.Toplevel):
    def __init__(self, parent, moon_rows, capture_row, ability_row,
                 cap_row=None, star_row=None, dark_row=None, cloud_row=None,
                 cap_enabled=False, star_enabled=False, dark_enabled=False,
                 cloud_enabled=False, white_icons_ref=None,
                 sidebar_cap_row=None, sidebar_star_row=None, sidebar_ability_row=None,
                 icons_visible=True):
        super().__init__(parent)

        self.title("OBS Overlay")
        self.attributes("-topmost", True)
        self.geometry("350x550")

        # Fade out when the user closes this window
        self.protocol("WM_DELETE_WINDOW",
                      lambda: fade_out(self, on_done=self.destroy))

        self.bg_mode = "dark"
        self.bg_color = BG_COLOR
        self.config(bg=self.bg_color)

        self.moon_rows = moon_rows
        self.cap_row = cap_row
        self.star_row = star_row
        self.dark_row = dark_row
        self.cloud_row = cloud_row
        self.cap_enabled = cap_enabled
        self.star_enabled = star_enabled
        self.dark_enabled = dark_enabled
        self.cloud_enabled = cloud_enabled
        self.white_icons_ref = white_icons_ref
        self.sidebar_cap_row = sidebar_cap_row
        self.sidebar_star_row = sidebar_star_row
        self.sidebar_ability_row = sidebar_ability_row
        self.icons_visible = icons_visible

        # Reference back to app for totals
        self._app = parent

        self.main = tk.Frame(self, bg=self.bg_color)
        self.main.pack(fill="both", expand=True)

        self.moon_frame = tk.Frame(self.main, bg=self.bg_color)
        self.moon_frame.grid(row=0, column=0, padx=8, sticky="n")

        # --- Cap row (above Cascade) ---
        self.cap_obs = None
        if self.cap_row and self.cap_enabled:
            self.cap_obs = OBSSimpleCounterRow(
                self.moon_frame, self.cap_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self.cap_obs.pack(pady=2, padx=6, anchor="w")

        # --- Standard kingdom moon rows ---
        self.moon_obs_rows = []
        for i, row in enumerate(moon_rows):
            obs_row = OBSMoonRow(self.moon_frame, row, self.bg_color,
                                 white_icons_ref=self.white_icons_ref)
            obs_row.pack(pady=2, padx=6, anchor="w")
            self.moon_obs_rows.append(obs_row)

        # --- Dark row (below Bowser) ---
        self.dark_obs = None
        if self.dark_row and self.dark_enabled:
            self.dark_obs = OBSMoonRow(
                self.moon_frame, self.dark_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self.dark_obs.pack(pady=2, padx=6, anchor="w")

        # --- Star row (below Dark, or below Bowser if Dark hidden) ---
        self.star_obs = None
        if self.star_row and self.star_enabled:
            self.star_obs = OBSSimpleCounterRow(
                self.moon_frame, self.star_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self.star_obs.pack(pady=2, padx=6, anchor="w")

        self.right = tk.Frame(self.main, bg=self.bg_color)
        self.right.grid(row=0, column=1, padx=12, sticky="n")

        self.moon_cave_header = SectionHeader(self.right, "Moon Cave")
        self.capture_col = OBSCaptureColumn(self.right, capture_row, self.bg_color)
        self.capture_col.pack(pady=(0, 20))

        self.cave_skip_header = SectionHeader(self.right, "Cave Skip")
        self.ability_col = OBSAbilityColumn(self.right, ability_row, self.bg_color)
        self.ability_col.pack(pady=(0, 20))

        self.bowser_row = OBSBowserRow(self.right, capture_row, self.bg_color)
        self.bowser_row.pack(pady=(0, 20))

        # Apply initial icons visibility
        if not self.icons_visible:
            self.moon_cave_header.pack_forget()
            self.capture_col.pack_forget()
            self.cave_skip_header.pack_forget()
            self.ability_col.pack_forget()
            self.bowser_row.pack_forget()

        self.moon_total_header = SectionHeader(self.right, "Moons:")
        self.moon_total_label = tk.Label(
            self.right,
            text="0 / 124",
            fg=TEXT_COLOR,
            bg=self.bg_color,
            font=FONT_BIG
        )
        self.moon_total_label.pack(pady=(0, 10))
        self._update_moon_total()

        # --- Cloud Kingdom counter on right sidebar ---
        self.obs_cloud_row = None

        # --- Row 1: Cap counter (below Moon Count) — hidden until toggled ---
        self.obs_sidebar_cap = None

        # --- Row 2: Captures counter (Spark_pylon) — hidden until toggled ---
        self.obs_sidebar_star = None

        # --- Row 3: Abilities (Long_Jump) — hidden until toggled ---
        self.obs_sidebar_ability = None

    def _update_moon_total(self):
        total = sum(row.count for row in self.moon_rows)
        # Add dark row only when dark is enabled
        if self.dark_enabled and self.dark_row:
            total += self.dark_row.count

        target = "124"
        try:
            if hasattr(self._app, "collective_target_var"):
                target = self._app.collective_target_var.get() or "124"
        except Exception:
            pass

        self.moon_total_label.config(text=f"{total} / {target}")
        self.after(200, self._update_moon_total)

    def refresh_special_rows(self, cap_enabled, star_enabled, dark_enabled, cloud_enabled=False):
        """Called by the app when special rows are toggled, to show/hide them in OBS.
        Moon Kingdom (dark_obs) is always shown when enabled — it is NOT subject to the optional-hide toggle."""
        self.cap_enabled = cap_enabled
        self.star_enabled = star_enabled
        self.dark_enabled = dark_enabled
        self.cloud_enabled = cloud_enabled
        hidden = hasattr(self._app, "obs_optional_hidden") and self._app.obs_optional_hidden

        # Cap row — hidden by the optional toggle
        if cap_enabled and self.cap_obs is None and self.cap_row:
            self.cap_obs = OBSSimpleCounterRow(
                self.moon_frame, self.cap_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        if self.cap_obs:
            if cap_enabled and not hidden:
                if self.moon_obs_rows:
                    self.cap_obs.pack(pady=2, padx=6, anchor="w",
                                      before=self.moon_obs_rows[0])
                else:
                    self.cap_obs.pack(pady=2, padx=6, anchor="w")
            else:
                self.cap_obs.pack_forget()
                if not cap_enabled:
                    self.cap_obs.destroy()
                    self.cap_obs = None

        # Dark row (Moon Kingdom) — NEVER hidden by the optional toggle; only by dark_enabled
        if dark_enabled and self.dark_obs is None and self.dark_row:
            self.dark_obs = OBSMoonRow(
                self.moon_frame, self.dark_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        if self.dark_obs:
            if dark_enabled:
                if self.star_obs:
                    self.dark_obs.pack(pady=2, padx=6, anchor="w",
                                       before=self.star_obs)
                else:
                    self.dark_obs.pack(pady=2, padx=6, anchor="w")
            else:
                self.dark_obs.pack_forget()
                self.dark_obs.destroy()
                self.dark_obs = None

        # Star row (Capture) — hidden by the optional toggle
        if star_enabled and self.star_obs is None and self.star_row:
            self.star_obs = OBSSimpleCounterRow(
                self.moon_frame, self.star_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        if self.star_obs:
            if star_enabled and not hidden:
                self.star_obs.pack(pady=2, padx=6, anchor="w")
            else:
                self.star_obs.pack_forget()
                if not star_enabled:
                    self.star_obs.destroy()
                    self.star_obs = None

    def _repack_sidebar_obs(self):
        """Unpack and re-pack all right-sidebar OBS rows in fixed order: Cap -> Cloud -> Star -> Dark.
        Respects obs_optional_hidden for all four rows, and icons_visible for Star and Dark."""
        hidden = hasattr(self._app, "obs_optional_hidden") and self._app.obs_optional_hidden
        for w in (self.obs_sidebar_cap, self.obs_cloud_row, self.obs_sidebar_star, self.obs_sidebar_ability):
            if w:
                w.pack_forget()
        if hidden:
            return
        if self.obs_sidebar_cap and hasattr(self._app, "sidebar_cap_visible") and self._app.sidebar_cap_visible:
            self.obs_sidebar_cap.pack(pady=(4, 2), anchor="center")
        if self.obs_cloud_row and self.cloud_enabled:
            self.obs_cloud_row.pack(pady=(4, 2), anchor="center")
        if self.obs_sidebar_star and hasattr(self._app, "sidebar_captures_visible") and self._app.sidebar_captures_visible and self.icons_visible:
            self.obs_sidebar_star.pack(pady=(2, 2), anchor="center")
        if self.obs_sidebar_ability and hasattr(self._app, "sidebar_ability_visible") and self._app.sidebar_ability_visible and self.icons_visible:
            self.obs_sidebar_ability.pack(pady=(2, 4), anchor="center")

    def refresh_cloud_row(self, cloud_enabled):
        """Show/hide the Cloud Kingdom counter on the OBS right sidebar."""
        self.cloud_enabled = cloud_enabled
        if cloud_enabled and self.obs_cloud_row is None and self.cloud_row:
            self.obs_cloud_row = OBSSimpleCounterRow(
                self.right, self.cloud_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        self._repack_sidebar_obs()

    def set_optional_kingdoms_visible(self, visible):
        """Show or hide Cap, Cloud, Star (Capture), and Dark (Movement Ability) rows in OBS only.
        Moon Kingdom (dark_obs) is intentionally NOT affected by this toggle."""
        # Left column: Cap and Star rows
        if visible:
            if self.cap_obs:
                if self.moon_obs_rows:
                    self.cap_obs.pack(pady=2, padx=6, anchor="w",
                                      before=self.moon_obs_rows[0])
                else:
                    self.cap_obs.pack(pady=2, padx=6, anchor="w")
            # NOTE: dark_obs (Moon Kingdom) is NOT touched here
            if self.star_obs:
                self.star_obs.pack(pady=2, padx=6, anchor="w")
        else:
            for w in (self.cap_obs, self.star_obs):
                if w:
                    w.pack_forget()
        # Right sidebar: always re-pack in fixed order Cap -> Cloud -> Star -> Dark
        self._repack_sidebar_obs()

    def set_icons_visible(self, visible):
        """Show or hide Moon Cave, Cave Skip and Bowser capture icons in OBS."""
        self.icons_visible = visible
        if visible:
            self.moon_cave_header.pack(fill="x", padx=8, pady=(10, 4))
            self.capture_col.pack(pady=(0, 20))
            self.cave_skip_header.pack(fill="x", padx=8, pady=(10, 4))
            self.ability_col.pack(pady=(0, 20))
            self.bowser_row.pack(pady=(0, 20))
            # Ensure they appear before moon_total_header
            self.moon_cave_header.pack_forget()
            self.capture_col.pack_forget()
            self.cave_skip_header.pack_forget()
            self.ability_col.pack_forget()
            self.bowser_row.pack_forget()
            self.moon_cave_header.pack(fill="x", padx=8, pady=(10, 4),
                                       before=self.moon_total_header)
            self.capture_col.pack(pady=(0, 20), before=self.moon_total_header)
            self.cave_skip_header.pack(fill="x", padx=8, pady=(10, 4),
                                       before=self.moon_total_header)
            self.ability_col.pack(pady=(0, 20), before=self.moon_total_header)
            self.bowser_row.pack(pady=(0, 20), before=self.moon_total_header)
        else:
            self.moon_cave_header.pack_forget()
            self.capture_col.pack_forget()
            self.cave_skip_header.pack_forget()
            self.ability_col.pack_forget()
            self.bowser_row.pack_forget()

    def refresh_sidebar_rows(self, cap_visible, captures_visible, ability_visible):
        """Called by the app when sidebar rows are toggled, to show/hide them in OBS.
        Order is always: Cap -> Cloud -> Star -> Dark, regardless of toggle sequence."""
        # Create widgets on first use if not yet created
        if self.obs_sidebar_cap is None and self.sidebar_cap_row:
            self.obs_sidebar_cap = OBSSimpleCounterRow(
                self.right, self.sidebar_cap_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        if self.obs_sidebar_star is None and self.sidebar_star_row:
            self.obs_sidebar_star = OBSSimpleCounterRow(
                self.right, self.sidebar_star_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        if self.obs_sidebar_ability is None and self.sidebar_ability_row:
            self.obs_sidebar_ability = OBSSidebarAbilityRow(
                self.right, self.sidebar_ability_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
        self._repack_sidebar_obs()

    def toggle_bg(self):
        if self.bg_mode == "dark":
            self.bg_mode = "green"
            self.bg_color = "#00FF00"
        else:
            self.bg_mode = "dark"
            self.bg_color = "#181818"

        self.config(bg=self.bg_color)

        for row in self.moon_obs_rows:
            row.set_bg(self.bg_color)
        if self.cap_obs:
            self.cap_obs.set_bg(self.bg_color)
        if self.star_obs:
            self.star_obs.set_bg(self.bg_color)
        if self.dark_obs:
            self.dark_obs.set_bg(self.bg_color)
        self.capture_col.set_bg(self.bg_color)
        self.ability_col.set_bg(self.bg_color)
        self.bowser_row.set_bg(self.bg_color)
        self.main.config(bg=self.bg_color)
        self.moon_frame.config(bg=self.bg_color)
        self.right.config(bg=self.bg_color)
        self.moon_cave_header.set_bg(self.bg_color)
        self.cave_skip_header.set_bg(self.bg_color)
        self.moon_total_header.set_bg(self.bg_color)
        self.moon_total_label.config(bg=self.bg_color)
        if self.obs_cloud_row:
            self.obs_cloud_row.set_bg(self.bg_color)
        if self.obs_sidebar_cap:
            self.obs_sidebar_cap.set_bg(self.bg_color)
        if self.obs_sidebar_star:
            self.obs_sidebar_star.set_bg(self.bg_color)
        if self.obs_sidebar_ability:
            self.obs_sidebar_ability.set_bg(self.bg_color)



# -------------------------
# Settings Window
# -------------------------
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.title("Settings")
        self.geometry("320x600")
        self.configure(bg=BG_COLOR)

        # Fade out when the user closes this window
        self.protocol("WM_DELETE_WINDOW",
                      lambda: fade_out(self, on_done=self.destroy))

        # Scrollable canvas so nothing gets cut off
        canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        inner = tk.Frame(canvas, bg=BG_COLOR)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Title styled the same as Moon Tracker label
        tk.Label(inner, text="Settings", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=FONT_BIG).pack(pady=(16, 12))

        container = tk.Frame(inner, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        ICON_SIZE = 28
        BTN_HEIGHT = ICON_SIZE + 8
        btn_opts = dict(fg_color=TOOLBAR_BG, hover_color="#1a5fc8",
                        corner_radius=10, border_width=0, cursor="hand2",
                        anchor="w", compound="left",
                        font=FONT_NORMAL)

        def make_row(icon_photo, label_text, command, height=BTN_HEIGHT):
            row = tk.Frame(container, bg=BG_COLOR)
            row.pack(fill="x", pady=4)
            btn = ctk.CTkButton(
                row,
                image=icon_photo,
                text=f"  {label_text}",
                command=command,
                width=260,
                height=height,
                **btn_opts
            )
            btn.pack(fill="x")
            return btn

        # White Icons toggle — shows WHITE metro icon when main view has COLORED icons (default),
        # and COLORED metro icon when main view has WHITE icons.
        # i.e. the button always shows what clicking will switch TO.
        current_white_icon = app.metro_color_photo if app.white_icons else app.metro_white_photo
        self.white_icon_btn = make_row(current_white_icon, "Toggle White Icons",
                                       app.toggle_white_icons)

        make_row(app.tb_cap_photo,      "Toggle Cap Moon Tracker",              app.toggle_cap_row)
        make_row(app.tb_cloud_photo,    "Toggle Cloud Moon Tracker",            app.toggle_cloud_row)
        make_row(app.tb_dark_photo,     "Toggle Moon Kingdom Tracker",          app.toggle_dark_row)

        # ── Hide Optional Kingdoms in OBS (only visible when at least one optional row is enabled) ──
        self._obs_optional_text = tk.StringVar(
            value="Unhide Optional Kingdoms in OBS" if app.obs_optional_hidden
                  else "Hide Optional Kingdoms in OBS"
        )
        self._obs_optional_frame = tk.Frame(container, bg=BG_COLOR)
        ctk.CTkButton(
            self._obs_optional_frame,
            textvariable=self._obs_optional_text,
            command=app.toggle_obs_optional,
            width=260, height=BTN_HEIGHT,
            fg_color="#4a2080", hover_color="#331560", text_color="#ffffff",
            corner_radius=10, cursor="hand2", font=FONT_NORMAL
        ).pack(fill="x")
        # Visibility applied after all frames are created (see end of __init__)

        # ── Clear Tracker + Clear Notes side by side (always visible, not tied to anything) ──
        def confirm_clear_tracker():
            popup = tk.Toplevel(self)
            popup.title("Confirm")
            popup.configure(bg=BG_COLOR)
            popup.geometry("320x130")
            popup.grab_set()
            tk.Label(popup, text="Are you sure you want to clear the Tracker?",
                     bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_NORMAL,
                     wraplength=280).pack(pady=(18, 10))
            btn_row = tk.Frame(popup, bg=BG_COLOR)
            btn_row.pack()
            ctk.CTkButton(btn_row, text="Yes", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#cc0000", hover_color="#aa0000", width=100,
                          command=lambda: [popup.destroy(), app.reset_all_moons()]
                          ).pack(side="left", padx=8)
            ctk.CTkButton(btn_row, text="No", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#444444", hover_color="#222222", width=100,
                          command=popup.destroy).pack(side="left", padx=8)

        def confirm_clear_notes():
            popup = tk.Toplevel(self)
            popup.title("Confirm")
            popup.configure(bg=BG_COLOR)
            popup.geometry("320x130")
            popup.grab_set()
            tk.Label(popup, text="Are you sure you want to clear the Notes Tab?",
                     bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_NORMAL,
                     wraplength=280).pack(pady=(18, 10))
            btn_row = tk.Frame(popup, bg=BG_COLOR)
            btn_row.pack()
            ctk.CTkButton(btn_row, text="Yes", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#cc0000", hover_color="#aa0000", width=100,
                          command=lambda: [popup.destroy(), app._clear_notes()]
                          ).pack(side="left", padx=8)
            ctk.CTkButton(btn_row, text="No", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#444444", hover_color="#222222", width=100,
                          command=popup.destroy).pack(side="left", padx=8)

        self._clear_pair_frame = tk.Frame(container, bg=BG_COLOR)
        self._clear_pair_frame.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(
            self._clear_pair_frame, text="Clear Tracker", command=confirm_clear_tracker,
            height=BTN_HEIGHT,
            fg_color="#ffffff", hover_color="#dddddd", text_color="#000000",
            corner_radius=10, cursor="hand2", font=FONT_NORMAL
        ).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ctk.CTkButton(
            self._clear_pair_frame, text="Clear Notes", command=confirm_clear_notes,
            height=BTN_HEIGHT,
            fg_color="#ffffff", hover_color="#dddddd", text_color="#000000",
            corner_radius=10, cursor="hand2", font=FONT_NORMAL
        ).pack(side="left", expand=True, fill="x", padx=(3, 0))

        # ── Load Spoiler Log ──
        ctk.CTkButton(
            container,
            text="📂  Load Spoiler Log",
            command=lambda: load_spoiler_log_file(app),
            width=260, height=BTN_HEIGHT,
            fg_color="#1a6040", hover_color="#145030", text_color="#ffffff",
            corner_radius=10, cursor="hand2",
            font=FONT_NORMAL
        ).pack(fill="x", pady=(8, 4))

        # Hide Ability Lock
        self.hide_ability_btn = ctk.CTkButton(
            container,
            textvariable=app._hide_ability_text,
            command=app.toggle_capture_icons,
            width=260, height=BTN_HEIGHT,
            fg_color="#000000", hover_color="#222222", text_color="#ffffff",
            corner_radius=10, cursor="hand2",
            font=FONT_NORMAL
        )
        self.hide_ability_btn.pack(fill="x", pady=(12, 4))

        # Star Moon Tracker & Dark Side Moon Tracker side by side — shown/hidden with Hide Ability Lock
        self._ability_pair_frame = tk.Frame(container, bg=BG_COLOR)
        self._ability_pair_frame.pack(fill="x", pady=4)
        ctk.CTkButton(
            self._ability_pair_frame,
            image=app.tb_captures_photo,
            text="  Star",
            command=app.toggle_sidebar_captures_row,
            height=BTN_HEIGHT,
            **btn_opts
        ).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ctk.CTkButton(
            self._ability_pair_frame,
            image=app.tb_ability_photo,
            text="  Dark Side",
            command=app.toggle_sidebar_ability_row,
            height=BTN_HEIGHT,
            **btn_opts
        ).pack(side="left", expand=True, fill="x", padx=(3, 0))

        # Apply initial visibility based on icons_visible state
        self._apply_ability_lock_visibility(app.icons_visible)
        # Apply initial visibility for Hide Optional Kingdoms button
        self._update_obs_optional_frame_visibility()

    def refresh_obs_optional_btn(self):
        """Called when any optional row is toggled to update label and visibility."""
        self._obs_optional_text.set(
            "Unhide Optional Kingdoms in OBS" if self.app.obs_optional_hidden
            else "Hide Optional Kingdoms in OBS"
        )
        self._update_obs_optional_frame_visibility()

    def _update_obs_optional_frame_visibility(self):
        """Show the button only when at least one optional kingdom row is enabled.
        Placed between the toggle rows and the Clear pair."""
        any_optional = (
            self.app.sidebar_cap_visible
            or self.app.cloud_enabled
            or (self.app.sidebar_captures_visible and self.app.icons_visible)
            or (self.app.sidebar_ability_visible and self.app.icons_visible)
        )
        self._obs_optional_frame.pack_forget()
        if any_optional:
            self._obs_optional_frame.pack(fill="x", pady=4,
                                          before=self._clear_pair_frame)

    def refresh_white_icon_button(self):
        """Called by toggle_white_icons to flip the button icon.
        When main view shows colored icons (white_icons=False): button shows white Metro icon.
        When main view shows white icons (white_icons=True): button shows colored Metro icon."""
        if self.app.white_icons:
            # Main view is white → button shows colored icon (clicking will revert to colored)
            self.white_icon_btn.configure(image=self.app.metro_color_photo)
        else:
            # Main view is colored → button shows white icon (clicking will switch to white)
            self.white_icon_btn.configure(image=self.app.metro_white_photo)

    def _apply_ability_lock_visibility(self, visible):
        """Show or hide Star/Dark Side pair row based on icons_visible (Hide Ability Lock state).
        Clear Tracker and Clear Notes are never affected."""
        if visible:
            self._ability_pair_frame.pack(fill="x", pady=4)
        else:
            self._ability_pair_frame.pack_forget()

    def refresh_hide_ability_btn(self):
        """Called by toggle_capture_icons to update Star/Dark Side button visibility."""
        self._apply_ability_lock_visibility(self.app.icons_visible)
        self._update_obs_optional_frame_visibility()


# -------------------------
# Spoiler Log Window
# -------------------------

def parse_spoiler_log(text):
    """
    Parse the SMO Randomizer plain-text spoiler log into structured sections.
    Returns a dict with keys:
      'meta'       : {seed, ...}
      'moons'      : {kingdom: [(moon_name, dest_kingdom, dest_capture_tag, unlock_moon), ...]}
      'entrances'  : {kingdom: [(from_exit, to_stage_kingdom, to_stage, to_exit), ...]}
      'paintings'  : [(kingdom_a, kingdom_b), ...]
      'path'       : [(step_num, kingdom, moon, at_location, reason, unlocks, route), ...]
      'raw'        : original text (always available)
    """
    data = {
        "meta": {},
        "moons": {},
        "entrances": {},
        "paintings": [],
        "path": [],
        "raw": text,
    }

    lines = text.splitlines()
    section = None
    current_kingdom = None
    current_step = None

    for line in lines:
        stripped = line.strip()

        # ── Section headers ──
        if stripped.startswith("=== ") and stripped.endswith(" ==="):
            header = stripped[4:-4].strip()
            if header == "SMO Randomizer Spoiler Log":
                section = "meta"
            elif header == "Moon Placements by Final Location":
                section = "moons"
            elif header == "Entrance Randomizer":
                section = "entrances"
            elif header == "Painting Links":
                section = "paintings"
            elif header == "Suggested Progress Path":
                section = "path"
            else:
                section = None
            current_kingdom = None
            current_step = None
            continue

        # ── Meta ──
        if section == "meta":
            if stripped.startswith("Seed:"):
                data["meta"]["seed"] = stripped.split(":", 1)[1].strip()
            continue

        # ── Moon Placements ──
        if section == "moons":
            # Kingdom header (no leading space)
            if stripped.endswith(":") and not line.startswith(" "):
                current_kingdom = stripped[:-1]
                data["moons"].setdefault(current_kingdom, [])
                continue
            # Moon entry: "  Moon Name - Destination Kingdom (Capture Tag) @ Unlock Moon"
            if line.startswith("  ") and " - " in stripped:
                # Split on " - " (first occurrence only)
                parts = stripped.split(" - ", 1)
                moon_name = parts[0].strip()
                rest = parts[1].strip()
                # rest is:  "Destination Kingdom (CaptureTag) @ Unlock Moon"
                # or        "Destination Kingdom @ Unlock Moon"
                # or        "Destination Kingdom"   (no @ → standalone / no prerequisite)
                capture_tag = ""
                unlock_moon = ""
                dest_raw = rest
                if " @ " in rest:
                    dest_raw, unlock_moon = rest.rsplit(" @ ", 1)
                # Extract optional (CaptureTag)
                if dest_raw.endswith(")") and "(" in dest_raw:
                    paren_start = dest_raw.rfind("(")
                    capture_tag = dest_raw[paren_start + 1:-1].strip()
                    dest_raw = dest_raw[:paren_start].strip()
                dest_kingdom = dest_raw.strip()
                if current_kingdom:
                    data["moons"][current_kingdom].append({
                        "moon": moon_name,
                        "dest": dest_kingdom,
                        "capture": capture_tag,
                        "unlock_at": unlock_moon,
                    })
            continue

        # ── Entrance Randomizer ──
        if section == "entrances":
            if stripped.endswith(":") and not line.startswith(" "):
                current_kingdom = stripped[:-1]
                data["entrances"].setdefault(current_kingdom, [])
                continue
            if line.startswith("  ") and " -> " in stripped:
                left, right = stripped.split(" -> ", 1)
                # left:  "Kingdom ExitName"  →  split on last space that separates exit id
                # More precisely: "Cap Kingdom PushBlockExStageEnt"
                # The kingdom name may have spaces, so we match the known kingdom prefix
                from_exit = left.strip()
                # right: "Kingdom: StageName (exit_id)"
                dest_stage = right.strip()
                if current_kingdom:
                    data["entrances"][current_kingdom].append({
                        "from": from_exit,
                        "to": dest_stage,
                    })
            continue

        # ── Painting Links ──
        if section == "paintings":
            if " <-> " in stripped:
                a, b = stripped.split(" <-> ", 1)
                # Strip stage annotation e.g. "Cascade Kingdom (WaterfallWorldHomeStage::start)"
                def _strip_stage(s):
                    if "(" in s:
                        return s[:s.index("(")].strip()
                    return s.strip()
                data["paintings"].append((_strip_stage(a), _strip_stage(b)))
            continue

        # ── Progress Path ──
        if section == "path":
            # Numbered step: "001. Kingdom: collect Moon at Location"
            import re
            step_match = re.match(r"^(\d+)\.\s+(.+?):\s+collect (.+?) at (.+)$", stripped)
            if step_match:
                current_step = {
                    "num": int(step_match.group(1)),
                    "kingdom": step_match.group(2).strip(),
                    "moon": step_match.group(3).strip(),
                    "location": step_match.group(4).strip(),
                    "reason": "",
                    "unlocks": [],
                    "route": [],
                }
                data["path"].append(current_step)
                continue
            if current_step:
                if stripped.startswith("Reason:"):
                    current_step["reason"] = stripped[7:].strip()
                elif stripped.startswith("Unlocks:"):
                    current_step["unlocks"] = [u.strip() for u in stripped[8:].split(",")]
                elif stripped.startswith("Route:"):
                    current_step["route"].append(stripped[6:].strip())
        continue

    return data


# Kingdom accent colours (reuse tracker palette where possible)
KINGDOM_COLORS = {
    "Cap Kingdom":       "#cccccc",
    "Cascade Kingdom":   "#e07040",
    "Sand Kingdom":      "#e8c040",
    "Lake Kingdom":      "#40a0e8",
    "Wooded Kingdom":    "#50b860",
    "Cloud Kingdom":     "#a0d0f0",
    "Lost Kingdom":      "#9060c0",
    "Metro Kingdom":     "#e04040",
    "Snow Kingdom":      "#90d0ff",
    "Seaside Kingdom":   "#40c0b0",
    "Luncheon Kingdom":  "#e86020",
    "Ruined Kingdom":    "#888888",
    "Bowser's Kingdom":  "#e05050",
    "Moon Kingdom":      "#b0a0e0",
    "Mushroom Kingdom":  "#e84080",
    "Dark Side":         "#4040c0",
    "Darker Side":       "#202060",
}


def _kc(kingdom):
    """Return accent color for a kingdom name, falling back to white."""
    for k, v in KINGDOM_COLORS.items():
        if k.lower() in kingdom.lower():
            return v
    return "#ffffff"


HIGHLIGHT_BG = "#3a5a1a"   # green-ish highlight for search matches
SECTION_HEADER_BG = "#242424"


class SpoilerLogWindow(tk.Toplevel):
    """
    A searchable, collapsible spoiler-log viewer.
    Styled to match the existing Notes window (dark background, Fredoka font, scrollable).
    Stays open across the session but does NOT persist the loaded file path.
    """

    def __init__(self, parent, spoiler_data):
        super().__init__(parent)
        self.title("Spoiler Log")
        self.geometry("860x760")
        self.configure(bg=BG_COLOR)
        self.protocol("WM_DELETE_WINDOW",
                      lambda: fade_out(self, on_done=self.destroy))

        self._data = spoiler_data
        self._section_frames = {}   # section_key -> (header_frame, body_frame, collapsed_var)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        self._all_text_items = []   # list of tk.Label / tk.Text widgets for search

        # ── Tab bar ──
        tab_frame = tk.Frame(self, bg="#111111")
        tab_frame.pack(fill="x")
        self._current_tab = tk.StringVar(value="structured")

        def _tab_btn(text, value):
            def _cmd():
                self._current_tab.set(value)
                _refresh_tab()
            btn = ctk.CTkButton(tab_frame, text=text, command=_cmd,
                                width=120, height=32,
                                fg_color=TOOLBAR_BG, hover_color="#1a5fc8",
                                corner_radius=0, font=FONT_NORMAL)
            btn.pack(side="left")
            return btn

        self._tab_structured = _tab_btn("Spoiler Log", "structured")
        self._tab_raw = _tab_btn("Raw JSON / Text", "raw")

        # ── Search bar (only shown on structured tab) ──
        self._search_outer = tk.Frame(self, bg=BG_COLOR)
        self._search_outer.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(self._search_outer, text="🔍 Search:", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=FONT_NORMAL).pack(side="left")
        self._search_entry = ctk.CTkEntry(
            self._search_outer, textvariable=self._search_var,
            placeholder_text="Filter all sections…",
            width=400, height=30, font=FONT_NORMAL)
        self._search_entry.pack(side="left", padx=8)
        ctk.CTkButton(self._search_outer, text="✕ Clear", width=60, height=30,
                      fg_color="#444444", hover_color="#222222",
                      corner_radius=8, font=FONT_NORMAL,
                      command=lambda: self._search_var.set("")).pack(side="left")

        # ── Main pane (swap between structured / raw) ──
        self._pane = tk.Frame(self, bg=BG_COLOR)
        self._pane.pack(fill="both", expand=True)

        self._structured_frame = None
        self._raw_frame = None

        def _refresh_tab():
            for w in self._pane.winfo_children():
                w.pack_forget()
            v = self._current_tab.get()
            if v == "structured":
                self._search_outer.pack(fill="x", padx=10, pady=(8, 4))
                if self._structured_frame is None:
                    self._build_structured()
                self._structured_frame.pack(fill="both", expand=True)
            else:
                self._search_outer.pack_forget()
                if self._raw_frame is None:
                    self._build_raw()
                self._raw_frame.pack(fill="both", expand=True)

        _refresh_tab()

    # ------------------------------------------------------------------ #
    #  Structured view
    # ------------------------------------------------------------------ #

    def _build_structured(self):
        outer = tk.Frame(self._pane, bg=BG_COLOR)
        outer.pack(fill="both", expand=True)
        self._structured_frame = outer

        canvas = tk.Canvas(outer, bg=BG_COLOR, highlightthickness=0)
        self._scroll_canvas = canvas  # stored so search can scroll to matches
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG_COLOR)
        self._structured_inner = inner
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Mouse-wheel scroll
        def _mw(evt):
            canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _mw)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        data = self._data

        # Seed banner
        seed = data["meta"].get("seed", "Unknown")
        tk.Label(inner, text=f"Seed: {seed}", bg=BG_COLOR, fg="#aaaaaa",
                 font=("Fredoka", 13)).pack(anchor="w", padx=16, pady=(8, 4))

        # Build sections
        if data["moons"]:
            self._build_section(inner, "🌙  Moon Placements", "moons",
                                lambda p: self._build_moons(p, data["moons"]))
        if data["paintings"]:
            self._build_section(inner, "🖼️  Painting Destinations", "paintings",
                                lambda p: self._build_paintings(p, data["paintings"]))
        if data["entrances"]:
            self._build_section(inner, "🚪  Loading Zone Connections", "entrances",
                                lambda p: self._build_entrances(p, data["entrances"]))
        if data["path"]:
            self._build_section(inner, "📍  Suggested Progress Path", "path",
                                lambda p: self._build_path(p, data["path"]))

        if not (data["moons"] or data["paintings"] or data["entrances"] or data["path"]):
            tk.Label(inner, text="⚠ No structured data recognised — use the 'Raw JSON / Text' tab.",
                     bg=BG_COLOR, fg="#ff8844", font=FONT_NORMAL,
                     wraplength=600, justify="left").pack(padx=20, pady=30)

    def _build_section(self, parent, title, key, builder):
        """Collapsible section: header row + body frame."""
        collapsed = tk.BooleanVar(value=False)

        header = tk.Frame(parent, bg=SECTION_HEADER_BG, cursor="hand2")
        header.pack(fill="x", padx=8, pady=(8, 0))

        arrow_var = tk.StringVar(value="▼")
        arrow_lbl = tk.Label(header, textvariable=arrow_var,
                             bg=SECTION_HEADER_BG, fg="#aaaaaa", font=FONT_BIG)
        arrow_lbl.pack(side="left", padx=(8, 4))

        tk.Label(header, text=title, bg=SECTION_HEADER_BG, fg=TEXT_COLOR,
                 font=FONT_BIG).pack(side="left", pady=6)

        body = tk.Frame(parent, bg=BG_COLOR)
        body.pack(fill="x", padx=8, pady=(0, 4))
        builder(body)

        def _toggle(_=None):
            if collapsed.get():
                body.pack_forget()
                arrow_var.set("▶")
            else:
                body.pack(fill="x", padx=8, pady=(0, 4))
                arrow_var.set("▼")
            collapsed.set(not collapsed.get())

        header.bind("<Button-1>", _toggle)
        arrow_lbl.bind("<Button-1>", _toggle)
        for child in header.winfo_children():
            child.bind("<Button-1>", _toggle)

        self._section_frames[key] = (header, body, collapsed)

    # ── Moon Placements ──
    def _build_moons(self, parent, moons_data):
        """
        Each kingdom gets a sub-collapsible group.
        Entry format:
          Moon Name  →  found in [Dest Kingdom]  via [Capture Tag]  by collecting [Unlock At]
        """
        for kingdom, entries in moons_data.items():
            kcolor = _kc(kingdom)
            grp = self._make_sub_group(parent, kingdom, kcolor)
            for e in entries:
                row = tk.Frame(grp, bg=BG_COLOR)
                row.pack(fill="x", padx=4, pady=1)

                moon_lbl = tk.Label(row, text=e["moon"], bg=BG_COLOR, fg=TEXT_COLOR,
                                    font=FONT_ZONES, anchor="w", cursor="hand2")
                moon_lbl.pack(side="left")
                self._all_text_items.append(moon_lbl)

                arrow = tk.Label(row, text="  →  ", bg=BG_COLOR, fg="#666666",
                                 font=FONT_ZONES)
                arrow.pack(side="left")

                dest_text = e["dest"]
                if e["capture"]:
                    dest_text += f"  [{e['capture']}]"
                dest_lbl = tk.Label(row, text=dest_text, bg=BG_COLOR,
                                    fg=_kc(e["dest"]), font=FONT_ZONES)
                dest_lbl.pack(side="left")
                self._all_text_items.append(dest_lbl)

                if e["unlock_at"]:
                    at_lbl = tk.Label(row, text=f"  @  {e['unlock_at']}",
                                      bg=BG_COLOR, fg="#888888", font=FONT_ZONES)
                    at_lbl.pack(side="left")
                    self._all_text_items.append(at_lbl)

    # ── Paintings ──
    def _build_paintings(self, parent, paintings):
        for a, b in paintings:
            row = tk.Frame(parent, bg=BG_COLOR)
            row.pack(fill="x", padx=12, pady=2)
            la = tk.Label(row, text=a, bg=BG_COLOR, fg=_kc(a), font=FONT_ZONES)
            la.pack(side="left")
            tk.Label(row, text="  ↔  ", bg=BG_COLOR, fg="#666666",
                     font=FONT_ZONES).pack(side="left")
            lb = tk.Label(row, text=b, bg=BG_COLOR, fg=_kc(b), font=FONT_ZONES)
            lb.pack(side="left")
            self._all_text_items.extend([la, lb])

    # ── Entrances ──
    def _build_entrances(self, parent, entrances_data):
        for kingdom, entries in entrances_data.items():
            kcolor = _kc(kingdom)
            grp = self._make_sub_group(parent, kingdom, kcolor)
            for e in entries:
                row = tk.Frame(grp, bg=BG_COLOR)
                row.pack(fill="x", padx=4, pady=1)
                from_lbl = tk.Label(row, text=e["from"], bg=BG_COLOR,
                                    fg="#c8a060", font=FONT_ZONES, anchor="w")
                from_lbl.pack(side="left")
                tk.Label(row, text="  →  ", bg=BG_COLOR, fg="#666666",
                         font=FONT_ZONES).pack(side="left")
                to_lbl = tk.Label(row, text=e["to"], bg=BG_COLOR,
                                  fg="#60b8c8", font=FONT_ZONES)
                to_lbl.pack(side="left")
                self._all_text_items.extend([from_lbl, to_lbl])

    # ── Progress Path ──
    def _build_path(self, parent, path):
        for step in path:
            row_outer = tk.Frame(parent, bg="#1c1c1c")
            row_outer.pack(fill="x", padx=4, pady=2)

            top = tk.Frame(row_outer, bg="#1c1c1c")
            top.pack(fill="x")

            num_lbl = tk.Label(top, text=f"{step['num']:03d}.", bg="#1c1c1c",
                               fg="#888888", font=FONT_ZONES, width=4, anchor="e")
            num_lbl.pack(side="left")

            kw_lbl = tk.Label(top, text=f" {step['kingdom']}:",
                              bg="#1c1c1c", fg=_kc(step["kingdom"]), font=FONT_ZONES)
            kw_lbl.pack(side="left")

            moon_lbl = tk.Label(top, text=f"  {step['moon']}",
                                bg="#1c1c1c", fg=TEXT_COLOR, font=FONT_ZONES)
            moon_lbl.pack(side="left")

            at_lbl = tk.Label(top, text=f"  @  {step['location']}",
                              bg="#1c1c1c", fg="#888888", font=FONT_ZONES)
            at_lbl.pack(side="left")
            self._all_text_items.extend([moon_lbl, kw_lbl, at_lbl])

            if step["unlocks"]:
                ul = tk.Label(row_outer,
                              text="  Unlocks: " + ", ".join(step["unlocks"]),
                              bg="#1c1c1c", fg="#70cc70", font=("Fredoka", 11))
                ul.pack(anchor="w", padx=6)
                self._all_text_items.append(ul)

    # ── Helpers ──
    def _make_sub_group(self, parent, title, color):
        """A nested collapsible group for per-kingdom data."""
        collapsed = tk.BooleanVar(value=False)
        hdr = tk.Frame(parent, bg="#1e1e1e", cursor="hand2")
        hdr.pack(fill="x", pady=(4, 0))
        arr_var = tk.StringVar(value="▼")
        arr = tk.Label(hdr, textvariable=arr_var, bg="#1e1e1e", fg="#888888",
                       font=FONT_NORMAL)
        arr.pack(side="left", padx=(10, 2))
        tk.Label(hdr, text=title, bg="#1e1e1e", fg=color,
                 font=FONT_NORMAL).pack(side="left", pady=3)

        body = tk.Frame(parent, bg=BG_COLOR)
        body.pack(fill="x", padx=14, pady=(0, 2))

        def _tog(_=None):
            if collapsed.get():
                body.pack(fill="x", padx=14, pady=(0, 2))
                arr_var.set("▼")
            else:
                body.pack_forget()
                arr_var.set("▶")
            collapsed.set(not collapsed.get())

        hdr.bind("<Button-1>", _tog)
        arr.bind("<Button-1>", _tog)
        for c in hdr.winfo_children():
            c.bind("<Button-1>", _tog)

        return body

    # ------------------------------------------------------------------ #
    #  Raw view
    # ------------------------------------------------------------------ #

    def _build_raw(self):
        frame = tk.Frame(self._pane, bg=BG_COLOR)
        self._raw_frame = frame

        text_box = ctk.CTkTextbox(frame, font=("Courier", 11),
                                  fg_color="#0e0e0e", text_color="#cccccc",
                                  scrollbar_button_color="#333333")
        text_box.pack(fill="both", expand=True, padx=6, pady=6)
        text_box.insert("1.0", self._data["raw"])
        text_box.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  Live search / highlight
    # ------------------------------------------------------------------ #

    def _on_search_changed(self, *_):
        query = self._search_var.get().strip().lower()
        first_match_widget = None

        for lbl in self._all_text_items:
            if not lbl.winfo_exists():
                continue
            try:
                text = lbl.cget("text").lower()
            except Exception:
                continue

            if query and query in text:
                lbl.configure(bg=HIGHLIGHT_BG)
                # Auto-expand sections that contain a match
                self._ensure_section_visible(lbl)
                if first_match_widget is None:
                    first_match_widget = lbl
            else:
                # Restore original bg
                parent_bg = lbl.master.cget("bg") if lbl.master else BG_COLOR
                lbl.configure(bg=parent_bg)

        # Scroll so the first match is visible, after Tk has processed layout changes
        if first_match_widget is not None:
            self.after(50, lambda w=first_match_widget: self._scroll_to_widget(w))

    def _scroll_to_widget(self, widget):
        """Scroll the structured canvas so that widget is near the top of the viewport."""
        if not hasattr(self, "_scroll_canvas") or not self._scroll_canvas.winfo_exists():
            return
        if not widget.winfo_exists():
            return

        canvas = self._scroll_canvas
        inner = self._structured_inner

        # winfo_rooty gives absolute screen Y; subtract inner frame's screen Y
        # to get the widget's Y position within the scrollable inner frame.
        try:
            widget_abs_y = widget.winfo_rooty()
            inner_abs_y  = inner.winfo_rooty()
            widget_y_in_inner = widget_abs_y - inner_abs_y
        except Exception:
            return

        inner_height = inner.winfo_height()
        if inner_height <= 0:
            return

        # Place the match ~10% from the top of the viewport for comfortable reading
        fraction = max(0.0, min(1.0, (widget_y_in_inner - 30) / inner_height))
        canvas.yview_moveto(fraction)

    def _ensure_section_visible(self, widget):
        """Walk up the widget tree and un-collapse any section that contains widget."""
        w = widget
        for _ in range(30):
            if w is None or not w.winfo_exists():
                return
            for key, (hdr, body, collapsed) in self._section_frames.items():
                if body == w or str(w).startswith(str(body)):
                    if collapsed.get():
                        # Simulate a toggle click to expand
                        body.pack(fill="x", padx=8, pady=(0, 4))
                        collapsed.set(False)
            try:
                w = w.master
            except Exception:
                return


# ------------------------------------------------------------------ #
#  Standalone loader helper (called from Settings)
# ------------------------------------------------------------------ #

def load_spoiler_log_file(parent_app):
    """
    Open a file picker for .json OR .txt files.
    Parse the result and open (or refresh) a SpoilerLogWindow on parent_app.
    """
    path = filedialog.askopenfilename(
        title="Load Spoiler Log",
        filetypes=[
            ("Spoiler Log files", "*.json *.txt"),
            ("JSON files", "*.json"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ]
    )
    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as exc:
        import tkinter.messagebox as mb
        mb.showerror("Spoiler Log", f"Could not read file:\n{exc}")
        return

    # Try to parse as JSON first (future-proofing), else plain text
    try:
        obj = json.loads(raw)
        # Wrap JSON as raw text for display; structured parsing is on plain-text format
        data = parse_spoiler_log("")
        data["raw"] = json.dumps(obj, indent=2)
        data["meta"]["seed"] = str(obj.get("seed", ""))
    except json.JSONDecodeError:
        data = parse_spoiler_log(raw)

    # Reuse or create the window
    if hasattr(parent_app, "spoiler_window") and parent_app.spoiler_window.winfo_exists():
        parent_app.spoiler_window.destroy()
    parent_app.spoiler_window = SpoilerLogWindow(parent_app, data)
    fade_in(parent_app.spoiler_window)


# -------------------------
# Loading Zone Window
# -------------------------
class LoadingZoneWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Loading Zone Notes")
        self.geometry("800x800")
        self.configure(bg=BG_COLOR)

        # Clear Notes button moved to Settings window

        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.h_scroll = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set)

        self.canvas.pack(fill="both", expand=True)
        self.h_scroll.pack(fill="x")
        self.bind_events()

        self.content = tk.Frame(self.canvas, bg=BG_COLOR)
        self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.build_columns()

        self.content.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def clear_all(self):
        """Clear all notes, reset icons, and uncollapse zones."""
        for kingdom in self.parent.loading_zones.values():
            for zone in kingdom["zones"].values():
                zone["note"] = ""
                zone["icon"] = "Moon.png"
                zone.pop("icon2", None)
                zone["collapsed"] = False
        self.parent.save_state()
        # Rebuild the columns to reflect cleared state
        self.content.destroy()
        self.content = tk.Frame(self.canvas, bg=BG_COLOR)
        self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.build_columns()
        self.content.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def build_columns(self):
        self.columns = {}
        for col, (kingdom, data) in enumerate(self.parent.loading_zones.items()):
            frame = KingdomColumn(self.content, kingdom, data, self.parent)
            frame.grid(row=0, column=col, padx=20, sticky="n")
            self.columns[kingdom] = frame

    def bind_events(self):
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.xview_scroll(-6, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.xview_scroll(6, "units"))

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.canvas.xview_scroll(-1, "units")
        else:
            self.canvas.xview_scroll(1, "units")


class KingdomColumn(tk.Frame):
    def __init__(self, parent, name, data, app):
        super().__init__(parent, bg=BG_COLOR)
        self.app = app
        self.name = name
        self.data = data
        self.visible = tk.BooleanVar(value=False)

        header = tk.Frame(self, bg=BG_COLOR)
        header.pack()

        icon = ImageTk.PhotoImage(resize_by_height(Image.open(data["icon"]), 20))
        self.icon = icon

        tk.Checkbutton(
            header,
            image=icon,
            text=name,
            compound="left",
            fg=data["color"],
            bg=BG_COLOR,
            selectcolor=BG_COLOR,
            variable=self.visible,
            command=self.toggle,
            font=FONT_BIG
        ).pack()

        zones = list(data["zones"].keys())
        MAX_PER_COL = 10

        self.columns_frame = tk.Frame(self, bg=BG_COLOR)
        self.columns_frame.pack()

        for col_idx in range(0, len(zones), MAX_PER_COL):
            col_frame = tk.Frame(self.columns_frame, bg=BG_COLOR)
            col_frame.grid(row=0, column=col_idx // MAX_PER_COL, padx=10, sticky="n")
            for zone in zones[col_idx: col_idx + MAX_PER_COL]:
                LoadingZoneRow(col_frame, name, zone, data, app).pack(anchor="w", pady=4)

        # Start collapsed since visible defaults to False
        self.columns_frame.pack_forget()

    def toggle(self):
        if self.visible.get():
            self.columns_frame.pack()
        else:
            self.columns_frame.pack_forget()


class LoadingZoneRow(tk.Frame):
    def __init__(self, parent, kingdom, zone, data, app):
        super().__init__(parent, bg=BG_COLOR)

        self.app = app
        self.num = app.loading_zones[kingdom]["zones"][zone].get("num", 1)
        self.state = app.loading_zones[kingdom]["zones"].setdefault(zone, {})
        self.state.setdefault("note", "")
        self.state.setdefault("icon", "Moon.png")
        self.state.setdefault("icon2", "Moon.png")
        self.state.setdefault("collapsed", False)
        self.color = data["color"]

        self.icon_img = ImageTk.PhotoImage(resize_by_height(Image.open(resource_path("assets/Moon.png")), 18))
        self.dark_icon = ImageTk.PhotoImage(resize_by_height(Image.open(resource_path("assets/Moon_Dark.png")), 18))

        top = tk.Frame(self, bg=BG_COLOR)
        top.pack(anchor="w")

        if self.num > 0:
            self.icon_label = tk.Label(top, image=self.icon_img, bg=BG_COLOR, cursor="hand2")
            self.icon_label.pack(side="left")
            self.icon_label.bind("<Button-1>", lambda e: self.open_icon_picker(self.icon_label))
            self.icon_photo = self.icon_img

        if self.num > 1:
            self.icon_label2 = tk.Label(top, image=self.icon_img, bg=BG_COLOR, cursor="hand2")
            self.icon_label2.pack(side="left")
            self.icon_label2.bind("<Button-1>", lambda e: self.open_icon_picker(self.icon_label2))
            self.icon_photo2 = self.icon_img

        self.name_label = tk.Label(
            top,
            text=zone,
            fg=data["color"],
            bg=BG_COLOR,
            cursor="hand2",
            font=FONT_ZONES
        )
        self.name_label.pack(side="left", padx=6)

        self.text = ctk.CTkTextbox(self, width=200, height=30, font=FONT_ZONES)
        self.text.insert("1.0", self.state["note"])
        self.text.pack(anchor="w", pady=(4, 8))
        self.text.bind("<KeyRelease>", lambda e: self.save_note())

        self.name_label.bind("<Button-1>", self.toggle)

        if self.num >= 1:
            if self.state["collapsed"]:
                self.name_label.config(fg="gray")
                self.text.pack_forget()
                self.icon_label.config(image=self.dark_icon)

            icon_name = self.state.get("icon", "Moon.png")
            icon_path = resource_path(f"assets/{icon_name}")
            if os.path.exists(icon_path):
                img = ImageTk.PhotoImage(resize_by_height(Image.open(icon_path), 18))
                self.icon_label.config(image=img)
                self.icon_photo = img

            if self.num > 1:
                icon2 = self.state.get("icon2", "Moon.png")
                path2 = resource_path(f"assets/{icon2}")
                if os.path.exists(path2):
                    img2 = ImageTk.PhotoImage(resize_by_height(Image.open(path2), 18))
                    self.icon_label2.config(image=img2)
                    self.icon_photo2 = img2

    def toggle(self, _):
        self.state["collapsed"] = not self.state["collapsed"]
        if self.state["collapsed"]:
            self.name_label.config(fg="gray")
            self.text.pack_forget()
            self.icon_label.config(image=self.dark_icon)
            if self.num > 1:
                self.icon_label2.config(image=self.dark_icon)
        else:
            self.name_label.config(fg=self.color)
            self.text.pack()
            self.icon_label.config(image=self.icon_img)
            if self.num > 1:
                self.icon_label2.config(image=self.icon_img)
        self.app.save_state()

    def save_note(self):
        self.state["note"] = self.text.get("1.0", "end-1c")
        self.app.save_state()

    def open_icon_picker(self, target_label):
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.configure(bg="#222222")

        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        win.geometry(f"+{x}+{y}")

        win.focus_force()
        win.bind("<FocusOut>", lambda e: win.destroy())

        icons = ["Cascade.png", "Sand.png", "Lake.png", "Wooded.png", "Lost.png",
                 "Metro.png", "Snow.png", "Seaside.png", "Luncheon.png", "Ruin.png",
                 "Bowser.png", "Cap.png", "Dark.png", "Star.png", "Moon.png",
                 "Moon_Dark.png", "checkmark.png", "xmark.png"]
        win.images = []

        for idx, icon in enumerate(icons):
            img = ImageTk.PhotoImage(resize_by_height(Image.open(resource_path(f"assets/{icon}")), 20))
            lbl = tk.Label(win, image=img, bg="#222222", cursor="hand2")
            row = idx // 6
            col = idx % 6
            lbl.grid(row=row, column=col, padx=4, pady=4)
            win.images.append(img)
            lbl.bind("<Button-1>", lambda e, i=icon, im=img: self.set_icon(i, im, target_label, win))

    def set_icon(self, icon_name, image, target_label, win):
        target_label.config(image=image)
        if target_label == self.icon_label:
            self.icon_photo = image
        elif hasattr(self, "icon_label2") and target_label == self.icon_label2:
            self.icon_photo2 = image

        if target_label == self.icon_label:
            self.state["icon"] = icon_name
        elif hasattr(self, "icon_label2") and target_label == self.icon_label2:
            self.state["icon2"] = icon_name

        self.app.save_state()
        win.destroy()


# -------------------------
# Main App
# -------------------------
class TrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Moon Tracker")
        self.geometry("780x800")
        self.configure(bg=BG_COLOR)

        self.white_icons = False
        self.dark_enabled = False
        self.star_enabled = False
        self.cap_enabled = False
        self.obs_optional_hidden = False

        self.main_container = tk.Frame(self, bg=BG_COLOR)
        self.main_container.pack(fill="both", expand=True)

        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_column = tk.Frame(self.main_container, bg=BG_COLOR)
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(10, 0))

        self.right_sidebar = tk.Frame(self.main_container, bg=BG_COLOR)
        self.right_sidebar.grid(row=0, column=1, sticky="nsew", padx=(20, 20))

        self.right_sidebar.grid_rowconfigure(0, weight=0)
        self.right_sidebar.grid_rowconfigure(1, weight=0)
        self.right_sidebar.grid_rowconfigure(2, weight=0)
        self.right_sidebar.grid_columnconfigure(0, weight=1)

        self.tracker_frame = tk.Frame(self.right_sidebar, bg=BG_COLOR)
        self.tracker_frame.grid(row=1, column=0)

        self.collective_title = tk.Label(
            self.tracker_frame,
            text="Moon Tracker",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=FONT_BIG
        )
        self.collective_title.pack(pady=(0, 12))

        self.collective_total_label = tk.Label(
            self.tracker_frame,
            text="0 / 124",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("Fredoka", 22, "bold")
        )
        self.collective_total_label.pack(pady=(0, 12))

        self.collective_target_var = tk.StringVar(value="124")
        self.collective_target_var.trace_add("write", lambda *_: self.update_collective_tracker())

        self.collective_target_entry = ctk.CTkEntry(
            self.tracker_frame,
            width=100,
            textvariable=self.collective_target_var
        )
        self.collective_target_entry.pack()

        # Notes button — below the Moon Tracker
        ctk.CTkButton(
            self.tracker_frame, text="Notes", command=self.open_loading_zone_window,
            font=FONT_NORMAL, corner_radius=12, width=100
        ).pack(pady=(10, 0))

        # Settings button — below Notes (black)
        ctk.CTkButton(
            self.tracker_frame, text="Settings", command=self.open_settings_window,
            font=FONT_NORMAL, corner_radius=12, width=100,
            fg_color="#000000", hover_color="#222222", text_color="#ffffff"
        ).pack(pady=(6, 0))

        # --- Toolbar icons are now in Settings; build them (hidden) ---
        self._build_toolbar()

        # --- Kingdom rows ---
        KINGDOMS = {
            "Cascade Kingdom": (resource_path("assets/Cascade.png"), resource_path("assets/Cascade_moon.png")),
            "Sand Kingdom": (resource_path("assets/Sand.png"), resource_path("assets/Sand_moon.png")),
            "Lake Kingdom": (resource_path("assets/Lake.png"), resource_path("assets/Lake_moon.png")),
            "Wooded Kingdom": (resource_path("assets/Wooded.png"), resource_path("assets/Wooded_moon.png")),
            "Lost Kingdom": (resource_path("assets/Lost.png"), resource_path("assets/Lost_moon.png")),
            "Metro Kingdom": (resource_path("assets/Metro.png"), resource_path("assets/Metro_moon.png")),
            "Snow Kingdom": (resource_path("assets/Snow.png"), resource_path("assets/Snow_moon.png")),
            "Seaside Kingdom": (resource_path("assets/Seaside.png"), resource_path("assets/Seaside_moon.png")),
            "Luncheon Kingdom": (resource_path("assets/Luncheon.png"), resource_path("assets/Luncheon_moon.png")),
            "Ruined Kingdom": (resource_path("assets/Ruin.png"), resource_path("assets/Ruin_moon.png")),
            "Bowser Kingdom": (resource_path("assets/Bowser.png"), resource_path("assets/Bowser_moon.png")),
        }

        self.loading_zones = {
            "Cap": {
                "color": "#fff500",
                "icon": resource_path("assets/Cap.png"),
                "zones": {
                    "Orange": {"num": 2},
                    "Paragoomba": {"num": 2},
                    "Frog": {"num": 2},
                    "Rolling On": {"num": 2},
                }
            },
            "Cascade": {
                "color": "#ff9900",
                "icon": resource_path("assets/Cascade.png"),
                "zones": {
                    "Dino": {"num": 2},
                    "2D": {"num": 2},
                    "Chain Chomp": {"num": 2},
                    "Swings": {"num": 2},
                    "Windy": {"num": 2},
                }
            },
            "Sand": {
                "color": "#8bf12c",
                "icon": resource_path("assets/Sand.png"),
                "zones": {
                    "Icy Cave": {"num": 1},
                    "Moe-eye": {"num": 2},
                    "Shop": {"num": 1},
                    "Employees": {"num": 1},
                    "Slots": {"num": 1},
                    "Rumble": {"num": 1},
                    "Outfit": {"num": 1},
                    "Jaxi Ruins": {"num": 2},
                    "Bullet Bill": {"num": 2},
                    "Gushen": {"num": 2},
                    "Sphynx": {"num": 1},
                    "Moving Platform": {"num": 2},
                    "Rocket": {"num": 2},
                    "Colossal Ruins": {"num": 2},
                }
            },
            "Lake": {
                "color": "#e46cab",
                "icon": resource_path("assets/Lake.png"),
                "zones": {
                    "Poison Waves": {"num": 2},
                    "Zipper": {"num": 2},
                    "Grab Climb": {"num": 2},
                    "Shop": {"num": 1},
                    "Puzzle": {"num": 1},
                }
            },
            "Wooded": {
                "color": "#1e65e7",
                "icon": resource_path("assets/Wooded.png"),
                "zones": {
                    "DW Odyssey": {"num": 0},
                    "DW Red Maze": {"num": 0},
                    "DW Pond": {"num": 0},
                    "DW Treasure": {"num": 1},
                    "DW Outfit": {"num": 1},
                    "Rocket": {"num": 2},
                    "Sheep": {"num": 2},
                    "Tank": {"num": 2},
                    "Vine Clouds": {"num": 2},
                    "Breakdown": {"num": 2},
                    "Invisible": {"num": 2},
                    "Flooded Pipes": {"num": 2},
                    "Flower Road": {"num": 2},
                    "Treasure Room": {"num": 1},
                }
            },
            "Lost": {
                "color": "#e71edd",
                "icon": resource_path("assets/Lost.png"),
                "zones": {
                    "Wiggler": {"num": 2},
                    "Shop": {"num": 1},
                    "Klepto": {"num": 2},
                }
            },
            "Metro": {
                "color": "#de7d5e",
                "icon": resource_path("assets/Metro.png"),
                "zones": {
                    "Yellow Shop": {"num": 1},
                    "Purple Shop": {"num": 1},
                    "Dino": {"num": 2},
                    "Bullet Billding": {"num": 2},
                    "Taxi": {"num": 2},
                    "Notes": {"num": 1},
                    "2D": {"num": 2},
                    "Slots": {"num": 1},
                    "People": {"num": 2},
                    "Outfit": {"num": 2},
                    "Rocket": {"num": 2},
                    "Dark": {"num": 2},
                    "Scaffolding": {"num": 2},
                    "Scooter": {"num": 2},
                    "Rotating Maze": {"num": 2},
                    "RC Car": {"num": 2},
                }
            },
            "Snow": {
                "color": "#e7930a",
                "icon": resource_path("assets/Snow.png"),
                "zones": {
                    "Puzzle": {"num": 1},
                    "Capless": {"num": 2},
                    "Rocket Flower": {"num": 2},
                    "Iceburn": {"num": 2},
                    "Flower Road": {"num": 2},
                    "Tracewalking": {"num": 1},
                    "Clouds": {"num": 2},
                    "Outfit": {"num": 2},
                    "Shop": {"num": 1},
                }
            },
            "Seaside": {
                "color": "#b36fe9",
                "icon": resource_path("assets/Seaside.png"),
                "zones": {
                    "Well Enter": {"num": 1},
                    "Well Exit": {"num": 1},
                    "Rumble": {"num": 1},
                    "Rocket": {"num": 2},
                    "Outfit": {"num": 1},
                    "Gushen": {"num": 2},
                    "Sphynx": {"num": 1},
                    "Pokio": {"num": 2},
                    "Lava Rising": {"num": 2},
                    "Sandy Bottom": {"num": 1},
                    "Spinning Maze": {"num": 2},
                }
            },
            "Luncheon": {
                "color": "#3fddbb",
                "icon": resource_path("assets/Luncheon.png"),
                "zones": {
                    "Magma Swamp": {"num": 2},
                    "Forks": {"num": 2},
                    "Cheese Rocks": {"num": 2},
                    "Veggie Room": {"num": 1},
                    "Slots": {"num": 1},
                    "Shop": {"num": 1},
                    "Outfit": {"num": 2},
                    "Spinning Athletics": {"num": 2},
                    "Lava Islands": {"num": 2},
                    "Volcano Cave": {"num": 2},
                    "Gears": {"num": 2},
                    "Magma Path": {"num": 2},
                }
            },
            "Ruined": {
                "color": "#ffd7e2",
                "icon": resource_path("assets/Ruin.png"),
                "zones": {
                    "Chargin' Chuck": {"num": 2},
                    "Rocket": {"num": 2},
                }
            },
            "Bowser's": {
                "color": "#d3304c",
                "icon": resource_path("assets/Bowser.png"),
                "zones": {
                    "Jizo": {"num": 2},
                    "Shop": {"num": 1},
                    "Outfit": {"num": 2},
                    "Treasure Room": {"num": 1},
                    "Spinning Tower": {"num": 2},
                    "Vine Clouds": {"num": 2},
                    "Hexagon Tower": {"num": 2},
                    "Wooden Tower": {"num": 2},
                }
            },
            "Mushroom": {
                "color": "#fff672",
                "icon": resource_path("assets/Star.png"),
                "zones": {
                    "Shop": {"num": 1},
                    "Castle Door": {"num": 2},
                    "Outfit": {"num": 2},
                    "Cloud Sea": {"num": 2},
                    "Well": {"num": 2},
                    "Knucklotec": {"num": 1},
                    "Torkdrift": {"num": 1},
                    "Mechawiggler": {"num": 1},
                    "Octopus": {"num": 1},
                    "Cookatiel": {"num": 1},
                    "Dragon": {"num": 1},
                    "Rocket": {"num": 2},
                }
            },
            "Darkside": {
                "color": "#fff2c6",
                "icon": resource_path("assets/Dark.png"),
                "zones": {
                    "Breakdown": {"num": 2},
                    "Invisible": {"num": 2},
                    "Vanishing": {"num": 2},
                    "Yoshi Siege": {"num": 2},
                    "Lava Rising": {"num": 2},
                    "Magma Swamp": {"num": 2},
                }
            },
            "Darkerside": {
                "color": "#fff2c6",
                "icon": resource_path("assets/Dark.png"),
                "zones": {
                    "Pipe": {"num": 1},
                }
            },
        }

        # --- Special rows (hidden by default) ---
        # Cap row: will be packed ABOVE Cascade (index 0)
        self.cap_row = SimpleCounterRow(self.left_column, resource_path("assets/Cap.png"), self)
        # Star row: will be packed BELOW Bowser (last moon_row) - now uses Spark_pylon_Capture icon
        self.star_row = SimpleCounterRow(self.left_column, resource_path("assets/Star.png"), self)
        # Dark row: will be packed BELOW Star (or below Bowser if Star hidden)
        self.dark_row = MoonRow(self.left_column, resource_path("assets/Moon.png"), app=self)

        # --- Standard kingdom rows ---
        self.moon_rows = []
        for name, (k_img, m_img) in KINGDOMS.items():
            row = MoonRow(self.left_column, k_img, app=self)
            row.pack(pady=5)
            self.moon_rows.append(row)

        self.obs = None

        # Controls live in the right sidebar (below the collective tracker).
        #
        # Layout (2-column grid):
        #   col 0, rows 0-3 : buttons (Hide Ability Lock, Open OBS, Toggle OBS BG, Clear)
        #   col 1, rows 0-1 : Moon Cave  (left_captures,  rowspan=2)
        #   col 1, rows 2-3 : Cave Skip  (right_captures, rowspan=2)
        #   col 0, row  4   : Cap Moon Count   — toggleable
        #   col 0, row  5   : Cloud Moon Count — toggleable
        #   col 0, row  6   : Capture Count    — toggleable
        #   col 0, row  7   : Ability Count    — toggleable
        self.controls_frame = tk.Frame(self.right_sidebar, bg=BG_COLOR)
        controls_frame = self.controls_frame
        controls_frame.grid(row=2, column=0, pady=(20, 10))
        controls_frame.grid_columnconfigure(0, weight=1)
        controls_frame.grid_columnconfigure(1, weight=0)

        # Col 0 buttons
        self.icons_visible = True
        # hide_ability_btn lives in the Settings window; create it as a detached widget
        # (no parent frame yet — it will be re-parented when SettingsWindow is created)
        self._hide_ability_text = tk.StringVar(value="Hide Ability Lock")

        ctk.CTkButton(controls_frame, text="Open OBS Overlay", command=self.open_obs,
                      font=FONT_NORMAL, corner_radius=12, fg_color="#cc0000", hover_color="#aa0000").grid(row=0, column=0, pady=(0,5), sticky="ew")

        ctk.CTkButton(controls_frame, text="Toggle OBS BG", command=self.toggle_obs_bg,
                      font=FONT_NORMAL, corner_radius=12, fg_color="#2a7a2a", hover_color="#1f5c1f").grid(row=1, column=0, sticky="ew")

        # Clear button moved to Settings window

        # Col 1 – Moon Cave ABOVE Cave Skip, packed vertically so they never overlap
        self._captures_col = tk.Frame(controls_frame, bg=BG_COLOR)
        self._captures_col.grid(row=0, column=1, rowspan=4, padx=(12, 0), sticky="n")

        tk.Label(self._captures_col, text="Moon Cave", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 11, "bold")).pack(pady=(0, 2))
        self.left_captures = CaptureRow(self._captures_col)
        self.left_captures.pack(pady=(0, 6))

        tk.Label(self._captures_col, text="Cave Skip", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 11, "bold")).pack(pady=(0, 2))
        self.right_captures = AbilityRow(self._captures_col, app=self)
        self.right_captures.pack()

        # Toggleable rows — col 0, fixed rows so order never shifts
        # Row 4 – Cap Moon Count
        self.sidebar_cap_row = SimpleCounterRow(controls_frame, resource_path("assets/Cap.png"), self)
        self.sidebar_cap_row.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        self.sidebar_cap_row.grid_remove()

        # Row 5 – Cloud Moon Count
        self.cloud_row = SimpleCounterRow(controls_frame, resource_path("assets/Cloud.png"), self)
        self.cloud_enabled = False
        self.cloud_row.grid(row=5, column=0, columnspan=2, pady=(4, 0))
        self.cloud_row.grid_remove()

        # Row 6 – Capture Count
        self.sidebar_star_row = SimpleCounterRow(controls_frame, resource_path("assets/Star.png"), self)
        self.sidebar_star_row.grid(row=6, column=0, columnspan=2, pady=(4, 0))
        self.sidebar_star_row.grid_remove()

        # Row 7 – Ability Count
        self.sidebar_ability_row = SidebarAbilityRow(controls_frame, self)
        self.sidebar_ability_row.grid(row=7, column=0, columnspan=2, pady=(4, 0))
        self.sidebar_ability_row.grid_remove()

        # Visibility flags for right sidebar rows
        self.sidebar_cap_visible = False
        self.sidebar_captures_visible = False
        self.sidebar_ability_visible = False

        self.load_state()
        self.update_collective_tracker()

        # Auto-position and auto-open all windows on startup
        self.after(100, self._auto_open_windows)

    def _auto_open_windows(self):
        """Position main window in centre, then open OBS on the right and Settings on the left."""
        self.update_idletasks()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        mw = self.winfo_width()
        mh = self.winfo_height()

        # Main window: centre of screen
        mx = (sw - mw) // 2
        my = (sh - mh) // 2
        self.geometry(f"{mw}x{mh}+{mx}+{my}")

        # Open OBS overlay and position it on the right side
        self.open_obs()
        if self.obs and self.obs.winfo_exists():
            self.obs.update_idletasks()
            ow = self.obs.winfo_width()
            oh = self.obs.winfo_height()
            ox = sw - ow - 10          # 10 px gap from right edge
            oy = (sh - oh) // 2
            self.obs.geometry(f"{ow}x{oh}+{ox}+{oy}")
            fade_in(self.obs)

        # Open Settings and position it on the left side
        self.open_settings_window()
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.update_idletasks()
            sw2 = self.settings_window.winfo_width()
            sh2 = self.settings_window.winfo_height()
            sx = 10                    # 10 px gap from left edge
            sy = (sh - sh2) // 2
            self.settings_window.geometry(f"{sw2}x{sh2}+{sx}+{sy}")
            fade_in(self.settings_window)

    # ------------------------------------------------------------------
    # Toolbar (req #3: image-based buttons with blue background)
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        ICON_SIZE = 28       # regular toolbar icon size
        WHITE_ICON_SIZE = 40 # larger size for White Icons button

        # Load metro icon for "White Icons" toggle button — larger size, plain (no rounding)
        metro_img = resize_by_width(Image.open(resource_path("assets/Metro.png")).convert("RGBA"), WHITE_ICON_SIZE)
        metro_white = self._make_image_white(metro_img)
        self.metro_color_photo = ImageTk.PhotoImage(metro_img)
        self.metro_white_photo = ImageTk.PhotoImage(metro_white)

        # Load toolbar icons for Dark / Star / Cap / Cloud / Captures / Ability
        self.tb_dark_photo = ImageTk.PhotoImage(
            resize_by_width(Image.open(resource_path("assets/Moon.png")).convert("RGBA"), ICON_SIZE)
        )
        self.tb_star_photo = ImageTk.PhotoImage(
            resize_by_width(Image.open(resource_path("assets/Spark_pylon_Capture.png")).convert("RGBA"), ICON_SIZE)
        )
        self.tb_cap_photo = ImageTk.PhotoImage(
            resize_by_width(Image.open(resource_path("assets/Cap.png")).convert("RGBA"), ICON_SIZE)
        )
        self.tb_cloud_photo = ImageTk.PhotoImage(
            resize_by_width(Image.open(resource_path("assets/Cloud.png")).convert("RGBA"), ICON_SIZE)
        )
        self.tb_captures_photo = ImageTk.PhotoImage(
            resize_by_width(Image.open(resource_path("assets/Star.png")).convert("RGBA"), ICON_SIZE)
        )
        self.tb_ability_photo = ImageTk.PhotoImage(
            resize_by_width(Image.open(resource_path("assets/Dark.png")).convert("RGBA"), ICON_SIZE)
        )

        # Toolbar frame is no longer shown — buttons moved to Settings window
        # (images are still loaded above for use in Settings and toggle logic)
        pass

    # ------------------------------------------------------------------
    # Row placement helpers (req #4)
    # ------------------------------------------------------------------
    def _repack_special_rows(self):
        """
        Enforce exact row order:
          Cap (if visible) → Cascade…Wooded → Lost…Bowser → Dark (if visible) → Star (if visible)
        Uses pack's `before`/`after` to slot correctly among existing widgets.
        """
        # Find the first and last moon row widgets
        first_kingdom = self.moon_rows[0]   # Cascade
        last_kingdom = self.moon_rows[-1]   # Bowser

        # --- Cap: directly above Cascade ---
        if self.cap_enabled:
            self.cap_row.pack_forget()
            self.cap_row.pack(before=first_kingdom, pady=5)
        else:
            self.cap_row.pack_forget()

        # --- Dark: directly below Bowser ---
        if self.dark_enabled:
            self.dark_row.pack_forget()
            self.dark_row.pack(after=last_kingdom, pady=5)
        else:
            self.dark_row.pack_forget()

        # --- Star: directly below Dark (if visible) else below Bowser ---
        if self.star_enabled:
            self.star_row.pack_forget()
            if self.dark_enabled:
                self.star_row.pack(after=self.dark_row, pady=5)
            else:
                self.star_row.pack(after=last_kingdom, pady=5)
        else:
            self.star_row.pack_forget()

    # ------------------------------------------------------------------
    # Toggle handlers (req #4 + #6)
    # ------------------------------------------------------------------
    def toggle_cap_row(self):
        """Cap button: only shows/hides the Cap counter on the right sidebar."""
        self.sidebar_cap_visible = not self.sidebar_cap_visible
        self._repack_sidebar_rows()
        self._notify_obs_sidebar_rows()
        self.save_state()
        self._refresh_settings_obs_optional_btn()

    def toggle_sidebar_captures_row(self):
        """Captures button: shows/hides the Spark_pylon counter on the right sidebar."""
        self.sidebar_captures_visible = not self.sidebar_captures_visible
        self._repack_sidebar_rows()
        self._notify_obs_sidebar_rows()

    def toggle_sidebar_ability_row(self):
        """Ability button: shows/hides the Long_Jump counter on the right sidebar."""
        self.sidebar_ability_visible = not self.sidebar_ability_visible
        self._repack_sidebar_rows()
        self._notify_obs_sidebar_rows()

    def _repack_sidebar_rows(self):
        """Show/hide the right-sidebar toggle rows using grid so order never changes.
        sidebar_star_row and sidebar_ability_row are also suppressed when icons_visible is False."""
        if self.sidebar_cap_visible:
            self.sidebar_cap_row.grid()
        else:
            self.sidebar_cap_row.grid_remove()
        if self.cloud_enabled:
            self.cloud_row.grid()
        else:
            self.cloud_row.grid_remove()
        if self.sidebar_captures_visible and self.icons_visible:
            self.sidebar_star_row.grid()
        else:
            self.sidebar_star_row.grid_remove()
        if self.sidebar_ability_visible and self.icons_visible:
            self.sidebar_ability_row.grid()
        else:
            self.sidebar_ability_row.grid_remove()

    def toggle_cloud_row(self):
        self.cloud_enabled = not self.cloud_enabled
        self._repack_cloud_row()
        self._notify_obs_cloud_row()
        self.save_state()
        self._refresh_settings_obs_optional_btn()

    def _repack_cloud_row(self):
        """Show/hide the Cloud counter row on the right sidebar using grid."""
        self._repack_sidebar_rows()

    def _notify_obs_cloud_row(self):
        if self.obs and self.obs.winfo_exists():
            self.obs.refresh_cloud_row(self.cloud_enabled)

    def toggle_star_row(self):
        self.star_enabled = not self.star_enabled
        self._repack_special_rows()
        self._notify_obs_special_rows()
        self.save_state()
        self._refresh_settings_obs_optional_btn()

    def toggle_dark_row(self):
        self.dark_enabled = not self.dark_enabled
        self._repack_special_rows()
        self._notify_obs_special_rows()
        self.update_collective_tracker()
        self.save_state()
        self._refresh_settings_obs_optional_btn()

    def toggle_obs_optional(self):
        """Hide or show Cap, Cloud, Star (Capture), and Dark (Movement Ability) rows in OBS only — does NOT hide Moon Kingdom (dark_obs)."""
        self.obs_optional_hidden = not self.obs_optional_hidden
        if self.obs and self.obs.winfo_exists():
            self.obs.set_optional_kingdoms_visible(not self.obs_optional_hidden)
        self._refresh_settings_obs_optional_btn()

    def _refresh_settings_obs_optional_btn(self):
        """Show the Hide Optional Kingdoms button only when at least one optional row is enabled."""
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_obs_optional_btn()

    def _notify_obs_special_rows(self):
        if self.obs and self.obs.winfo_exists():
            self.obs.refresh_special_rows(
                self.cap_enabled, self.star_enabled, self.dark_enabled,
                self.cloud_enabled
            )

    def _notify_obs_sidebar_rows(self):
        if self.obs and self.obs.winfo_exists():
            self.obs.refresh_sidebar_rows(
                self.sidebar_cap_visible,
                self.sidebar_captures_visible,
                self.sidebar_ability_visible
            )

    # ------------------------------------------------------------------
    # White icon toggle (req #1)
    # ------------------------------------------------------------------
    def _make_image_white(self, image):
        img = image.convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a > 0:
                    pixels[x, y] = (255, 255, 255, a)
        return img

    def toggle_white_icons(self):
        self.white_icons = not self.white_icons

        # Update all standard kingdom rows
        for row in self.moon_rows:
            row.apply_white_mode(self.white_icons)

        # Update Cap row icon (left column)
        self.cap_row.apply_white_mode(self.white_icons)

        # Update Cloud row icon (right sidebar)
        self.cloud_row.apply_white_mode(self.white_icons)

        # Update Dark row icon
        self.dark_row.apply_white_mode(self.white_icons)

        # Update sidebar Cap row icon (Row 1 on right)
        self.sidebar_cap_row.apply_white_mode(self.white_icons)

        # Update Star Moon Tracker and Dark Side Moon Tracker
        self.star_row.apply_white_mode(self.white_icons)
        self.sidebar_star_row.apply_white_mode(self.white_icons)
        self.sidebar_ability_row.apply_white_mode(self.white_icons)

        # Update the Settings window button if open.
        # When main view shows white icons → button shows colored icon (so user knows clicking reverts).
        # When main view shows colored icons → button shows white icon (so user knows clicking enables white).
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_white_icon_button()
        # OBS rows pick up changes automatically via white_icons_ref lambda

    # ------------------------------------------------------------------
    # Collective tracker (req #5: Dark contributes; Cap/Star do NOT)
    # ------------------------------------------------------------------
    def update_collective_tracker(self):
        total = sum(row.count for row in self.moon_rows)
        if self.dark_enabled:
            total += self.dark_row.count
        target = self.collective_target_var.get().strip() or "?"
        self.collective_total_label.config(text=f"{total} / {target}")

    # ------------------------------------------------------------------
    # OBS
    # ------------------------------------------------------------------
    def open_obs(self):
        if self.obs and self.obs.winfo_exists():
            # Already open — bring to front with a quick fade in
            fade_in(self.obs)
            return
        self.obs = OBSWindow(
            self,
            self.moon_rows,
            self.left_captures,
            self.right_captures,
            cap_row=self.cap_row,
            star_row=self.star_row,
            dark_row=self.dark_row,
            cloud_row=self.cloud_row,
            cap_enabled=self.cap_enabled,
            star_enabled=self.star_enabled,
            dark_enabled=self.dark_enabled,
            cloud_enabled=self.cloud_enabled,
            white_icons_ref=lambda: self.white_icons,
            sidebar_cap_row=self.sidebar_cap_row,
            sidebar_star_row=self.sidebar_star_row,
            sidebar_ability_row=self.sidebar_ability_row,
            icons_visible=self.icons_visible,
        )
        fade_in(self.obs)

    def open_settings_window(self):
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            fade_in(self.settings_window)
            return
        self.settings_window = SettingsWindow(self, self)
        fade_in(self.settings_window)

    def _clear_notes(self):
        """Clear all loading zone notes; refresh the Notes window if open."""
        for kingdom in self.loading_zones.values():
            for zone in kingdom["zones"].values():
                zone["note"] = ""
                zone["icon"] = "Moon.png"
                zone.pop("icon2", None)
                zone["collapsed"] = False
        self.save_state()
        if hasattr(self, "lz_window") and self.lz_window.winfo_exists():
            self.lz_window.clear_all()

    def open_loading_zone_window(self):
        if not hasattr(self, "lz_window") or not self.lz_window.winfo_exists():
            self.lz_window = LoadingZoneWindow(self)

    def toggle_obs_bg(self):
        if self.obs and self.obs.winfo_exists():
            self.obs.toggle_bg()

    def toggle_capture_icons(self):
        """Show/hide Moon Cave, Cave Skip, Capture count & Ability count. Toggles button label too."""
        self.icons_visible = not self.icons_visible
        if self.icons_visible:
            self._captures_col.grid()
            self.controls_frame.grid_columnconfigure(0, weight=1)
            self.controls_frame.grid_columnconfigure(1, weight=0)
            if self.sidebar_captures_visible:
                self.sidebar_star_row.grid()
            if self.sidebar_ability_visible:
                self.sidebar_ability_row.grid()
            self._hide_ability_text.set("Hide Ability Lock")
        else:
            self._captures_col.grid_remove()
            self.controls_frame.grid_columnconfigure(0, weight=1)
            self.controls_frame.grid_columnconfigure(1, weight=1)
            self.sidebar_star_row.grid_remove()
            self.sidebar_ability_row.grid_remove()
            self._hide_ability_text.set("Unhide Ability Lock")
        # Update Settings window button label if open
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_hide_ability_btn()
        self._refresh_settings_obs_optional_btn()
        if self.obs and self.obs.winfo_exists():
            self.obs.set_icons_visible(self.icons_visible)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset_all_moons(self):
        for row in self.moon_rows:
            row.reset()
        self.cap_row.reset()
        self.cloud_row.reset()
        self.star_row.reset()
        self.dark_row.reset()
        self.left_captures.reset()
        self.right_captures.reset()
        self.sidebar_cap_row.reset()
        self.sidebar_star_row.reset()
        self.sidebar_ability_row.reset()
        for kingdom in self.loading_zones.values():
            for zone in kingdom["zones"].values():
                zone["note"] = ""
                zone["icon"] = "Moon.png"
                zone["collapsed"] = False
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        self.collective_target_var.set("124")
        self.update_collective_tracker()

    # ------------------------------------------------------------------
    # Save / Load (req #2)
    # ------------------------------------------------------------------
    def save_state(self):
        dark_max = None
        if self.dark_row.max_val is not None:
            dark_max = self.dark_row.max_val

        data = {
            "loading_zones": self.loading_zones,
            "cap_enabled": self.cap_enabled,
            "cloud_enabled": self.cloud_enabled,
            "star_enabled": self.star_enabled,
            "dark_enabled": self.dark_enabled,
            "cap_count": self.cap_row.count,
            "cloud_count": self.cloud_row.count,
            "star_count": self.star_row.count,
            "dark_count": self.dark_row.count,
            "dark_max": dark_max,
            "moons": [
                {
                    "count": row.count,
                    "max": row.max_val,
                    "lock": row.lock_icon.active,
                    "peace": row.peace_icon.active,
                }
                for row in self.moon_rows
            ],
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Failed to save state:", e)

    def load_state(self):
        if not os.path.exists(STATE_FILE):
            return

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "loading_zones" in data:
                self.loading_zones = data["loading_zones"]

            # Restore special row visibility (triggers pack logic)
            if data.get("cap_enabled"):
                self.cap_enabled = True
            if data.get("cloud_enabled"):
                self.cloud_enabled = True
            if data.get("star_enabled"):
                self.star_enabled = True
            if data.get("dark_enabled"):
                self.dark_enabled = True

            # Restore special row counts
            self.cap_row.count = data.get("cap_count", 0)
            self.cap_row.count_label.config(text=str(self.cap_row.count))

            self.cloud_row.count = data.get("cloud_count", 0)
            self.cloud_row.count_label.config(text=str(self.cloud_row.count))

            self.star_row.count = data.get("star_count", 0)
            self.star_row.count_label.config(text=str(self.star_row.count))

            self.dark_row.count = data.get("dark_count", 0)
            dark_max = data.get("dark_max", None)
            self.dark_row.max_val = dark_max
            if dark_max is not None:
                self.dark_row.max_var.set(str(dark_max))
            self.dark_row.update_label()

            # Restore standard kingdom rows
            for row, saved in zip(self.moon_rows, data.get("moons", [])):
                row.count = saved["count"]
                row.max_val = saved.get("max")
                if row.max_val is not None:
                    row.max_var.set(str(row.max_val))
                row.lock_icon.active = saved["lock"]
                row.lock_icon.config(image=row.lock_icon.unlocked if saved["lock"] else row.lock_icon.locked)
                row.peace_icon.active = saved["peace"]
                row.peace_icon.config(image=row.peace_icon.unlocked if saved["peace"] else row.peace_icon.locked)
                row.update_label()

            # Apply correct packing order after restoring state
            self._repack_special_rows()
            self._repack_cloud_row()

        except Exception as e:
            print("Failed to load state:", e)


if __name__ == "__main__":
    TrackerApp().mainloop()
