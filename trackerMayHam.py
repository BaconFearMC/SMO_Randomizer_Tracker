import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import customtkinter as ctk
import os
import sys
import json
import re

# Hide the console window when running as a frozen PyInstaller bundle on Windows.
# On other platforms this block is a no-op.
if getattr(sys, "frozen", False):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    # Redirect stdout/stderr to devnull so stray prints do not crash when
    # there is no console attached (common on macOS .app and Linux --windowed builds).
    import io
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()


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

# ---------------------------------------------------------------------------
# Settings menu button switches.
# Set any value to 0 to make that button go away on boot (it will never be
# created). Everything defaults to 1 (visible/enabled).
# ---------------------------------------------------------------------------
SETTINGS_BUTTONS = {
    "total_moon_tracker":     1,   # Total Moon Tracker
    "white_kingdom_icons":    1,   # White Kingdom Icons
    "moon_counter_icons":     1,   # Moon Counter Icons
    "lock_peace_icons":       1,   # Lock & Peace Icons
    "cap_moon_tracker":       1,   # Cap Moon Tracker
    "cloud_moon_tracker":     1,   # Cloud Moon Tracker
    "moon_kingdom_tracker":   1,   # Moon Kingdom Tracker
    "timer":                  1,   # Toggle Timer
    "timer_ms":               1,   # Add Milliseconds to Timer
    "clear_tracker":          1,   # Clear Tracker
    "clear_notes":            1,   # Clear Notes
    "reset":                  1,   # RESET
    "open_obs":                1,   # Open OBS
    "optional_kingdoms_obs":   1,   # Toggle Optional Kingdoms in OBS
    "global_ability_lock":     1,   # Toggle Global Ability Lock
    "star":                    1,   # Star
    "dark_side":               1,   # Dark Side
    "peace_ability_lock":      1,   # Toggle Peace Ability Lock
    "peace_lock_obs":          1,   # Toggle Peace Lock in OBS
    "load_spoiler_log":        1,   # Load Spoiler Log
    "compact_view":            1,   # Compact View
}


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
        self._locked_path = locked_img
        self._unlocked_path = unlocked_img
        self.locked = ImageTk.PhotoImage(resize_by_width(Image.open(locked_img), 20))
        self.unlocked = ImageTk.PhotoImage(resize_by_width(Image.open(unlocked_img), 20))
        # Compact versions (11px wide ≈ 45% of 20)
        self.locked_compact = ImageTk.PhotoImage(resize_by_width(Image.open(locked_img), 11))
        self.unlocked_compact = ImageTk.PhotoImage(resize_by_width(Image.open(unlocked_img), 11))
        super().__init__(parent, image=self.locked, cursor="hand2", bg=bg)
        self.active = False
        self._compact = False
        self.bind("<Button-1>", self.toggle)

    def toggle(self, _=None):
        self.active = not self.active
        if self._compact:
            self.config(image=self.unlocked_compact if self.active else self.locked_compact)
        else:
            self.config(image=self.unlocked if self.active else self.locked)

    def set_compact(self, on):
        self._compact = on
        if self.active:
            self.config(image=self.unlocked_compact if on else self.unlocked)
        else:
            self.config(image=self.locked_compact if on else self.locked)

    def reset(self):
        self.active = False
        self.config(image=self.locked_compact if self._compact else self.locked)


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
# Peace Ability Lock capture icons
# -------------------------

# Per-kingdom capture sequences for "Hide Peace Ability Lock".
# Each entry is a list of tokens:
#   str   → capture name  (image: "capture{name}.png" or special: "Climb.png"/"GroundPound.png")
#   "/"   → slash separator (rendered as a "/" label)
#   "-"   → gap (same size as a regular icon gap)
KINGDOM_PEACE_CAPTURES = {
    "Cascade Kingdom": [
        "chainchomp", "-", "bigchainchomp", "/", "trex", "-", "goldenchainchomp",
    ],
    "Sand Kingdom": [
        "bulletbill", "-", "knucklotecsfist",
    ],
    "Lake Kingdom": [
        "zipper",
    ],
    "Wooded Kingdom": [
        "uproot", "-", "climb", "-", "sherm",
    ],
    "Lost Kingdom": [],
    "Metro Kingdom": [
        "pylon", "-", "climb", "-", "sherm", "-", "manhole",
    ],
    "Snow Kingdom": [
        "tyfoo", "-", "shiverianracer",
    ],
    "Seaside Kingdom": [
        "gushen",
    ],
    "Luncheon Kingdom": [
        "hammerbro", "-", "meat", "-", "lavabubble",
    ],
    "Ruined Kingdom": [
        "pylon", "-", "groundpound",
    ],
    "Bowser Kingdom": [
        "pylon", "-", "pokio",
    ],
}

# Mapping from kingdom name (as used in KINGDOMS dict keys and special rows) to moontick asset name
KINGDOM_MOONTICK_ASSET = {
    "Cascade Kingdom":  "moontickCascade",
    "Sand Kingdom":     "moontickSand",
    "Lake Kingdom":     "moontickLake",
    "Wooded Kingdom":   "moontickWooded",
    "Lost Kingdom":     "moontickLost",
    "Metro Kingdom":    "moontickMetro",
    "Snow Kingdom":     "moontickSnow",
    "Seaside Kingdom":  "moontickSeaside",
    "Luncheon Kingdom": "moontickLuncheon",
    "Ruined Kingdom":   "moontickRuined",
    "Bowser Kingdom":   "moontickBowsers",
    # Special rows
    "Cap":          "moontickCap",
    "Cloud":        "moontickCloud",
    "Star":         "moontickStar",
    "Moon Kingdom": "moontickMoon",
    "Dark Side":    "moontickDarkSide",
}

# Special filenames that don't follow the "capture{name}.png" pattern
_SPECIAL_CAPTURE_FILES = {
    "climb":       "Climb.png",
    "groundpound": "GroundPound.png",
}

def _capture_image_path(name):
    """Return the asset path for a capture icon by its token name."""
    if name in _SPECIAL_CAPTURE_FILES:
        return resource_path(f"assets/{_SPECIAL_CAPTURE_FILES[name]}")
    return resource_path(f"assets/capture{name}.png")


class PeaceCaptureIcon(tk.Label):
    """A single clickable capture icon that starts black (inactive) and lights up on click.
    Syncs with all other PeaceCaptureIcon instances that share the same capture name
    via the app-level registry."""

    ICON_SIZE = 52  # height in pixels — slightly larger than ToggleCaptures (normal Ability Lock size)

    def __init__(self, parent, capture_name, app, bg=BG_COLOR):
        self.capture_name = capture_name
        self.app = app

        img_path = _capture_image_path(capture_name)
        try:
            base_img = resize_by_height(Image.open(img_path).convert("RGBA"), self.ICON_SIZE)
        except Exception:
            # Fallback: plain grey rectangle if asset missing
            base_img = Image.new("RGBA", (self.ICON_SIZE, self.ICON_SIZE), (100, 100, 100, 255))

        self._img_color  = ImageTk.PhotoImage(base_img)
        self._img_black  = ImageTk.PhotoImage(self._make_black(base_img))

        super().__init__(parent, image=self._img_black, cursor="hand2", bg=bg)
        self.active = False
        self.bind("<Button-1>", self._on_click)

        # Register with app-level registry so duplicates stay in sync
        app._peace_capture_registry.setdefault(capture_name, []).append(self)

    def _make_black(self, image):
        """Returns a greyed-out (dark grey) version of the icon for the inactive state."""
        img = image.copy().convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a > 0:
                    pixels[x, y] = (60, 60, 60, a)
        return img

    def _on_click(self, _=None):
        # Toggle all icons with the same capture name together
        new_state = not self.active
        for icon in self.app._peace_capture_registry.get(self.capture_name, []):
            icon._set_state(new_state)

    def _set_state(self, state):
        self.active = state
        self.config(image=self._img_color if state else self._img_black)

    def reset(self):
        self._set_state(False)


class KingdomPeaceLockRow(tk.Frame):
    """A row of PeaceCaptureIcon widgets for one kingdom, shown next to its MoonRow.
    Hidden by default; revealed by the Hide Peace Ability Lock button."""

    def __init__(self, parent, kingdom_name, app, bg=BG_COLOR):
        super().__init__(parent, bg=bg)
        self.app = app
        self.kingdom_name = kingdom_name
        self._icons = []

        tokens = KINGDOM_PEACE_CAPTURES.get(kingdom_name, [])
        col = 0
        for token in tokens:
            if token == "/":
                tk.Label(self, text="/", bg=bg, fg=TEXT_COLOR,
                         font=("Fredoka", 14, "bold")).grid(row=0, column=col, padx=1)
                col += 1
            elif token == "-":
                # Gap: same visual weight as a regular inter-icon gap
                tk.Label(self, text="", bg=bg, width=2).grid(row=0, column=col)
                col += 1
            else:
                icon = PeaceCaptureIcon(self, token, app, bg=bg)
                icon.grid(row=0, column=col, padx=2)
                self._icons.append(icon)
                col += 1

    def reset(self):
        for icon in self._icons:
            icon.reset()


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

        # Moon tick icon — shown between kingdom icon and - button when enabled (col 4)
        self._moontick_photo = None
        self._moontick_label = tk.Label(self, bg=BG_COLOR)
        # Not gridded yet; apply_moontick manages placement

        self._btn_dec = ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG)
        self._btn_dec.grid(row=0, column=6, padx=5)

        self.label = tk.Label(self, text="0 / ?", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.label.grid(row=0, column=7, padx=5)

        self._btn_inc = ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG)
        self._btn_inc.grid(row=0, column=8, padx=5)

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

    def apply_compact(self, on):
        """Switch between normal and compact sizing for all non-kingdom-icon elements."""
        if on:
            # ~45% of normal: buttons 22×22, entry 28×19, font size 9
            compact_font = ("Fredoka", 9, "bold")
            self._btn_dec.configure(width=22, height=22, corner_radius=6, font=compact_font)
            self._btn_inc.configure(width=22, height=22, corner_radius=6, font=compact_font)
            self.entry.configure(width=28, height=19, corner_radius=6, font=compact_font)
            self.label.config(font=compact_font)
            self.lock_icon.set_compact(True)
            self.peace_icon.set_compact(True)
        else:
            self._btn_dec.configure(width=40, height=40, corner_radius=12, font=FONT_BIG)
            self._btn_inc.configure(width=40, height=40, corner_radius=12, font=FONT_BIG)
            self.entry.configure(width=50, height=35, corner_radius=10, font=FONT_BIG)
            self.label.config(font=FONT_BIG)
            self.lock_icon.set_compact(False)
            self.peace_icon.set_compact(False)

    def apply_moontick(self, enabled, asset_name=None):
        """Show or hide the moontick icon between the kingdom icon and - button."""
        if enabled and asset_name:
            if self._moontick_photo is None:
                try:
                    img = resize_by_height(Image.open(resource_path(f"assets/{asset_name}.png")).convert("RGBA"), 40)
                    self._moontick_photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._moontick_photo = None
            if self._moontick_photo:
                self._moontick_label.config(image=self._moontick_photo)
                self._moontick_label.grid(row=0, column=4, padx=(2, 0))
        else:
            self._moontick_label.grid_remove()

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

        # Moon tick icon — col 1, shown between kingdom icon and - button when enabled
        self._moontick_photo = None
        self._moontick_label = tk.Label(self, bg=BG_COLOR)
        # not gridded yet; apply_moontick manages placement at col 1

        ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=2)
        self.count_label = tk.Label(self, text="0", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.count_label.grid(row=0, column=3, padx=5)
        ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=4)

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

    def apply_moontick(self, enabled, asset_name=None):
        """Show or hide the moontick icon between the kingdom icon and - button."""
        if enabled and asset_name:
            if self._moontick_photo is None:
                try:
                    img = resize_by_height(Image.open(resource_path(f"assets/{asset_name}.png")).convert("RGBA"), 40)
                    self._moontick_photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._moontick_photo = None
            if self._moontick_photo:
                self._moontick_label.config(image=self._moontick_photo)
                self._moontick_label.grid(row=0, column=1, padx=(2, 0))
        else:
            self._moontick_label.grid_remove()

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

        # Moon tick icon — shown between icon (col 0) and - button (col 2) when enabled
        self._moontick_photo = None
        self._moontick_label = tk.Label(self, bg=BG_COLOR)
        # not gridded yet; apply_moontick manages placement at col 1

        ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=2)
        self.count_label = tk.Label(self, text="0", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.count_label.grid(row=0, column=3, padx=5)
        ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=4)

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

    def apply_moontick(self, enabled, asset_name=None):
        """Show or hide the moontick icon between the icon and - button."""
        if enabled and asset_name:
            if self._moontick_photo is None:
                try:
                    img = resize_by_height(Image.open(resource_path(f"assets/{asset_name}.png")).convert("RGBA"), 40)
                    self._moontick_photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._moontick_photo = None
            if self._moontick_photo:
                self._moontick_label.config(image=self._moontick_photo)
                self._moontick_label.grid(row=0, column=1, padx=(2, 0))
        else:
            self._moontick_label.grid_remove()

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

        # Moon tick icon for OBS — between kingdom icon (col 2) and counter (col 4)
        self._moontick_photo = None
        self._moontick_label = tk.Label(self, bg=bg_color)
        # not gridded yet; apply_moontick manages placement at col 3

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
        for widget in (self.lock_label, self.peace_label, self.kingdom_label, self.text, self._moontick_label):
            widget.config(bg=bg_color)

    def apply_moontick(self, enabled, asset_name=None):
        """Show or hide moontick icon between kingdom icon and counter in OBS row."""
        if enabled and asset_name:
            if self._moontick_photo is None:
                try:
                    img = resize_by_height(Image.open(resource_path(f"assets/{asset_name}.png")).convert("RGBA"), 40)
                    self._moontick_photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._moontick_photo = None
            if self._moontick_photo:
                self._moontick_label.config(image=self._moontick_photo)
                self._moontick_label.grid(row=0, column=3, padx=(2, 0))
        else:
            self._moontick_label.grid_remove()


class OBSSimpleCounterRow(tk.Frame):
    """OBS row for SimpleCounterRow (Cap / Star)."""
    def __init__(self, parent, source_row, bg_color, white_icons_ref=None):
        super().__init__(parent, bg=bg_color)
        self.source_row = source_row
        self.white_icons_ref = white_icons_ref

        self.icon = tk.Label(self, image=source_row.photo, bg=bg_color)
        self.icon.grid(row=0, column=0, padx=4)

        # Moon tick icon for OBS — between kingdom icon (col 0) and counter (col 2)
        self._moontick_photo = None
        self._moontick_label = tk.Label(self, bg=bg_color)
        # not gridded yet; apply_moontick manages placement at col 1

        self.label = tk.Label(self, text="0", fg=TEXT_COLOR, bg=bg_color, font=FONT_BIG)
        self.label.grid(row=0, column=2, padx=4)

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
        self._moontick_label.config(bg=bg)

    def apply_moontick(self, enabled, asset_name=None):
        """Show or hide moontick icon between kingdom icon and counter in OBS simple counter row."""
        if enabled and asset_name:
            if self._moontick_photo is None:
                try:
                    img = resize_by_height(Image.open(resource_path(f"assets/{asset_name}.png")).convert("RGBA"), 40)
                    self._moontick_photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._moontick_photo = None
            if self._moontick_photo:
                self._moontick_label.config(image=self._moontick_photo)
                self._moontick_label.grid(row=0, column=1, padx=(2, 0))
        else:
            self._moontick_label.grid_remove()


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

        # Moon tick icon — between icon (col 0) and counter (col 2)
        self._moontick_photo = None
        self._moontick_label = tk.Label(self, bg=bg_color)
        # not gridded yet; apply_moontick manages placement at col 1

        self.label = tk.Label(self, text="0", fg=TEXT_COLOR, bg=bg_color, font=FONT_BIG)
        self.label.grid(row=0, column=2, padx=4)

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
        self._moontick_label.config(bg=bg)

    def apply_moontick(self, enabled, asset_name=None):
        """Show or hide moontick icon between icon and counter in OBS sidebar ability row."""
        if enabled and asset_name:
            if self._moontick_photo is None:
                try:
                    img = resize_by_height(Image.open(resource_path(f"assets/{asset_name}.png")).convert("RGBA"), 40)
                    self._moontick_photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._moontick_photo = None
            if self._moontick_photo:
                self._moontick_label.config(image=self._moontick_photo)
                self._moontick_label.grid(row=0, column=1, padx=(2, 0))
        else:
            self._moontick_label.grid_remove()


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


class OBSPeaceLockRow(tk.Frame):
    """Mirrors a KingdomPeaceLockRow on the OBS overlay — polls state every 200 ms."""

    def __init__(self, parent, peace_lock_row, bg_color):
        super().__init__(parent, bg=bg_color)
        self.peace_lock_row = peace_lock_row
        self.bg_color = bg_color
        self._labels = []

        tokens = KINGDOM_PEACE_CAPTURES.get(peace_lock_row.kingdom_name, [])
        icon_idx = 0
        col = 0
        for token in tokens:
            if token == "/":
                lbl = tk.Label(self, text="/", bg=bg_color, fg=TEXT_COLOR,
                               font=("Fredoka", 14, "bold"))
                lbl.grid(row=0, column=col, padx=1)
                self._labels.append(("sep", lbl, None))
                col += 1
            elif token == "-":
                lbl = tk.Label(self, text="", bg=bg_color, width=2)
                lbl.grid(row=0, column=col)
                self._labels.append(("gap", lbl, None))
                col += 1
            else:
                # Grab matching source icon from the peace_lock_row
                if icon_idx < len(peace_lock_row._icons):
                    src = peace_lock_row._icons[icon_idx]
                    lbl = tk.Label(self, image=src._img_black, bg=bg_color)
                    lbl.grid(row=0, column=col, padx=2)
                    self._labels.append(("icon", lbl, src))
                    icon_idx += 1
                col += 1

        self.update()

    def update(self):
        for kind, lbl, src in self._labels:
            if kind == "icon" and src is not None:
                lbl.config(image=src._img_color if src.active else src._img_black)
        self.after(200, self.update)

    def set_bg(self, bg):
        self.bg_color = bg
        self.config(bg=bg)
        for kind, lbl, _ in self._labels:
            lbl.config(bg=bg)


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
                 icons_visible=True,
                 peace_lock_rows=None, peace_lock_visible=False,
                 timer_visible=False, timer_text="00:00"):
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
        self.peace_lock_rows_src = peace_lock_rows or []
        self.peace_lock_visible = peace_lock_visible

        # Reference back to app for totals
        self._app = parent

        self.main = tk.Frame(self, bg=self.bg_color)
        self.main.pack(fill="both", expand=True)

        self.moon_frame = tk.Frame(self.main, bg=self.bg_color)
        self.moon_frame.grid(row=0, column=0, padx=8, sticky="n")

        # Track the current grid row being used in moon_frame
        self._moon_frame_row_offset = 0

        # --- Cap row (above Cascade) ---
        self.cap_obs = None
        if self.cap_row and self.cap_enabled:
            self.cap_obs = OBSSimpleCounterRow(
                self.moon_frame, self.cap_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self.cap_obs.grid(row=self._moon_frame_row_offset, column=0, pady=2, padx=6, sticky="w")
            self._moon_frame_row_offset += 1

        # --- Standard kingdom moon rows + Peace Lock rows ---
        self.moon_obs_rows = []
        self.peace_obs_rows = []
        kingdom_names = list(KINGDOM_PEACE_CAPTURES.keys())
        for i, row in enumerate(moon_rows):
            grid_row = self._moon_frame_row_offset + i
            obs_row = OBSMoonRow(self.moon_frame, row, self.bg_color,
                                 white_icons_ref=self.white_icons_ref)
            obs_row.grid(row=grid_row, column=0, pady=2, padx=6, sticky="w")
            self.moon_obs_rows.append(obs_row)

            # Build peace lock row for this kingdom if it has captures — placed inline (same grid row, col 1)
            kname = kingdom_names[i] if i < len(kingdom_names) else ""
            tokens = KINGDOM_PEACE_CAPTURES.get(kname, [])
            if tokens and i < len(self.peace_lock_rows_src):
                p_row = OBSPeaceLockRow(self.moon_frame,
                                        self.peace_lock_rows_src[i],
                                        self.bg_color)
                if self.peace_lock_visible:
                    p_row.grid(row=grid_row, column=1, padx=(4, 6), sticky="w")
                self.peace_obs_rows.append((kname, p_row, grid_row))
            else:
                self.peace_obs_rows.append((kname, None, grid_row))

        self._moon_frame_row_offset += len(moon_rows)

        # --- Dark row (below Bowser) ---
        self.dark_obs = None
        self._dark_obs_grid_row = None
        if self.dark_row and self.dark_enabled:
            self.dark_obs = OBSMoonRow(
                self.moon_frame, self.dark_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self._dark_obs_grid_row = self._moon_frame_row_offset
            self.dark_obs.grid(row=self._moon_frame_row_offset, column=0, pady=2, padx=6, sticky="w")
            self._moon_frame_row_offset += 1

        # --- Star row (below Dark, or below Bowser if Dark hidden) ---
        self.star_obs = None
        self._star_obs_grid_row = None
        if self.star_row and self.star_enabled:
            self.star_obs = OBSSimpleCounterRow(
                self.moon_frame, self.star_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self._star_obs_grid_row = self._moon_frame_row_offset
            self.star_obs.grid(row=self._moon_frame_row_offset, column=0, pady=2, padx=6, sticky="w")
            self._moon_frame_row_offset += 1

        self.right = tk.Frame(self.main, bg=self.bg_color)
        self.right.grid(row=0, column=1, padx=12, sticky="n")

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

        self.moon_cave_header = SectionHeader(self.right, "Moon Cave")
        self.capture_col = OBSCaptureColumn(self.right, capture_row, self.bg_color)
        self.capture_col.pack(pady=(0, 20))

        self.cave_skip_header = SectionHeader(self.right, "Cave Skip")
        self.ability_col = OBSAbilityColumn(self.right, ability_row, self.bg_color)
        self.ability_col.pack(pady=(0, 20))

        self.bowser_row = OBSBowserRow(self.right, capture_row, self.bg_color)
        self.bowser_row.pack(pady=(0, 20))

        # --- Timer — shown below Cave Skip & Bowser; OBS only displays the time, no buttons ---
        self.timer_label_obs = tk.Label(
            self.right, text=timer_text, fg=TEXT_COLOR, bg=self.bg_color, font=FONT_BIG
        )
        if timer_visible:
            self.timer_label_obs.pack(pady=(0, 10))

        # Apply initial icons visibility
        if not self.icons_visible:
            self.moon_cave_header.pack_forget()
            self.capture_col.pack_forget()
            self.cave_skip_header.pack_forget()
            self.ability_col.pack_forget()
            self.bowser_row.pack_forget()

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
                self.cap_obs.grid(row=0, column=0, pady=2, padx=6, sticky="w")
            else:
                self.cap_obs.grid_remove()
                if not cap_enabled:
                    self.cap_obs.destroy()
                    self.cap_obs = None

        # Dark row (Moon Kingdom) — NEVER hidden by the optional toggle; only by dark_enabled
        if dark_enabled and self.dark_obs is None and self.dark_row:
            self.dark_obs = OBSMoonRow(
                self.moon_frame, self.dark_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self._dark_obs_grid_row = self._moon_frame_row_offset
            self._moon_frame_row_offset += 1
        if self.dark_obs:
            if dark_enabled:
                self.dark_obs.grid(row=self._dark_obs_grid_row, column=0, pady=2, padx=6, sticky="w")
            else:
                self.dark_obs.grid_remove()
                self.dark_obs.destroy()
                self.dark_obs = None

        # Star row (Capture) — hidden by the optional toggle
        if star_enabled and self.star_obs is None and self.star_row:
            self.star_obs = OBSSimpleCounterRow(
                self.moon_frame, self.star_row, self.bg_color,
                white_icons_ref=self.white_icons_ref
            )
            self._star_obs_grid_row = self._moon_frame_row_offset
            self._moon_frame_row_offset += 1
        if self.star_obs:
            if star_enabled and not hidden:
                self.star_obs.grid(row=self._star_obs_grid_row, column=0, pady=2, padx=6, sticky="w")
            else:
                self.star_obs.grid_remove()
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
                self.cap_obs.grid(row=0, column=0, pady=2, padx=6, sticky="w")
            # NOTE: dark_obs (Moon Kingdom) is NOT touched here
            if self.star_obs and self._star_obs_grid_row is not None:
                self.star_obs.grid(row=self._star_obs_grid_row, column=0, pady=2, padx=6, sticky="w")
        else:
            for w in (self.cap_obs, self.star_obs):
                if w:
                    w.grid_remove()
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
        else:
            self.moon_cave_header.pack_forget()
            self.capture_col.pack_forget()
            self.cave_skip_header.pack_forget()
            self.ability_col.pack_forget()
            self.bowser_row.pack_forget()

    def set_timer_visible(self, visible):
        """Show or hide the Timer label in OBS (below Cave Skip & Bowser)."""
        if visible:
            self.timer_label_obs.pack(pady=(0, 10))
        else:
            self.timer_label_obs.pack_forget()

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

    def set_peace_lock_visible(self, visible):
        """Show or hide the peace lock rows in OBS — inline next to each kingdom row."""
        self.peace_lock_visible = visible
        for entry in self.peace_obs_rows:
            kname, p_row, grid_row = entry
            if p_row is None:
                continue
            tokens = KINGDOM_PEACE_CAPTURES.get(kname, [])
            if tokens:
                if visible:
                    p_row.grid(row=grid_row, column=1, padx=(4, 6), sticky="w")
                else:
                    p_row.grid_remove()

    def set_lock_peace_visible(self, visible):
        """Show or hide lock/peace labels in all OBS moon rows."""
        for obs_row in self.moon_obs_rows:
            if visible:
                obs_row.lock_label.grid()
                obs_row.peace_label.grid()
            else:
                obs_row.lock_label.grid_remove()
                obs_row.peace_label.grid_remove()
        # Also dark_obs if present
        if self.dark_obs:
            if visible:
                self.dark_obs.lock_label.grid()
                self.dark_obs.peace_label.grid()
            else:
                self.dark_obs.lock_label.grid_remove()
                self.dark_obs.peace_label.grid_remove()

    def set_moontick_visible(self, visible, kingdom_moontick_map):
        """Show or hide moontick icons in all OBS moon rows and special counter rows.
        kingdom_moontick_map: dict from kingdom_name -> asset_name (e.g. 'moontickCascade')"""
        kingdom_names = list(KINGDOM_PEACE_CAPTURES.keys())
        for i, obs_row in enumerate(self.moon_obs_rows):
            kname = kingdom_names[i] if i < len(kingdom_names) else ""
            asset = kingdom_moontick_map.get(kname)
            obs_row.apply_moontick(visible, asset)
        # dark_obs (Moon Kingdom)
        if self.dark_obs:
            asset = kingdom_moontick_map.get("Moon Kingdom")
            self.dark_obs.apply_moontick(visible, asset)
        # cap_obs
        if self.cap_obs:
            asset = kingdom_moontick_map.get("Cap")
            self.cap_obs.apply_moontick(visible, asset)
        # star_obs
        if self.star_obs:
            asset = kingdom_moontick_map.get("Star")
            self.star_obs.apply_moontick(visible, asset)
        # obs_cloud_row
        if self.obs_cloud_row:
            asset = kingdom_moontick_map.get("Cloud")
            self.obs_cloud_row.apply_moontick(visible, asset)
        # obs_sidebar_cap
        if self.obs_sidebar_cap:
            asset = kingdom_moontick_map.get("Cap")
            self.obs_sidebar_cap.apply_moontick(visible, asset)
        # obs_sidebar_star
        if self.obs_sidebar_star:
            asset = kingdom_moontick_map.get("Star")
            self.obs_sidebar_star.apply_moontick(visible, asset)
        # obs_sidebar_ability (Dark Side)
        if self.obs_sidebar_ability:
            asset = kingdom_moontick_map.get("Dark Side")
            self.obs_sidebar_ability.apply_moontick(visible, asset)


    def set_moon_total_visible(self, visible):
        """Show or hide the Moons total section on the OBS right sidebar."""
        if visible:
            self.moon_total_header.pack(fill="x", padx=8, pady=(10, 4))
            self.moon_total_label.pack(pady=(0, 10))
        else:
            self.moon_total_header.pack_forget()
            self.moon_total_label.pack_forget()

    def toggle_bg(self):
        if self.bg_mode == "dark":
            self.bg_mode = "green"
            self.bg_color = "#00FF00"
        else:
            self.bg_mode = "dark"
            self.bg_color = "#181818"

        self._apply_bg(self.bg_color)

    def set_bg_color(self, color):
        """Set the OBS window background to any hex colour string."""
        self.bg_mode = "custom"
        self.bg_color = color
        self._apply_bg(color)

    def _apply_bg(self, color):
        """Apply *color* to every widget in the OBS window."""
        self.config(bg=color)

        for row in self.moon_obs_rows:
            row.set_bg(color)
        if self.cap_obs:
            self.cap_obs.set_bg(color)
        if self.star_obs:
            self.star_obs.set_bg(color)
        if self.dark_obs:
            self.dark_obs.set_bg(color)
        self.capture_col.set_bg(color)
        self.ability_col.set_bg(color)
        self.bowser_row.set_bg(color)
        self.main.config(bg=color)
        self.moon_frame.config(bg=color)
        self.right.config(bg=color)
        self.moon_cave_header.set_bg(color)
        self.cave_skip_header.set_bg(color)
        self.moon_total_header.set_bg(color)
        self.moon_total_label.config(bg=color)
        if self.obs_cloud_row:
            self.obs_cloud_row.set_bg(color)
        if self.obs_sidebar_cap:
            self.obs_sidebar_cap.set_bg(color)
        if self.obs_sidebar_star:
            self.obs_sidebar_star.set_bg(color)
        if self.obs_sidebar_ability:
            self.obs_sidebar_ability.set_bg(color)
        for entry in self.peace_obs_rows:
            _, p_row, _ = entry
            if p_row is not None:
                p_row.set_bg(color)



# -------------------------
# Settings Window
# -------------------------
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.title("Settings")
        self.resizable(True, True)
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

        def _on_inner_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Auto-resize window to fit content (up to screen height)
            req_h = inner.winfo_reqheight() + 40
            req_w = inner.winfo_reqwidth() + 20
            screen_h = self.winfo_screenheight() - 60
            screen_w = self.winfo_screenwidth() - 40
            self.geometry(f"{min(req_w, screen_w)}x{min(req_h, screen_h)}")

        inner.bind("<Configure>", _on_inner_configure)

        # Title
        tk.Label(inner, text="Settings", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=FONT_BIG).pack(pady=(16, 12))

        # Outer columns container
        cols_frame = tk.Frame(inner, bg=BG_COLOR)
        cols_frame.pack(fill="both", expand=True, padx=12, pady=(0, 16))

        BTN_HEIGHT = 36
        btn_opts = dict(fg_color=TOOLBAR_BG, hover_color="#1a5fc8",
                        corner_radius=10, border_width=0, cursor="hand2",
                        font=FONT_NORMAL)

        AQUA   = "#2ab8b8"
        AQUA_H = "#1e9090"

        def col_header(parent, text):
            tk.Label(parent, text=text, bg=BG_COLOR, fg=TEXT_COLOR,
                     font=("Fredoka", 13, "bold")).pack(fill="x", pady=(0, 6))

        def make_btn(parent, text, command, fg="#1f6feb", hover="#1a5fc8",
                     text_color="#ffffff", height=BTN_HEIGHT, image=None):
            kw = dict(text=text, command=command, height=height,
                      fg_color=fg, hover_color=hover, text_color=text_color,
                      corner_radius=10, cursor="hand2", font=FONT_NORMAL)
            if image is not None:
                kw["image"] = image
                kw["anchor"] = "w"
                kw["compound"] = "left"
            return ctk.CTkButton(parent, **kw)

        # ── COLUMN 1: Customization (LEFT SIDE) ─────────────────────────
        col1 = tk.Frame(cols_frame, bg=BG_COLOR)
        col1.grid(row=0, column=0, sticky="n", padx=(0, 10))
        col_header(col1, "Customization")

        # Buttons that are referenced later (in refresh_* methods) default to
        # None so those methods can safely no-op when SETTINGS_BUTTONS hides them.
        self.moon_tracker_btn = None
        self.white_icon_btn = None
        self.moon_tick_btn = None
        self.lock_peace_btn = None
        self._col1_btns = []   # track left-col buttons for height equalization

        if SETTINGS_BUTTONS["total_moon_tracker"]:
            self._moon_tracker_text = tk.StringVar(value="Total Moon Tracker")
            self.moon_tracker_btn = ctk.CTkButton(
                col1,
                image=app.tb_moon_dark_photo,
                textvariable=self._moon_tracker_text,
                command=app.toggle_total_moon_tracker,
                height=BTN_HEIGHT,
                anchor="w", compound="left",
                **btn_opts
            )
            self.moon_tracker_btn.pack(fill="x", pady=3)
            self._col1_btns.append(self.moon_tracker_btn)
        else:
            self._moon_tracker_text = tk.StringVar(value="Total Moon Tracker")

        if SETTINGS_BUTTONS["white_kingdom_icons"]:
            current_white_icon = app.metro_color_photo if app.white_icons else app.metro_white_photo
            self.white_icon_btn = ctk.CTkButton(
                col1, image=current_white_icon, text="  White Kingdom Icons",
                command=app.toggle_white_icons, height=BTN_HEIGHT,
                anchor="w", compound="left", **btn_opts
            )
            self.white_icon_btn.pack(fill="x", pady=3)
            self._col1_btns.append(self.white_icon_btn)

        # Moon Counter Icons — shown below White Kingdom Icons
        if SETTINGS_BUTTONS["moon_counter_icons"]:
            self._moon_tick_text = tk.StringVar(value="Moon Counter Icons")
            self.moon_tick_btn = ctk.CTkButton(
                col1,
                image=app.tb_moontick_cap_photo,
                textvariable=self._moon_tick_text,
                command=app.toggle_moon_tick,
                height=BTN_HEIGHT,
                anchor="w", compound="left",
                fg_color=TOOLBAR_BG, hover_color="#1a5fc8", text_color="#ffffff",
                corner_radius=10, cursor="hand2", font=FONT_NORMAL
            )
            self.moon_tick_btn.pack(fill="x", pady=3)
            self._col1_btns.append(self.moon_tick_btn)
        else:
            self._moon_tick_text = tk.StringVar(value="Moon Counter Icons")

        if SETTINGS_BUTTONS["lock_peace_icons"]:
            lp_icon = app.tb_lock_photo if app.lock_peace_hidden else app.tb_unlock_photo
            self.lock_peace_btn = ctk.CTkButton(
                col1, image=lp_icon, text="  Lock & Peace Icons",
                command=app.toggle_lock_peace, height=BTN_HEIGHT,
                anchor="w", compound="left", **btn_opts
            )
            self.lock_peace_btn.pack(fill="x", pady=3)
            self._col1_btns.append(self.lock_peace_btn)

        if SETTINGS_BUTTONS["cap_moon_tracker"]:
            b = make_btn(col1, "Cap Moon Tracker", app.toggle_cap_row,
                         image=app.tb_cap_photo)
            b.pack(fill="x", pady=3)
            self._col1_btns.append(b)
        if SETTINGS_BUTTONS["cloud_moon_tracker"]:
            b = make_btn(col1, "Cloud Moon Tracker", app.toggle_cloud_row,
                         image=app.tb_cloud_photo)
            b.pack(fill="x", pady=3)
            self._col1_btns.append(b)
        if SETTINGS_BUTTONS["moon_kingdom_tracker"]:
            b = make_btn(col1, "Moon Kingdom Tracker", app.toggle_dark_row,
                         image=app.tb_dark_photo)
            b.pack(fill="x", pady=3)
            self._col1_btns.append(b)
        if SETTINGS_BUTTONS["timer"]:
            b = make_btn(col1, "  Toggle Timer", app.toggle_timer,
                         image=app.tb_clock_photo)
            b.pack(fill="x", pady=3)
            self._col1_btns.append(b)

        # Add Milliseconds to Timer — appears/disappears alongside Toggle Timer (Settings only)
        if SETTINGS_BUTTONS.get("timer_ms", 1) and SETTINGS_BUTTONS["timer"]:
            self._timer_ms_btn = ctk.CTkButton(
                col1,
                text="  Add Milliseconds to Timer",
                command=app.toggle_timer_ms,
                height=BTN_HEIGHT,
                fg_color="#4a2080", hover_color="#331560", text_color="#ffffff",
                corner_radius=10, cursor="hand2", font=FONT_NORMAL
            )
            self._timer_ms_btn.pack(fill="x", pady=3)
            self._col1_btns.append(self._timer_ms_btn)
            # Only show if timer is currently visible
            if not app.timer_visible:
                self._timer_ms_btn.pack_forget()
                self._col1_btns.remove(self._timer_ms_btn)
        else:
            self._timer_ms_btn = None

        # ── COLUMN 2: Clear + OBS (MIDDLE — no height matching) ────────
        col2 = tk.Frame(cols_frame, bg=BG_COLOR)
        col2.grid(row=0, column=1, sticky="n", padx=10)
        col_header(col2, "Clear")

        def confirm_clear_tracker():
            popup = tk.Toplevel(self)
            popup.title("Confirm")
            popup.configure(bg=BG_COLOR)
            popup.geometry("320x130")
            popup.update_idletasks()
            popup.wait_visibility()
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
            popup.update_idletasks()
            popup.wait_visibility()
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

        def confirm_reset():
            popup = tk.Toplevel(self)
            popup.title("Confirm RESET")
            popup.configure(bg=BG_COLOR)
            popup.geometry("340x140")
            popup.update_idletasks()
            popup.wait_visibility()
            popup.grab_set()
            tk.Label(popup,
                     text="Are you sure you want to RESET everything?\nThis will clear the Tracker, Notes, and all Settings.",
                     bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_NORMAL,
                     wraplength=300, justify="center").pack(pady=(18, 10))
            btn_row = tk.Frame(popup, bg=BG_COLOR)
            btn_row.pack()
            def do_reset():
                popup.destroy()
                app._clear_notes()
                app.reset_all_moons()
                app._reset_all_settings()
            ctk.CTkButton(btn_row, text="Yes", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#cc0000", hover_color="#aa0000", width=100,
                          command=do_reset).pack(side="left", padx=8)
            ctk.CTkButton(btn_row, text="No", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#444444", hover_color="#222222", width=100,
                          command=popup.destroy).pack(side="left", padx=8)

        # Clear Tracker — pinkish-red with white text
        PINK_RED  = "#e05070"
        PINK_RED_H = "#c03050"
        if SETTINGS_BUTTONS["clear_tracker"]:
            b = make_btn(col2, "Clear Tracker", confirm_clear_tracker,
                         fg=PINK_RED, hover=PINK_RED_H, text_color="#ffffff")
            b.pack(fill="x", pady=3)
        if SETTINGS_BUTTONS["clear_notes"]:
            b = make_btn(col2, "Clear Notes", confirm_clear_notes,
                         fg=PINK_RED, hover=PINK_RED_H, text_color="#ffffff")
            b.pack(fill="x", pady=3)
        if SETTINGS_BUTTONS["reset"]:
            b = make_btn(col2, "RESET", confirm_reset,
                         fg="#aa0000", hover="#880000")
            b.pack(fill="x", pady=3)

        # ── OBS sub-header (below RESET in col2) ────────────────────────
        tk.Label(col2, text="OBS", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 13, "bold")).pack(fill="x", pady=(10, 6))

        # Open OBS button
        if SETTINGS_BUTTONS["open_obs"]:
            b = make_btn(col2, "Open OBS", app.open_obs,
                         fg="#cc0000", hover="#aa0000")
            b.pack(fill="x", pady=3)

        # Toggle Optional Kingdoms in OBS — clickable only when Cap, Cloud, Star OR Dark Side is visible
        self._obs_optional_btn = None
        if SETTINGS_BUTTONS["optional_kingdoms_obs"]:
            self._obs_optional_text = tk.StringVar(value="Toggle Optional Kingdoms in OBS")
            self._obs_optional_btn = ctk.CTkButton(
                col2,
                textvariable=self._obs_optional_text,
                command=app.toggle_obs_optional,
                height=BTN_HEIGHT,
                fg_color="#4a2080", hover_color="#331560", text_color="#ffffff",
                corner_radius=10, cursor="hand2", font=FONT_NORMAL
            )
            self._obs_optional_btn.pack(fill="x", pady=3)
            # Store a dummy _obs_optional_frame reference for compat
            self._obs_optional_frame = self._obs_optional_btn
            # Apply initial enabled/disabled state
            self._update_obs_optional_frame_visibility()
        else:
            self._obs_optional_text = tk.StringVar(value="Toggle Optional Kingdoms in OBS")
            self._obs_optional_frame = None

        # ── COLUMN 3: Ability Lock + Miscellaneous (RIGHT SIDE — height-matched with col1) ──
        col3 = tk.Frame(cols_frame, bg=BG_COLOR)
        col3.grid(row=0, column=2, sticky="n", padx=(10, 0))
        self._col3_btns = []   # track right-col buttons for height equalization
        col_header(col3, "Ability Lock")

        self.hide_ability_btn = None
        self._star_btn = None
        self._darkside_btn = None
        self._peace_lock_btn = None
        self._peace_lock_obs_btn = None

        if SETTINGS_BUTTONS["global_ability_lock"]:
            self.hide_ability_btn = ctk.CTkButton(
                col3,
                textvariable=app._hide_ability_text,
                command=app.toggle_capture_icons,
                height=BTN_HEIGHT,
                fg_color=AQUA, hover_color=AQUA_H, text_color="#ffffff",
                corner_radius=10, cursor="hand2", font=FONT_NORMAL
            )
            self.hide_ability_btn.pack(fill="x", pady=3)
            self._col3_btns.append(self.hide_ability_btn)

        # Star and Dark Side — greyed/disabled by Toggle Global Ability Lock
        self._ability_pair_frame = tk.Frame(col3, bg=BG_COLOR)
        self._ability_pair_frame.pack(fill="x", pady=3)

        if SETTINGS_BUTTONS["star"]:
            self._star_btn = make_btn(self._ability_pair_frame, "  Star",
                                      app.toggle_sidebar_captures_row,
                                      fg=AQUA, hover=AQUA_H,
                                      image=app.tb_captures_photo)
            self._star_btn.pack(pady=3, anchor="center")
            self._col3_btns.append(self._star_btn)
        if SETTINGS_BUTTONS["dark_side"]:
            self._darkside_btn = make_btn(self._ability_pair_frame, "  Dark Side",
                                          app.toggle_sidebar_ability_row,
                                          fg=AQUA, hover=AQUA_H,
                                          image=app.tb_ability_photo)
            self._darkside_btn.pack(pady=3, anchor="center")
            self._col3_btns.append(self._darkside_btn)

        # Toggle Peace Ability Lock
        self._peace_lock_text = tk.StringVar(value="Toggle Peace Ability Lock")

        def toggle_peace_lock_with_popup():
            # Show the info popup only when unhiding (peace currently hidden → about to show)
            if not app.peace_lock_visible:
                popup = tk.Toplevel(self)
                popup.title("Peace Ability Lock")
                popup.configure(bg=BG_COLOR)
                popup.geometry("460x190")
                popup.update_idletasks()
                popup.wait_visibility()
                popup.grab_set()
                tk.Label(
                    popup,
                    text="Keep in mind this only shows the Dev Intended solutions.\n"
                         "This game has very in-depth movement and has many\n"
                         "combinations to beat certain areas.",
                    bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_NORMAL,
                    wraplength=420, justify="center"
                ).pack(pady=(18, 10))
                ctk.CTkButton(
                    popup, text="Got it", font=FONT_NORMAL, corner_radius=10,
                    fg_color=AQUA, hover_color=AQUA_H, width=100,
                    command=lambda: [popup.destroy(), app.toggle_peace_lock()]
                ).pack()
            else:
                app.toggle_peace_lock()

        if SETTINGS_BUTTONS["peace_ability_lock"]:
            self._peace_lock_btn = ctk.CTkButton(
                col3,
                textvariable=self._peace_lock_text,
                command=toggle_peace_lock_with_popup,
                height=BTN_HEIGHT,
                fg_color=AQUA, hover_color=AQUA_H, text_color="#ffffff",
                corner_radius=10, cursor="hand2", font=FONT_NORMAL
            )
            self._peace_lock_btn.pack(fill="x", pady=3)
            self._col3_btns.append(self._peace_lock_btn)

        # Toggle Peace Lock in OBS
        self._peace_lock_obs_text = tk.StringVar(value="Toggle Peace Lock in OBS")
        if SETTINGS_BUTTONS["peace_lock_obs"]:
            self._peace_lock_obs_btn = ctk.CTkButton(
                col3,
                textvariable=self._peace_lock_obs_text,
                command=app.toggle_peace_lock_obs,
                height=BTN_HEIGHT,
                fg_color="#4a2080", hover_color="#331560", text_color="#ffffff",
                corner_radius=10, cursor="hand2", font=FONT_NORMAL
            )
            self._peace_lock_obs_btn.pack(fill="x", pady=3)
            self._col3_btns.append(self._peace_lock_obs_btn)
            self._update_peace_lock_obs_btn_state()

        # Apply initial visibility based on icons_visible state
        self._apply_ability_lock_visibility(app.icons_visible)

        # ── Miscellaneous (below Ability Lock in col3) ───────────────────
        tk.Label(col3, text="Miscellaneous", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 13, "bold")).pack(fill="x", pady=(10, 6))

        if SETTINGS_BUTTONS["load_spoiler_log"]:
            b = make_btn(col3, "📂  Load Spoiler Log",
                         lambda: load_spoiler_log_file(app),
                         fg="#1a6040", hover="#145030")
            b.pack(fill="x", pady=3)
            self._col3_btns.append(b)

        self._compact_view_text = tk.StringVar(
            value="Disable Compact View" if app.compact_view else "Compact View"
        )
        if SETTINGS_BUTTONS["compact_view"]:
            b = ctk.CTkButton(
                col3,
                textvariable=self._compact_view_text,
                command=app.toggle_compact_view,
                height=BTN_HEIGHT,
                fg_color="#5a3080", hover_color="#3d2060", text_color="#ffffff",
                corner_radius=10, cursor="hand2",
                font=FONT_NORMAL
            )
            b.pack(fill="x", pady=3)
            self._col3_btns.append(b)

        # ── Auto-equalize LEFT (col1/Customization) vs RIGHT (col3/Ability Lock+Misc) ──
        # The middle column (col2/Clear+OBS) is left untouched.
        def _equalize_columns():
            inner.update_idletasks()
            h1 = col1.winfo_reqheight()
            h3 = col3.winfo_reqheight()
            if h1 <= 0 or h3 <= 0 or not self._col1_btns or not self._col3_btns:
                return
            if h1 > h3:
                # Right side is shorter — enlarge its buttons
                n = len(self._col3_btns)
                extra = h1 - h3
                bonus = extra // n
                remainder = extra - bonus * n
                for i, btn in enumerate(self._col3_btns):
                    try:
                        cur = btn.cget("height")
                        add = bonus + (1 if i < remainder else 0)
                        btn.configure(height=cur + add)
                    except Exception:
                        pass
            elif h3 > h1:
                # Left side is shorter — enlarge its buttons
                n = len(self._col1_btns)
                extra = h3 - h1
                bonus = extra // n
                remainder = extra - bonus * n
                for i, btn in enumerate(self._col1_btns):
                    try:
                        cur = btn.cget("height")
                        add = bonus + (1 if i < remainder else 0)
                        btn.configure(height=cur + add)
                    except Exception:
                        pass

        inner.after(100, _equalize_columns)

    def refresh_moon_tracker_btn(self):
        """Total Moon Tracker button label is static now; kept for compatibility."""
        self._moon_tracker_text.set("Total Moon Tracker")

    def refresh_moon_tick_btn(self):
        """Moon Counter Icons button label is static now; kept for compatibility."""
        self._moon_tick_text.set("Moon Counter Icons")

    def refresh_lock_peace_btn(self):
        """Swap lock/unlock icon on the Lock & Peace Icons button to reflect current state."""
        if self.lock_peace_btn is None:
            return
        icon = self.app.tb_lock_photo if self.app.lock_peace_hidden else self.app.tb_unlock_photo
        self.lock_peace_btn.configure(image=icon)

    def refresh_obs_optional_btn(self):
        """Called when any optional row is toggled to update label and enabled state."""
        self._obs_optional_text.set("Toggle Optional Kingdoms in OBS")
        self._update_obs_optional_frame_visibility()

    def _update_obs_optional_frame_visibility(self):
        """Grey-out the Toggle Optional Kingdoms in OBS button when none of the 4 optional rows
        is enabled: Cap, Cloud, Star (Capture Count), or Dark Side (Movement Ability)."""
        if self._obs_optional_btn is None:
            return
        any_optional = (
            self.app.sidebar_cap_visible
            or self.app.cloud_enabled
            or self.app.sidebar_captures_visible
            or self.app.sidebar_ability_visible
        )
        if any_optional:
            self._obs_optional_btn.configure(state="normal",
                                             fg_color="#4a2080", hover_color="#331560")
        else:
            self._obs_optional_btn.configure(state="disabled",
                                             fg_color="#2a1040", hover_color="#2a1040")

    def refresh_white_icon_button(self):
        """Called by toggle_white_icons to flip the button icon.
        When main view shows colored icons (white_icons=False): button shows white Metro icon.
        When main view shows white icons (white_icons=True): button shows colored Metro icon."""
        if self.white_icon_btn is None:
            return
        if self.app.white_icons:
            # Main view is white → button shows colored icon (clicking will revert to colored)
            self.white_icon_btn.configure(image=self.app.metro_color_photo)
        else:
            # Main view is colored → button shows white icon (clicking will switch to white)
            self.white_icon_btn.configure(image=self.app.metro_white_photo)

    def _apply_ability_lock_visibility(self, visible):
        """Grey-out or enable the Star/Dark Side buttons based on icons_visible state."""
        AQUA     = "#2ab8b8"
        AQUA_DIM = "#1a6060"
        if visible:
            if self._star_btn is not None:
                self._star_btn.configure(state="normal",
                                         fg_color=AQUA, hover_color=AQUA_DIM)
            if self._darkside_btn is not None:
                self._darkside_btn.configure(state="normal",
                                             fg_color=AQUA, hover_color=AQUA_DIM)
        else:
            if self._star_btn is not None:
                self._star_btn.configure(state="disabled",
                                         fg_color="#1a5050", hover_color="#1a5050")
            if self._darkside_btn is not None:
                self._darkside_btn.configure(state="disabled",
                                             fg_color="#1a5050", hover_color="#1a5050")

    def refresh_peace_lock_btn(self):
        """Update the Toggle Peace Ability Lock button label."""
        self._peace_lock_text.set("Toggle Peace Ability Lock")
        self._update_peace_lock_obs_btn_state()

    def refresh_peace_lock_obs_btn(self):
        """Update the Toggle Peace Lock in OBS button label."""
        self._peace_lock_obs_text.set("Toggle Peace Lock in OBS")
        self._update_peace_lock_obs_btn_state()

    def _update_peace_lock_obs_btn_state(self):
        """Grey-out Toggle Peace Lock in OBS button when Peace Ability Lock is hidden."""
        if self._peace_lock_obs_btn is None:
            return
        if self.app.peace_lock_visible:
            self._peace_lock_obs_btn.configure(
                state="normal", fg_color="#4a2080", hover_color="#331560"
            )
        else:
            self._peace_lock_obs_btn.configure(
                state="disabled", fg_color="#2a1040", hover_color="#2a1040"
            )

    def refresh_compact_view_btn(self):
        """Update Compact View button label."""
        self._compact_view_text.set(
            "Disable Compact View" if self.app.compact_view else "Compact View"
        )

    def apply_compact_buttons(self, compact_on):
        """Grey-out Toggle Peace Ability Lock button when Compact View is enabled."""
        AQUA   = "#2ab8b8"
        AQUA_H = "#1e9090"
        if self._peace_lock_btn is None:
            return
        if compact_on:
            self._peace_lock_btn.configure(state="disabled",
                                           fg_color="#1a5050", hover_color="#1a5050")
        else:
            self._peace_lock_btn.configure(state="normal",
                                           fg_color=AQUA, hover_color=AQUA_H)

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
                # Optional manual ordering: a leading "N. " on the moon name means
                # "put this moon at position N within its kingdom". The number is
                # recorded for sorting and stripped so it is never displayed.
                manual_order = None
                order_match = re.match(r"^(\d+)\.\s+(.*)$", moon_name)
                if order_match:
                    manual_order = int(order_match.group(1))
                    moon_name = order_match.group(2).strip()
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
                        "order": manual_order,
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

                # Pull out the bare entrance id by stripping the leading kingdom-name
                # prefix (it always repeats the current section's kingdom header).
                from_id = from_exit
                if current_kingdom and from_exit.startswith(current_kingdom):
                    from_id = from_exit[len(current_kingdom):].strip()

                # Split "Dest Kingdom: StageName (exit_id)" into its parts so the
                # destination id can be looked up against the room-name database too.
                to_kingdom, to_stage_name, to_id = "", dest_stage, ""
                if ": " in dest_stage:
                    to_kingdom, to_stage_name = dest_stage.split(": ", 1)
                    to_kingdom = to_kingdom.strip()
                    to_stage_name = to_stage_name.strip()
                id_match = re.search(r"\(([^)]+)\)\s*$", to_stage_name)
                if id_match:
                    to_id = id_match.group(1).strip()
                    to_stage_name = to_stage_name[:id_match.start()].strip()

                if current_kingdom:
                    data["entrances"][current_kingdom].append({
                        "from": from_exit,
                        "to": dest_stage,
                        "from_kingdom": current_kingdom,
                        "from_id": from_id,
                        "to_kingdom": to_kingdom,
                        "to_stage": to_stage_name,
                        "to_id": to_id,
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

    # Apply any manual "N. " ordering hints within each kingdom's moon list.
    for kingdom in data["moons"]:
        data["moons"][kingdom] = _apply_manual_order(data["moons"][kingdom])

    return data


def _apply_manual_order(entries):
    """Reorder a kingdom's moon entries honouring manual "order" hints.

    An entry whose ``order`` is N is placed at 1-based slot N (0-based N-1).
    Entries without an order keep their original relative order and fill the
    remaining slots. Out-of-range or colliding numbers fall through to the next
    free slot so nothing is ever dropped."""
    n = len(entries)
    if n == 0:
        return entries

    result = [None] * n
    numbered = sorted((e for e in entries if e.get("order") is not None),
                      key=lambda e: e["order"])
    others = [e for e in entries if e.get("order") is None]

    for e in numbered:
        pos = max(0, e["order"] - 1)
        if pos >= n:
            pos = n - 1
        # Walk forward to the next free slot; wrap to the first free slot if the
        # tail is already full.
        while pos < n and result[pos] is not None:
            pos += 1
        if pos >= n:
            pos = result.index(None)
        result[pos] = e

    fillers = iter(others)
    for i in range(n):
        if result[i] is None:
            result[i] = next(fillers)

    return result

# -------------------------
# Room-name database (used to translate the raw entrance/exit ids that show
# up in the Entrance Randomizer section into the human-readable room names
# players actually recognise).
# -------------------------

ROOM_DATABASE_TEXT = r"""
# =========================================================
# Cap Kingdom
# =========================================================
"Orange": "Yellow Subarea with Pylons Room (in Cap Kingdom)",  # PushBlockEx (ID: PushBlockExStageEnt)
"Paragoomba": "Paragoomba Poison Wave Shards Room (in Cap Kingdom)",  # PoisonWaveEx (ID: PoisonWaveExEnt)
"Frog": "Frog Shards Subarea Room (in Cap Kingdom)",  # FrogSearchEx (ID: FrogSearchExStageEnt)
"Rolling On": "Rolling Spinies Moon Pipe Subarea Room (in Cap Kingdom)",  # RollingEx (ID: rollingstart)

# =========================================================
# Cascade Kingdom
# =========================================================
"Dino": "T-Rex Coin Duping Room (in Cascade Kingdom)",  # TrexPoppunEx (ID: RexPoppunEx)
"2D": "2D Moving Platforms Subarea Room (in Cascade Kingdom)",  # Lift2DEx (ID: Lift2D)
"Chain Chomp": "Chain Chomp Aim Subarea Room (in Cascade Kingdom)",  # WanwanClashEx (ID: WanwanExStart)
"Swings": "Wind Moon Pipe Subarea Room (in Cascade Kingdom)",  # WindBlowEx (ID: WindBlowExStart)
"Windy": "Cloud Platforms & Swinging Platforms Room (in Cascade Kingdom)",  # CapAppearEx (ID: CapAppearExEnt)

# =========================================================
# Sand Kingdom
# =========================================================
"Icy Cave": "Underground Quicksand Room (in Sand Kingdom)",  # SandWorldPressEx (ID: arijigoku)
"Moe-eye": "Invisible Maze Subarea Room (in Sand Kingdom)",  # SandWorldMeganeEx (ID: wall)
"Moving Platform": "Transparent Lifts Moon Rock Pipe Subarea Room (in Sand Kingdom)",  # MeganeLiftEx (ID: meganelift01)
"Shop (Employees Only)": "Employee's Only (in Sand Kingdom)",  # SandWorldShop (ID: bar2)
"Shop": "Crazy Cap Shop Room (in Sand Kingdom)",  # SandWorldShop (ID: bar1)
"Skull Sign": "UNDETERMINED ROOM (in Sand Kingdom)",  # SandWorldMeganeEx (ID: anki2)
"Slots": "Slots Room (in Sand Kingdom)",  # SandWorldSlot (ID: town)
"Rumble": "Rumble Room (in Sand Kingdom)",  # SandWorldVibration (ID: shindo)
"Outfit": "Costume Room (in Sand Kingdom)",  # SandWorldCostume (ID: abc)
"Jaxi Ruins": "Jaxi Ruins Subarea Room (in Sand Kingdom)",  # SandWorldSphinxEx (ID: aaa/run00)
"Bullet Bill": "Bullet Bill Maze Room (in Sand Kingdom)",  # SandWorldKillerEx (ID: doukutu1)
"Gushen": "Gushen Moon Pipe Subarea Room (in Sand Kingdom)",  # WaterTubeEx (ID: EX_2DHosui)
"Sphynx": "Sphynx Room (in Sand Kingdom)",  # SandWorldSecret (ID: hide)
"Rocket": "Rocket Subarea Room (in Sand Kingdom)",  # SandWorldRotate (ID: biru)
"Colossal Ruins": "Rocket Flower Moon Pipe Subarea Room (in Sand Kingdom)",  # RocketFlowerEx (ID: rocket)
"Icy Cave (Alt Entrance)": "Underground Quicksand Room (in Sand Kingdom)",  # SandWorldPressEx (ID: arijigoku1)

# =========================================================
# Lake Kingdom
# =========================================================
"Poison Waves": "Poison Wave with Frogs Room (in Lake Kingdom)",  # FrogPoisonEx (ID: LakeWorldMoonEX1a)
"Zipper": "Zipper Subarea Room (in Lake Kingdom)",  # FastenerEx (ID: FastenerEx)
"Grab Climb": "Flower Trampoline Subarea Room (in Lake Kingdom)",  # TrampolineWallCatchEx (ID: CapTrampolineA)
"Shop": "Crazy Cap Shop Room (in Lake Kingdom)",  # LakeWorldShop (ID: LakeWorldShop)
"Puzzle": "Puzzle Piece Subarea Room (in Lake Kingdom)",  # GotogotonEx (ID: Goton)

# =========================================================
# Wooded Kingdom
# =========================================================
"DW Odyssey": "Deep Woods Room (in Wooded Kingdom)",  # ForestWorldWoods (ID: Jyukai003v)
"DW Red Maze": "Deep Woods Room (in Wooded Kingdom)",  # ForestWorldWoods (ID: Jyukai004)
"DW Pond": "Deep Woods Room (in Wooded Kingdom)",  # ForestWorldWoods (ID: Jyukai002)
"DW Treasure": "Deep Woods Treasure Pipe Room (in Wooded Kingdom)",  # ForestWorldWoodsTreasure
"DW Outfit": "Deep Woods Costume Room (in Wooded Kingdom)",  # ForestWorldWoodsCostume
"DW Section 001": "Deep Woods Room (in Wooded Kingdom)",  # ForestWorldWoods (ID: Jyukai001)
"DW Section 001v": "Deep Woods Room (in Wooded Kingdom)",  # ForestWorldWoods (ID: Jyukai001v)
"DW Section 003": "Deep Woods Room (in Wooded Kingdom)",  # ForestWorldWoods (ID: Jyukai003)
"Rocket": "Rocket Fog Subarea Room (in Wooded Kingdom)",  # FogMountainEx (ID: EX_Mist)
"Sheep": "Sheep Subarea Room (in Wooded Kingdom)",  # AnimalChaseEx (ID: EX_AnimalChase)
"Tank": "Sherm / Fire Bro Subarea Room (in Wooded Kingdom)",  # ShootingElevatorEx (ID: EX_Tankuro)
"Vine Clouds": "Beanstalk Subarea Room (in Wooded Kingdom)",  # ForestWorldCloudBonusEx (ID: EXCloud)
"Breakdown": "Breakdown Road Room (in Wooded Kingdom)",  # KillerRoadEx (ID: KillerRoad)
"Invisible": "Poison Piranha Plant Subarea Room (in Wooded Kingdom)",  # PackunPoisonEx (ID: PoisonEx)
"Flooded Pipes": "Flood Pipeway Room (in Wooded Kingdom)",  # ForestWorldWaterEx (ID: EX_Water)
"Flower Road": "Flower Road over Poison Room (in Wooded Kingdom)",  # RailCollisionEx (ID: EX_RailCollision)
"Treasure Room": "Nut Bonus Room (in Wooded Kingdom)",  # ForestWorldBonus (ID: bonus)

# =========================================================
# Cloud Kingdom
# =========================================================
"Picture Match": "Stone Face Picture Match Room (in Cloud Kingdom)",  # FukuwaraiKuribo (ID: Fukuwarai)
"2D Blocks": "2D Floating Blocks Subarea Room (in Cloud Kingdom)",  # Cube2DEx (ID: cube)

# =========================================================
# Lost Kingdom
# =========================================================
"Wiggler": "Piranha Plant & Wiggler Moon Pipe Room (in Lost Kingdom)",  # ImomuPoisonEx (ID: imomu_01)
"Shop": "Crazy Cap Shop Room (in Lost Kingdom)",  # ClashWorldShop (ID: Kinopio)
"Klepto": "Klepto Subarea Room (in Lost Kingdom)",  # JangoEx (ID: ClashWorldMoonEX2)

# =========================================================
# Metro Kingdom
# =========================================================
"Yellow Shop": "Crazy Cap Shop Room (in Metro Kingdom)",  # CityWorldShop01 (ID: shop_corect)
"Purple Shop": "Crazy Cap Shop Room (in Metro Kingdom)",  # CityWorldShop01 (ID: shop_coin)
"Dino": "T-Rex Subarea Room (in Metro Kingdom)",  # TrexBikeEx (ID: bike02)
"Bullet Billding": "Bullet Billding Room (in Metro Kingdom)",  # PoleKillerEx (ID: bou)
"Taxi": "Taxi Subarea Room (in Metro Kingdom)",  # ShootingCityEx (ID: taxi)
"Notes": "2D Notes Subarea Room (in Metro Kingdom)",  # Note2D3DRoomEx (ID: onpu)
"2D": "2D SMB1 Movie Room (in Metro Kingdom)",  # Theater2DEx (ID: theater)
"Slots": "Slots Room (in Metro Kingdom)",  # CityWorldSandSlot (ID: Bonus)
"People": "Crowded People Road Room (in Metro Kingdom)",  # CityPeopleRoad (ID: gunsyu)
"Outfit": "Electric Wire Subarea Room (in Metro Kingdom)",  # ElectricWireEx (ID: densen)
"Rocket": "Rocket Pole Subarea Room (in Metro Kingdom)",  # PoleGrabCeilEx (ID: tenjo)
"Dark": "Dark Ogres Pipe Room (in Metro Kingdom)",  # DonsukeEx (ID: donsuke)
"Scaffolding": "Hammer Bros Pipe Room (in Metro Kingdom)",  # SwingSteelEx (ID: gragra)
"Scooter": "Bike Subarea Room (in Metro Kingdom)",  # BikeSteelEx (ID: bike)
"Rotating Maze": "Spinies Maze Pipe Room (in Metro Kingdom)",  # CapRotatePackunEx (ID: kaitendokan)
"RC Car": "RC Car Room (in Metro Kingdom)",  # RadioControlEx

# =========================================================
# Snow Kingdom
# =========================================================
"Puzzle": "Ty-Foo Puzzle Room (in Snow Kingdom)",  # ByugoPuzzleEx (ID: ByugoPuzzle)
"Capless": "Freezing Water Climb Room (in Snow Kingdom)",  # IceWaterBlockEx (ID: EX_IceWater)
"Rocket Flower": "Rocket Flower Water Subarea Room (in Snow Kingdom)",  # IceWaterDashEx (ID: EX_IceWaterDash)
"Iceburn": "Bound Bowl Iceburn Circuit Room (in Snow Kingdom)",  # SnowWorldRace001
"Flower Road": "Banzai Bill Flower Road Room (in Snow Kingdom)",  # KillerRailCollisionEx (ID: EX_RailCol2)
"Tracewalking": "Tracewalking Subarea Room (in Snow Kingdom)",  # IceWalkerEx (ID: FigureWalker)
"Clouds": "Beanstalk Cloud Subarea Room (in Snow Kingdom)",  # SnowWorldCloudBonusEx (ID: EX_SkyBonus)
"Outfit": "2D Outfit Subarea Room (in Snow Kingdom)",  # SnowWorldCostume
"Shop": "Crazy Cap Shop Room (in Snow Kingdom)",  # SnowWorldShop

# =========================================================
# Seaside Kingdom
# =========================================================
"Well Enter": "Underwater Cave Room (in Seaside Kingdom)",  # SeaWorldUtsuboCave (ID: PukupukuCaveStart)
"Well Exit": "Underwater Cave Room (in Seaside Kingdom)",  # SeaWorldUtsuboCave (ID: PukupukuCaveStart)
"Rumble": "Rumble Room (in Seaside Kingdom)",  # SeaWorldVibration (ID: shindo_Lv2)
"Rocket": "Rocket Subarea Room (in Seaside Kingdom)",  # CloudEx (ID: SeaWorldEX2)
"Outfit": "Sailor Costume Room (in Seaside Kingdom)",  # SeaWorldCostume (ID: CostumeEventSeaWorld)
"Gushen": "Gushen Subarea Room (in Seaside Kingdom)",  # WaterValleyEx (ID: SeaWorldEX1a)
"Sphynx": "Sphynx Room (in Seaside Kingdom)",  # SeaWorldSecret (ID: TreasureEventWorldSea)
"Pokio": "Pokio Moon Pipe Subarea Room (in Seaside Kingdom)",  # ReflectBombEx (ID: SeaWorldMoonEX1a)
"Lava Rising": "Uproot Lava Subarea Room (in Seaside Kingdom)",  # SenobiTowerEx (ID: SeaWorldEX3a)
"Sandy Bottom": "Sneaking Man Room (in Seaside Kingdom)",  # SeaWorldSneakingMan (ID: RoomEventWorldSea)
"Spinning Maze": "Spinies Rotate Pipe Room (in Seaside Kingdom)",  # TogezoRotateEx (ID: SeaWorldMoonEX2)

# =========================================================
# Luncheon Kingdom
# =========================================================
"Slots": "Luncheon Slots Room (in Luncheon Kingdom)",  # LavaBonus1 (ID: town)
"Magma Swamp": "Piranha Up and Down Room (in Luncheon Kingdom)",  # LavaWorldUpDownEx (ID: KeyMoveEx)
"Volcano Cave": "Blue Platforms & Clouds Room (in Luncheon Kingdom)",  # CapAppearLavaLiftEx (ID: LavaLiftEx)
"Forks": "Forks Room (in Luncheon Kingdom)",  # ForkEx (ID: ForkEX)
"Cheese Rocks": "Cheese Shards Room (in Luncheon Kingdom)",  # LavaWorldExcavationEx (ID: MartinCubeEx)
"Veggie Room": "Chest & Vegetables Room (in Luncheon Kingdom)",  # LavaWorldTreasure (ID: TreasureEventWorldLava)
"Shop": "Crazy Cap Shop Room (in Luncheon Kingdom)",  # LavaWorldShop (ID: shop)
"Outfit": "Chef Costume Room (in Luncheon Kingdom)",  # LavaWorldCostume (ID: CostumeEventWorldLava)
"Spinning Athletics": "Spinning Athletics Room (in Luncheon Kingdom)",  # LavaWorldClockEx (ID: BBQEx)
"Lava Islands": "Podoboo Moon Pipe Room (in Luncheon Kingdom)",  # LavaWorldFenceLiftEx (ID: FenceLiftEx)
"Gears": "Fire Bros & Ice Snakes Room (in Luncheon Kingdom)",  # GabuzouClockEx (ID: GabuzouClockEx)
"Magma Path": "Podoboo Lane Room (in Luncheon Kingdom)",  # LavaWorldBubbleLaneEx (ID: PechoBubbleEx)

# =========================================================
# Ruined Kingdom
# =========================================================
"Chargin' Chuck": "Chargin' Chuck Moon Pipe Room (in Ruined Kingdom)",  # BullRunEx (ID: BossRaidWorldMoonEx02_Enter)
"Rocket": "2D Roulette Tower Room (in Ruined Kingdom)",  # DotTowerEx (ID: BossRaidWorldEx01_Eixt)

# =========================================================
# Bowser's Kingdom
# =========================================================
"Jizo": "Jizo + P-Switch Pipe Room (in Bowser's Kingdom)",  # JizoSwitchEx (ID: jizo01)
"Shop": "Crazy Cap Shop Room (in Bowser's Kingdom)",  # SkyWorldShop (ID: shop)
"Outfit": "Costume Room (in Bowser's Kingdom)",  # SkyWorldCostume (ID: byoubu)
"Treasure Room": "Chest Room (in Bowser's Kingdom)",  # SkyWorldTreasure (ID: shop_dress)
"Spinning Tower": "Pokio Climb Room (in Bowser's Kingdom)",  # TsukkunRotateEx (ID: tukkun000_enter)
"Vine Clouds": "Beanstalk Rocket Room (in Bowser's Kingdom)",  # SkyWorldCloudBonusEx (ID: sora001)
"Hexagon Tower": "Pokio Tower Room (in Bowser's Kingdom)",  # TsukkunClimbEx (ID: tukkun001_enter)
"Wooden Tower": "Para-Bones Tower Room (in Bowser's Kingdom)",  # KaronWingTower

# =========================================================
# Moon Kingdom
# =========================================================
"Galaxy2D": "Low Gravity 2D Subarea Room (in Moon Kingdom)",  # Galaxy2DEx (ID: dot00)
"Athletic": "Moon Rock Pipe Room (in Moon Kingdom)",  # MoonAthleticEx (ID: moon)
"Sphinx": "Sphinx Room (in Moon Kingdom)",  # MoonWorldSphinx (ID: ggg)
"Shop": "Crazy Cap Shop Room (in Moon Kingdom)",  # MoonWorldShop (ID: ddd)

# =========================================================
# Mushroom Kingdom
# =========================================================
"Yoshi Cloud": "Yoshi Pipe Subarea Room (in Mushroom Kingdom)",  # YoshiCloudEx (ID: PeachWorldEx1a)
"Dot Hard": "2D Well Subarea Room (in Mushroom Kingdom)",  # DotHardEx (ID: PeachWorldEx2a)
"Fukuwarai": "Mario Picture Match Room (in Mushroom Kingdom)",  # FukuwaraiMario (ID: Fukuwarai2)
"Peach Castle": "Peach Castle Room (in Mushroom Kingdom)",  # PeachWorldCastle (ID: PeachCastleGate)
"Shop": "Crazy Cap Shop Room (in Mushroom Kingdom)",  # PeachWorldShop (ID: PeachWorldShopA)
"Costume": "Courtyard Costume Room (in Mushroom Kingdom)",  # PeachWorldCostume (ID: CostumeEventWorldPeach)
"Boss Painting: TorkDrift": "TorkDrift Boss Rematch Room (in Mushroom Kingdom)",  # PeachWorldPictureBossForest (ID: BossForestA)
"Boss Painting: Knuckleotec": "Knuckleotec Boss Rematch Room (in Mushroom Kingdom)",  # PeachWorldPictureBossKnuckle (ID: BossKnuckleA)
"Boss Painting: Cookatiel": "Cookatiel Boss Rematch Room (in Mushroom Kingdom)",  # PeachWorldPictureBossMagma (ID: BossMagmaA)
"Boss Painting: Ruined Dragon": "Ruined Dragon Boss Rematch Room (in Mushroom Kingdom)",  # PeachWorldPictureBossRaid (ID: BossRaidA)
"Boss Painting: Brigadier Mollosque-Lanceur III, Dauphin of Bubblaine": "Brigadier Mollosque-Lanceur III Boss Rematch Room (in Mushroom Kingdom)",  # PeachWorldPictureGiantWanderBoss (ID: GiantWanderBossA)
"Boss Painting: Mechawiggler": "Mechawiggler Boss Rematch Room (in Mushroom Kingdom)",  # PeachWorldPictureMofumofu (ID: MofumofuA)

# =========================================================
# Dark Side
# =========================================================
"Tower Stacker": "Broodal Tower Stack Room (in Dark Side)",  # Special1WorldTowerStackerStage (ID: StackerRoomStart)
"Tower Bomb": "Broodal Bomb Room (in Dark Side)",  # Special1WorldTowerBombTailStage (ID: BombTailRoomStart)
"Tower Fire": "Fire Blower Room (in Dark Side)",  # Special1WorldTowerFireBlowerStage (ID: FireBlowerRoomStart)
"Tower Cap": "Cap Thrower Room (in Dark Side)",  # Special1WorldTowerCapThrowerStage (ID: CapThrowerRoomStart)
"Bike No Cap": "No Cap Bike Room (in Dark Side)",  # BikeSteelNoCapExStage (ID: BikeSteelNoCapEx)
"Poison No Cap": "No Cap Poison Room (in Dark Side)",  # PackunPoisonNoCapExStage (ID: PackunPoisonNoCapEx)
"Road No Cap": "No Cap Road Room (in Dark Side)",  # KillerRoadNoCapExStage (ID: KillerRoadNoCapEx)
"Taxi Yoshi": "Yoshi Taxi Clone Room (in Dark Side)",  # ShootingCityYoshiExStage (ID: ShootingCityYoshiEx)
"Senobi Yoshi": "Yoshi Uproot Room (in Dark Side)",  # SenobiTowerYoshiExStage (ID: SenobiTowerYoshiEx)
"Lava Yoshi": "Yoshi Lava Room (in Dark Side)",  # LavaWorldUpDownYoshiExStage (ID: LavaWorldUpDownYoshiEx)
"""




def parse_room_database(text):
    """
    Parse the SMO Randomizer room-name database (a Python-dict-literal-style
    listing with trailing "# InternalName (ID: entrance_id)" comments) into a
    lookup of {(kingdom, entrance/exit id): human-readable room name}.

    Raw ids are NOT globally unique — e.g. id "shop" means a different room
    in Luncheon Kingdom than it does in Bowser's Kingdom, and id "town" means
    a different room in Sand Kingdom than in Luncheon Kingdom. Every
    description ends in a "(in X Kingdom)" / "(in Dark Side)" tag, which is
    used as the other half of the lookup key.

    A single line can list more than one id, separated by "/", e.g.:
        # SandWorldSphinxEx (ID: aaa/run00)
    Lines whose comment has no "(ID: ...)" piece are skipped, since they
    can't be matched against anything in the Entrance Randomizer section.
    """
    lookup = {}
    line_re = re.compile(r'^"[^"]+":\s*"([^"]+)",.*?\(ID:\s*([^)]+)\)\s*$')
    kingdom_re = re.compile(r'^(.*)\(in ([^)]+)\)$')
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith('"'):
            continue
        m = line_re.match(line)
        if not m:
            continue
        description, id_blob = m.group(1), m.group(2)
        km = kingdom_re.match(description)
        kingdom = km.group(2).strip() if km else None
        for entry_id in id_blob.split("/"):
            entry_id = entry_id.strip()
            if entry_id:
                lookup[(kingdom, entry_id)] = description
    return lookup


# Global id → human-readable-room-name lookup, built once at import time.
ROOM_NAME_LOOKUP = parse_room_database(ROOM_DATABASE_TEXT)


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
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        self._nav_nodes = []            # Chapters sidebar tree (containers + leaf pages)

        # ── Page registry (lazy-loaded "Chapters" pages) ──
        # Each page has: key, title, builder(parent)->None, built flag, and its own
        # canvas/inner frame + text-item list so search/highlight only ever touches
        # whichever page is currently on screen. Building all four sections (which
        # can easily be 1000+ widgets total) into one giant frame up front is what
        # was causing the window to hang/stop responding — now only the page the
        # user actually clicks on gets built.
        self._pages = {}            # key -> dict(title, builder, frame, canvas, inner, built, text_items, capture_tag_items)
        self._current_page_key = None

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

        # ── Quick-search lists ──────────────────────────────────────────────────
        CAPTURES_LIST = [
            "Frog", "Spark Pylon", "Paragoomba", "Chain Chomp", "Big Chain Chomp",
            "Broode's Chain Chomp", "T-Rex", "Binoculars", "Bullet Bill", "Moe-Eye",
            "Cactus", "Goomba", "Knucklotec's Fist", "Mini Rocket", "Glydon", "Lakitu",
            "Zipper", "Cheep Cheep", "Puzzle Part (Lake Kingdom)", "Poison Piranha Plant",
            "Uproot", "Fire Bro", "Sherm", "Coin Coffer", "Tree", "Boulder",
            "Picture Match Part (Goomba)", "Tropical Wiggler", "Pole", "Manhole",
            "Taxi", "RC Car", "Ty-Foo", "Shiverian Racer", "Cheep Cheep (Snow Kingdom)",
            "Gushen", "Lava Bubble", "Volbonan", "Hammer Bro", "Meat",
            "Fire Piranha Plant", "Pokio", "Jizo", "Bowser Statue", "Parabones",
            "Banzai Bill", "Chargin' Chuck", "Bowser", "Letter",
            "Puzzle Part (Metro Kingdom)", "Picture Match Part (Mario)", "Yoshi",
        ]
        MOVEMENT_LIST = [
            "Double Jump", "Triple Jump", "Backflip", "Long Jump", "Vault",
            "Side Flip", "Ground Pound", "Dive", "Ground Pound Jump", "Roll",
            "Roll Boost", "Spin", "Wall Jump", "Ledge Grab", "Climb",
            "Up Throw", "Down Throw", "Spin Throw", "Neutral Throw",
        ]

        # ── Body: Chapters sidebar (left) + content (right) ──
        body_container = tk.Frame(self, bg=BG_COLOR)
        body_container.pack(fill="both", expand=True)
        body_container.grid_rowconfigure(0, weight=1)
        body_container.grid_columnconfigure(1, weight=1)

        self._chapters_sidebar = tk.Frame(body_container, bg="#101010", width=190)
        self._chapters_sidebar.grid(row=0, column=0, sticky="ns")
        self._chapters_sidebar.grid_propagate(False)

        tk.Label(self._chapters_sidebar, text="📖 Chapters", bg="#101010", fg="#999999",
                 font=("Fredoka", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        chapters_canvas = tk.Canvas(self._chapters_sidebar, bg="#101010", highlightthickness=0)
        chapters_vsb = tk.Scrollbar(self._chapters_sidebar, orient="vertical",
                                     command=chapters_canvas.yview)
        chapters_canvas.configure(yscrollcommand=chapters_vsb.set)
        chapters_vsb.pack(side="right", fill="y")
        chapters_canvas.pack(side="left", fill="both", expand=True)
        self._chapters_canvas = chapters_canvas

        self._chapters_inner = tk.Frame(chapters_canvas, bg="#101010")
        chapters_canvas.create_window((0, 0), window=self._chapters_inner, anchor="nw")
        self._chapters_inner.bind(
            "<Configure>",
            lambda e: chapters_canvas.configure(scrollregion=chapters_canvas.bbox("all")))

        def _chapters_mw(evt):
            chapters_canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
            return "break"
        chapters_canvas.bind("<MouseWheel>", _chapters_mw)
        chapters_canvas.bind("<Button-4>", lambda e: (chapters_canvas.yview_scroll(-1, "units"), "break"))
        chapters_canvas.bind("<Button-5>", lambda e: (chapters_canvas.yview_scroll(1, "units"), "break"))

        content_frame = tk.Frame(body_container, bg=BG_COLOR)
        content_frame.grid(row=0, column=1, sticky="nsew")

        # ── Search bar (only shown on structured tab) ──
        self._search_outer = tk.Frame(content_frame, bg=BG_COLOR)
        self._search_outer.pack(fill="x", padx=10, pady=(8, 2))

        # Row 1: text entry
        search_row = tk.Frame(self._search_outer, bg=BG_COLOR)
        search_row.pack(fill="x")
        tk.Label(search_row, text="🔍 Search:", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=FONT_NORMAL).pack(side="left")
        self._search_entry = ctk.CTkEntry(
            search_row, textvariable=self._search_var,
            placeholder_text="Filter this section…",
            width=400, height=30, font=FONT_NORMAL)
        self._search_entry.pack(side="left", padx=8)
        ctk.CTkButton(search_row, text="✕ Clear", width=60, height=30,
                      fg_color="#444444", hover_color="#222222",
                      corner_radius=8, font=FONT_NORMAL,
                      command=lambda: self._search_var.set("")).pack(side="left")

        # Row 2: quick-search dropdowns
        quick_row = tk.Frame(self._search_outer, bg=BG_COLOR)
        quick_row.pack(fill="x", pady=(4, 2))

        # Load small icons for the dropdown labels
        _star_img = resize_by_height(
            Image.open(resource_path("assets/Star.png")).convert("RGBA"), 18)
        _dark_img = resize_by_height(
            Image.open(resource_path("assets/Dark.png")).convert("RGBA"), 18)
        self._qs_star_photo = ImageTk.PhotoImage(_star_img)
        self._qs_dark_photo = ImageTk.PhotoImage(_dark_img)

        # Captures icon label
        tk.Label(quick_row, image=self._qs_star_photo, bg=BG_COLOR).pack(side="left", padx=(0, 2))

        self._captures_var = tk.StringVar(value="Captures…")
        captures_menu = ctk.CTkOptionMenu(
            quick_row,
            variable=self._captures_var,
            values=["Captures…"] + CAPTURES_LIST,
            command=self._on_quick_search,
            width=170, height=26,
            font=FONT_ZONES,
            fg_color="#1f3a6e", button_color="#1a3060",
            dropdown_fg_color="#1a1a2e", dropdown_hover_color="#1f6feb",
        )
        captures_menu.pack(side="left", padx=(0, 12))

        # Movement icon label
        tk.Label(quick_row, image=self._qs_dark_photo, bg=BG_COLOR).pack(side="left", padx=(0, 2))

        self._movement_var = tk.StringVar(value="Movement…")
        movement_menu = ctk.CTkOptionMenu(
            quick_row,
            variable=self._movement_var,
            values=["Movement…"] + MOVEMENT_LIST,
            command=self._on_quick_search,
            width=170, height=26,
            font=FONT_ZONES,
            fg_color="#3a1a3a", button_color="#2e1530",
            dropdown_fg_color="#1a1a2e", dropdown_hover_color="#9b59b6",
        )
        movement_menu.pack(side="left")

        # ── Main pane (swap between structured / raw) ──
        self._pane = tk.Frame(content_frame, bg=BG_COLOR)
        self._pane.pack(fill="both", expand=True)

        self._structured_outer = None
        self._raw_frame = None

        def _refresh_tab():
            for w in self._pane.winfo_children():
                w.pack_forget()
            v = self._current_tab.get()
            if v == "structured":
                self._chapters_sidebar.grid()
                self._search_outer.pack(fill="x", padx=10, pady=(8, 4))
                if self._structured_outer is None:
                    self._build_structured()
                self._structured_outer.pack(fill="both", expand=True)
            else:
                self._chapters_sidebar.grid_remove()
                self._search_outer.pack_forget()
                if self._raw_frame is None:
                    self._build_raw()
                self._raw_frame.pack(fill="both", expand=True)

        _refresh_tab()

    # ------------------------------------------------------------------ #
    #  Structured view — one lazy-built "page" per *leaf* section
    #  (a single kingdom for Moon Placements / Loading Zones, or a whole
    #  flat section for Paintings / Progress Path). Only the leaf the user
    #  actually clicks on is ever built or shown, and only one at a time.
    # ------------------------------------------------------------------ #

    def _build_structured(self):
        """Set up the structured-tab container and register (but do NOT build)
        every leaf section as its own page, plus build the collapsible Chapters
        navigation tree. Pages are built the first time they're selected."""
        outer = tk.Frame(self._pane, bg=BG_COLOR)
        self._structured_outer = outer

        data = self._data

        # Navigation tree shown in the left "Chapters" sidebar. Each node is
        # either a "page" (clicking shows it) or a "container" (clicking
        # expands/collapses its per-kingdom children). It's built entirely from
        # the parsed data up front — no widgets are created until a leaf is
        # opened, so the window never hangs building everything at once.
        self._nav_nodes = []

        if data["moons"]:
            children = []
            for kingdom, entries in data["moons"].items():
                page_key = f"moons::{kingdom}"
                self._register_page(
                    outer, page_key, f"🌙Moon Placements — {kingdom}",
                    lambda p, e=entries: self._build_moons(p, e))
                children.append({"key": page_key, "label": kingdom})
            self._nav_nodes.append({
                "kind": "container", "key": "moons",
                "title": "🌙Moon Placements", "children": children,
                "expanded": False})

        if data["paintings"]:
            self._register_page(outer, "paintings", "🖼️Painting Destinations",
                                lambda p: self._build_paintings(p, data["paintings"]))
            self._nav_nodes.append({
                "kind": "page", "key": "paintings",
                "title": "🖼️Painting Destinations"})

        if data["entrances"]:
            children = []
            for kingdom, entries in data["entrances"].items():
                page_key = f"entrances::{kingdom}"
                self._register_page(
                    outer, page_key, f"🚪  Loading Zone Connections — {kingdom}",
                    lambda p, e=entries: self._build_entrances(p, e))
                children.append({"key": page_key, "label": kingdom})
            self._nav_nodes.append({
                "kind": "container", "key": "entrances",
                "title": "🚪Loading Zone Connections", "children": children,
                "expanded": False})

        if data["path"]:
            self._register_page(outer, "path", "📍  Suggested Progress Path",
                                lambda p: self._build_path(p, data["path"]))
            self._nav_nodes.append({
                "kind": "page", "key": "path",
                "title": "📍  Suggested Progress Path"})

        # Landing placeholder shown until the user opens a chapter.
        self._landing = tk.Frame(outer, bg=BG_COLOR)
        tk.Label(
            self._landing,
            text=("Select a chapter on the left to view it.\n\n"
                  "Moon Placements and Loading Zone Connections expand into\n"
                  "their kingdoms when clicked — pick a kingdom to show only\n"
                  "that section. Only one section is shown at a time."),
            bg=BG_COLOR, fg="#888888", font=FONT_NORMAL,
            justify="left").pack(padx=24, pady=24, anchor="w")

        if not self._nav_nodes:
            tk.Label(outer, text="⚠ No structured data recognised — use the 'Raw JSON / Text' tab.",
                     bg=BG_COLOR, fg="#ff8844", font=FONT_NORMAL,
                     wraplength=600, justify="left").pack(padx=20, pady=30)

        self._show_landing()

    def _register_page(self, outer, key, title, builder):
        """Create the (empty) scroll container for a page, deferring the actual
        widget-building work until the page is first shown."""
        frame = tk.Frame(outer, bg=BG_COLOR)

        seed = self._data["meta"].get("seed", "Unknown")

        canvas = tk.Canvas(frame, bg=BG_COLOR, highlightthickness=0)
        vsb = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG_COLOR)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))

        tk.Label(inner, text=f"Seed: {seed}", bg=BG_COLOR, fg="#aaaaaa",
                 font=("Fredoka", 13)).pack(anchor="w", padx=16, pady=(8, 4))
        tk.Label(inner, text=title, bg=BG_COLOR, fg=TEXT_COLOR,
                 font=FONT_BIG).pack(anchor="w", padx=16, pady=(0, 4))

        body_host = tk.Frame(inner, bg=BG_COLOR)
        body_host.pack(fill="both", expand=True)

        self._pages[key] = {
            "title": title,
            "builder": builder,
            "frame": frame,
            "canvas": canvas,
            "inner": inner,
            "body_host": body_host,
            "built": False,
            "text_items": [],
            "capture_tag_items": [],
        }

    def _ensure_page_built(self, key):
        """Build a page's contents the first time it's needed (lazy)."""
        page = self._pages.get(key)
        if page is None or page["built"]:
            return
        page["built"] = True
        self._active_page_key_for_build = key
        try:
            page["builder"](page["body_host"])
        finally:
            self._active_page_key_for_build = None

    def _register_text_item(self, widget):
        """Add a label to the currently-building page's search index."""
        key = getattr(self, "_active_page_key_for_build", None)
        if key is not None and key in self._pages:
            self._pages[key]["text_items"].append(widget)

    def _register_capture_tag(self, widget, tags):
        """Add a (label, tags) pair to the currently-building page's capture index."""
        key = getattr(self, "_active_page_key_for_build", None)
        if key is not None and key in self._pages:
            self._pages[key]["capture_tag_items"].append((widget, tags))

    def _hide_all_pages(self):
        """Detach the landing placeholder and every page frame from view."""
        if getattr(self, "_landing", None) is not None:
            self._landing.pack_forget()
        for p in self._pages.values():
            p["frame"].pack_forget()

    def _show_landing(self):
        """Show the 'pick a chapter' placeholder and clear the current page."""
        self._hide_all_pages()
        self._current_page_key = None
        if getattr(self, "_landing", None) is not None:
            self._landing.pack(fill="both", expand=True)
        self._populate_chapters()

    def _show_page(self, key):
        """Switch the structured-tab view to the given leaf page, building it if
        this is the first time it's been opened. Only one page is ever shown."""
        if key not in self._pages:
            return
        self._ensure_page_built(key)

        self._hide_all_pages()

        page = self._pages[key]
        page["frame"].pack(fill="both", expand=True)
        self._current_page_key = key
        self._scroll_canvas = page["canvas"]
        self._structured_inner = page["inner"]

        # Make sure the parent container is expanded so the active kingdom is
        # visible in the sidebar, then refresh the sidebar to reflect selection.
        for node in getattr(self, "_nav_nodes", []):
            if node["kind"] == "container":
                if any(c["key"] == key for c in node["children"]):
                    node["expanded"] = True
        self._populate_chapters()

        # Re-bind mouse-wheel scrolling to whichever canvas is now visible.
        canvas = page["canvas"]
        def _mw(evt):
            canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _mw)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # Re-apply any active search filter to the page now on screen.
        self._on_search_changed()

    # ── Chapters sidebar ──
    def _toggle_container(self, node):
        """Expand/collapse a top-level container's kingdom list in the sidebar."""
        node["expanded"] = not node["expanded"]
        self._populate_chapters()

    def _make_chapter_button(self, text, color, font, pad_left, on_click, pady):
        """Create one clickable row in the Chapters sidebar."""
        btn = tk.Label(self._chapters_inner, text=text, bg="#101010", fg=color,
                       font=font, cursor="hand2", anchor="w",
                       wraplength=165, justify="left")
        btn.pack(fill="x", padx=(pad_left, 8), pady=pady)
        btn.bind("<Button-1>", on_click)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(fg="#ffffff"))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.configure(fg=c))
        # Scroll the sidebar (not the content pane) when the wheel is used while
        # hovering a chapter row. Returning "break" stops the global content-pane
        # wheel binding from also firing.
        cc = self._chapters_canvas
        btn.bind("<MouseWheel>",
                 lambda e: (cc.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
        btn.bind("<Button-4>", lambda e: (cc.yview_scroll(-1, "units"), "break")[1])
        btn.bind("<Button-5>", lambda e: (cc.yview_scroll(1, "units"), "break")[1])
        return btn

    def _populate_chapters(self):
        """(Re)build the collapsible Chapters sidebar from the navigation tree."""
        for w in self._chapters_inner.winfo_children():
            w.destroy()

        if not getattr(self, "_nav_nodes", None):
            tk.Label(self._chapters_inner, text="No sections found.",
                     bg="#101010", fg="#555555", font=("Fredoka", 11),
                     wraplength=160, justify="left").pack(padx=12, pady=8, anchor="w")
            return

        for node in self._nav_nodes:
            if node["kind"] == "page":
                self._make_chapter_button(
                    node["title"], "#dddddd", FONT_BIG, 12,
                    lambda e, k=node["key"]: self._show_page(k), pady=(8, 2))
            else:  # container
                arrow = "▾" if node["expanded"] else "▸"
                self._make_chapter_button(
                    f"{arrow}  {node['title']}", "#dddddd", FONT_BIG, 12,
                    lambda e, n=node: self._toggle_container(n), pady=(8, 2))
                if node["expanded"]:
                    for child in node["children"]:
                        active = (child["key"] == self._current_page_key)
                        color = "#ffffff" if active else _kc(child["label"])
                        label = ("• " if active else "") + child["label"]
                        self._make_chapter_button(
                            label, color, ("Fredoka", 11), 28,
                            lambda e, k=child["key"]: self._show_page(k), pady=1)

    # ── Moon Placements (a single kingdom's entries) ──
    def _build_moons(self, parent, entries):
        """
        Build the moon placements for ONE kingdom (the page is per-kingdom).
        Entries are laid out in a 3-column grid (Unlock/Moon | arrow | Destination)
        so the arrow sits in the same place on every row, no matter how long the
        moon/kingdom names are.
        Entry format (top line):
          Unlock Moon (or trigger)  →  Dest Kingdom Moon  [Capture Tag]
        Entry format (grey subtext, right under the destination text):
          Originally 'Moon Name'
        If there is no unlock/trigger moon (standalone placement), the left side
        falls back to showing the moon name itself, and no "Originally" subtext
        is shown since there's nothing different to attribute it to.
        """
        grid = tk.Frame(parent, bg=BG_COLOR)
        grid.pack(fill="x", padx=4, anchor="w")

        r = 0
        for e in entries:
            has_unlock = bool(e["unlock_at"])
            left_text = e["unlock_at"] if has_unlock else e["moon"]
            pady_top = (6, 0) if has_unlock else (6, 4)

            left_lbl = tk.Label(grid, text=left_text, bg=BG_COLOR, fg=TEXT_COLOR,
                                font=FONT_ZONES, anchor="w", cursor="hand2")
            left_lbl.grid(row=r, column=0, sticky="w", pady=pady_top)
            self._register_text_item(left_lbl)

            tk.Label(grid, text="  →  ", bg=BG_COLOR, fg="#666666",
                     font=FONT_ZONES).grid(row=r, column=1, pady=pady_top)

            dest_text = f"{e['dest']} Moon"
            if e["capture"]:
                dest_text += f": [{e['capture']}]"
            dest_lbl = tk.Label(grid, text=dest_text, bg=BG_COLOR,
                                fg=_kc(e["dest"]), font=FONT_ZONES, anchor="w")
            dest_lbl.grid(row=r, column=2, sticky="w", pady=pady_top)
            self._register_text_item(dest_lbl)

            # Register for exact capture-tag matching (split on comma, strip whitespace)
            if e["capture"]:
                tags = [t.strip() for t in e["capture"].split(",") if t.strip()]
                self._register_capture_tag(dest_lbl, tags)

            r += 1

            # Grey "Originally '<Moon Name>'" subtext, sharing the destination
            # column so it lines up directly under the destination text. Only
            # shown when the top line's left side is the unlock/trigger moon
            # rather than this moon's own name.
            if has_unlock:
                orig_lbl = tk.Label(grid, text=f"Originally '{e['moon']}'",
                                    bg=BG_COLOR, fg="#888888",
                                    font=("Fredoka", 11), anchor="w")
                orig_lbl.grid(row=r, column=2, sticky="w", pady=(0, 4))
                self._register_text_item(orig_lbl)
                r += 1

    # ── Paintings ──
    def _build_paintings(self, parent, paintings):
        grid = tk.Frame(parent, bg=BG_COLOR)
        grid.pack(fill="x", padx=12, anchor="w")

        for r, (a, b) in enumerate(paintings):
            la = tk.Label(grid, text=a, bg=BG_COLOR, fg=_kc(a), font=FONT_ZONES, anchor="w")
            la.grid(row=r, column=0, sticky="w", pady=2)
            tk.Label(grid, text="  ↔  ", bg=BG_COLOR, fg="#666666",
                     font=FONT_ZONES).grid(row=r, column=1, pady=2)
            lb = tk.Label(grid, text=b, bg=BG_COLOR, fg=_kc(b), font=FONT_ZONES, anchor="w")
            lb.grid(row=r, column=2, sticky="w", pady=2)
            self._register_text_item(la)
            self._register_text_item(lb)

    # ── Entrances (a single kingdom's entries) ──
    def _build_entrances(self, parent, entries):
        grid = tk.Frame(parent, bg=BG_COLOR)
        grid.pack(fill="x", padx=4, anchor="w")

        r = 0
        for e in entries:
            # Look up human-readable room names from the database, keyed by
            # (kingdom, raw id) since the same raw id (e.g. "shop", "town")
            # means a different room in different kingdoms.
            from_desc = ROOM_NAME_LOOKUP.get((e.get("from_kingdom"), e.get("from_id")))
            to_desc = ROOM_NAME_LOOKUP.get((e.get("to_kingdom"), e.get("to_id")))
            has_raw = bool(from_desc or to_desc)
            pady_top = (4, 0) if has_raw else (4, 4)

            from_lbl = tk.Label(grid, text=from_desc or e["from"], bg=BG_COLOR,
                                fg="#c8a060", font=FONT_ZONES, anchor="w")
            from_lbl.grid(row=r, column=0, sticky="w", pady=pady_top)
            tk.Label(grid, text="  →  ", bg=BG_COLOR, fg="#666666",
                     font=FONT_ZONES).grid(row=r, column=1, pady=pady_top)
            to_lbl = tk.Label(grid, text=to_desc or e["to"], bg=BG_COLOR,
                              fg="#60b8c8", font=FONT_ZONES, anchor="w")
            to_lbl.grid(row=r, column=2, sticky="w", pady=pady_top)
            self._register_text_item(from_lbl)
            self._register_text_item(to_lbl)
            r += 1

            # Secondary line: the raw internal stage/entrance ids, kept as a
            # quieter reference under the translated names. Only shown when a
            # translation actually happened — otherwise it'd just repeat itself.
            if has_raw:
                raw_lbl = tk.Label(grid, text=f"      {e['from']}  →  {e['to']}",
                                   bg=BG_COLOR, fg="#555555", font=("Fredoka", 10),
                                   anchor="w")
                raw_lbl.grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 4))
                self._register_text_item(raw_lbl)
                r += 1

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
            self._register_text_item(moon_lbl)
            self._register_text_item(kw_lbl)
            self._register_text_item(at_lbl)

            if step["unlocks"]:
                ul = tk.Label(row_outer,
                              text="  Unlocks: " + ", ".join(step["unlocks"]),
                              bg="#1c1c1c", fg="#70cc70", font=("Fredoka", 11))
                ul.pack(anchor="w", padx=6)
                self._register_text_item(ul)

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

    def _clear_all_highlights(self):
        """Reset the background of every label on every already-built page."""
        for page in self._pages.values():
            if not page["built"]:
                continue
            for lbl in page["text_items"]:
                if lbl.winfo_exists():
                    parent_bg = lbl.master.cget("bg") if lbl.master else BG_COLOR
                    lbl.configure(bg=parent_bg)

    def _find_capture_page(self, term):
        """Return the moon page key of the first kingdom (in data order) whose
        moon list contains *term* as an exact bracketed [...] tag, or None.
        Matching is restricted to the capture/ability tags, never moon names."""
        for kingdom, entries in self._data["moons"].items():
            for e in entries:
                if not e["capture"]:
                    continue
                tags = [t.strip().lower() for t in e["capture"].split(",") if t.strip()]
                if term in tags:
                    return f"moons::{kingdom}"
        return None

    def _on_quick_search(self, selection):
        """Called when a Captures or Movement dropdown item is selected.

        Searches every kingdom (not just the one on screen) for the selected
        word as an exact bracketed [...] tag, navigates to the page that holds
        the first match, then highlights every matching entry on that page and
        scrolls to the first one. Shows the not-found popup if nothing matches.
        Does NOT touch the text search bar or match against moon names."""
        if selection in ("Captures…", "Movement…"):
            return

        # Reset dropdown labels after a short delay so same item can be re-selected
        self.after(150, lambda: self._captures_var.set("Captures…"))
        self.after(150, lambda: self._movement_var.set("Movement…"))

        # Clear any existing text-search highlights first, then any leftover
        # quick-search highlights on other pages.
        self._search_var.set("")
        self._clear_all_highlights()

        term = selection.strip().lower()

        target_key = self._find_capture_page(term)
        if target_key is None:
            import tkinter.messagebox as mb
            mb.showwarning(
                "Ability Not Found",
                "Ability could not be found. There may be an issue with your generated seed.",
                parent=self
            )
            return

        # Navigate to the page holding the match (builds it lazily if needed).
        self._show_page(target_key)

        page = self._pages[target_key]
        first_match = None
        for lbl, tags in page["capture_tag_items"]:
            if not lbl.winfo_exists():
                continue
            if any(t.lower() == term for t in tags):
                lbl.configure(bg=HIGHLIGHT_BG)
                if first_match is None:
                    first_match = lbl
            else:
                parent_bg = lbl.master.cget("bg") if lbl.master else BG_COLOR
                lbl.configure(bg=parent_bg)

        if first_match is not None:
            self.after(50, lambda w=first_match: self._scroll_to_widget(w))

    def _on_search_changed(self, *_):
        query = self._search_var.get().strip().lower()
        first_match_widget = None

        page = self._pages.get(self._current_page_key) if self._current_page_key else None
        text_items = page["text_items"] if page else []

        for lbl in text_items:
            if not lbl.winfo_exists():
                continue
            try:
                text = lbl.cget("text").lower()
            except Exception:
                continue

            if query and query in text:
                lbl.configure(bg=HIGHLIGHT_BG)
                if first_match_widget is None:
                    first_match_widget = lbl
            else:
                # Restore original bg
                parent_bg = lbl.master.cget("bg") if lbl.master else BG_COLOR
                lbl.configure(bg=parent_bg)

        # Scroll so the first match is visible, after Tk has processed layout changes
        if first_match_widget is not None:
            self.after(50, lambda w=first_match_widget: self._scroll_to_widget(w))
        elif query:
            # Nothing matched — show "not found" popup after a short debounce
            # Only show once the user has stopped typing (300 ms idle)
            if hasattr(self, "_no_result_after"):
                self.after_cancel(self._no_result_after)
            self._no_result_after = self.after(
                400,
                lambda q=query: self._show_not_found_popup(q)
            )

    def _show_not_found_popup(self, query):
        """Show a popup when a search query matches nothing in the spoiler log."""
        # Don't show if the query has already changed or been cleared
        if self._search_var.get().strip().lower() != query:
            return
        import tkinter.messagebox as mb
        mb.showwarning(
            "Ability Not Found",
            "Ability could not be found. There may be an issue with your generated seed.",
            parent=self
        )

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
        self.lock_peace_hidden = False
        self.total_moon_tracker_hidden = False
        self.compact_view = False
        self.peace_lock_obs_hidden = False  # track OBS peace lock visibility
        self.moon_tick_enabled = False      # track moon tick icon visibility
        self.timer_visible = False          # track Timer widget visibility
        self.timer_seconds = 0              # current Timer duration, in seconds
        self.timer_ms_enabled = False       # track Milliseconds row visibility in Timer
        self.timer_running = False          # track whether the auto-running timer is active
        self._timer_after_id = None         # after() handle for the running timer's tick loop

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
        self.right_sidebar.grid_rowconfigure(3, weight=0)
        self.right_sidebar.grid_rowconfigure(4, weight=0)
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

        # ── Notes + Settings buttons live outside tracker_frame so they're never hidden ──
        self._buttons_frame = tk.Frame(self.right_sidebar, bg=BG_COLOR)
        self._buttons_frame.grid(row=3, column=0, pady=(6, 0))

        # Notes button
        ctk.CTkButton(
            self._buttons_frame, text="Notes", command=self.open_loading_zone_window,
            font=FONT_NORMAL, corner_radius=12, width=100
        ).pack(pady=(0, 6))

        # Settings button (black)
        ctk.CTkButton(
            self._buttons_frame, text="Settings", command=self.open_settings_window,
            font=FONT_NORMAL, corner_radius=12, width=100,
            fg_color="#000000", hover_color="#222222", text_color="#ffffff"
        ).pack()

        # Timer widget — lives below Settings in Main View, hidden until toggled on
        self._build_timer_widgets()

        self._hide_ability_text = tk.StringVar(value="Toggle Global Ability Lock")

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

        # --- Peace Ability Lock registry (shared by all PeaceCaptureIcon instances) ---
        self._peace_capture_registry = {}
        self.peace_lock_visible = False  # hidden by default

        # --- Left-column layout frame (2-column grid: kingdoms | captures) ---
        # This keeps all kingdom rows left-anchored and the captures panel
        # immediately to their right, matching the OBS overlay layout.
        self._left_layout = tk.Frame(self.left_column, bg=BG_COLOR)
        self._left_layout.pack(anchor="w", fill="none")

        # Col 0: kingdom rows stacked (cap/kingdoms/dark/star)
        self._kingdoms_col = tk.Frame(self._left_layout, bg=BG_COLOR)
        self._kingdoms_col.grid(row=0, column=0, sticky="nw")

        # Moon Cave + Cave Skip — placed in right sidebar below Moon Tracker (row 2)
        # _left_layout col 1 is no longer used for captures
        self._captures_col = tk.Frame(self.right_sidebar, bg=BG_COLOR)
        self._captures_col.grid(row=2, column=0, pady=(8, 0))

        tk.Label(self._captures_col, text="Moon Cave", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 11, "bold")).pack(pady=(0, 2))
        self.left_captures = CaptureRow(self._captures_col)
        self.left_captures.pack(pady=(0, 6))

        tk.Label(self._captures_col, text="Cave Skip", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 11, "bold")).pack(pady=(0, 2))
        self.right_captures = AbilityRow(self._captures_col, app=self)
        self.right_captures.pack()

        # --- Special rows (hidden by default) — all children of _kingdoms_col ---
        # Cap row: packed ABOVE Cascade
        self.cap_row = SimpleCounterRow(self._kingdoms_col, resource_path("assets/Cap.png"), self)
        # Star row: packed BELOW Bowser
        self.star_row = SimpleCounterRow(self._kingdoms_col, resource_path("assets/Star.png"), self)
        # Dark row: packed BELOW Star (or below Bowser if Star hidden)
        self.dark_row = MoonRow(self._kingdoms_col, resource_path("assets/Moon.png"), app=self)

        # --- Standard kingdom rows ---
        self.moon_rows = []
        self.peace_lock_rows = []
        self._kingdom_names = list(KINGDOMS.keys())  # ordered list of kingdom names
        for name, (k_img, m_img) in KINGDOMS.items():
            row = MoonRow(self._kingdoms_col, k_img, app=self)
            row.pack(pady=5, anchor="w")
            self.moon_rows.append(row)
            # Peace lock row — inline in the MoonRow grid at col 10
            peace_row = KingdomPeaceLockRow(row, name, app=self)
            peace_row.grid(row=0, column=10, padx=(8, 2))
            peace_row.grid_remove()  # hidden until toggled
            self.peace_lock_rows.append(peace_row)

        self.obs = None

        # Compact-mode total label — lives in _kingdoms_col, shown only in compact view
        self._compact_total_label = tk.Label(
            self._kingdoms_col,
            text="0 / 124",
            bg=BG_COLOR, fg=TEXT_COLOR,
            font=("Fredoka", 13, "bold")
        )
        # Not packed yet; toggle_compact_view manages its placement

        # Controls live in the right sidebar (below the collective tracker).
        self.controls_frame = tk.Frame(self.right_sidebar, bg=BG_COLOR)
        controls_frame = self.controls_frame
        controls_frame.grid(row=4, column=0, pady=(20, 10))
        controls_frame.grid_columnconfigure(0, weight=1)

        # Col 0 buttons
        self.icons_visible = True

        # Compact-mode clone: a separate frame in _kingdoms_col.
        self._captures_col_compact = tk.Frame(self._kingdoms_col, bg=BG_COLOR)
        tk.Label(self._captures_col_compact, text="Moon Cave", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 11, "bold")).pack(pady=(0, 2))
        self._left_captures_compact = CaptureRow(self._captures_col_compact)
        self._left_captures_compact.pack(pady=(0, 6))
        tk.Label(self._captures_col_compact, text="Cave Skip", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 11, "bold")).pack(pady=(0, 2))
        self._right_captures_compact = AbilityRow(self._captures_col_compact, app=self)
        self._right_captures_compact.pack()
        # Not packed yet; compact view toggle manages its placement

        # Toggleable rows — fixed rows so order never shifts
        # Row 0 – Cap Moon Count
        self.sidebar_cap_row = SimpleCounterRow(controls_frame, resource_path("assets/Cap.png"), self)
        self.sidebar_cap_row.grid(row=0, column=0, pady=(8, 0))
        self.sidebar_cap_row.grid_remove()

        # Row 1 – Cloud Moon Count
        self.cloud_row = SimpleCounterRow(controls_frame, resource_path("assets/Cloud.png"), self)
        self.cloud_enabled = False
        self.cloud_row.grid(row=1, column=0, pady=(4, 0))
        self.cloud_row.grid_remove()

        # Row 2 – Capture Count
        self.sidebar_star_row = SimpleCounterRow(controls_frame, resource_path("assets/Star.png"), self)
        self.sidebar_star_row.grid(row=2, column=0, pady=(4, 0))
        self.sidebar_star_row.grid_remove()

        # Row 3 – Ability Count
        self.sidebar_ability_row = SidebarAbilityRow(controls_frame, self)
        self.sidebar_ability_row.grid(row=3, column=0, pady=(4, 0))
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

        # Position Change OBS BG picker above the OBS overlay
        if hasattr(self, "_obs_bg_picker") and self._obs_bg_picker.winfo_exists():
            self._obs_bg_picker.update_idletasks()
            pw = self._obs_bg_picker.winfo_width()
            ph = self._obs_bg_picker.winfo_height()
            if self.obs and self.obs.winfo_exists():
                ox2 = self.obs.winfo_x()
                ow2 = self.obs.winfo_width()
                oy2 = self.obs.winfo_y()
                px = ox2 + (ow2 - pw) // 2
                py = max(0, oy2 - ph - 8)
                self._obs_bg_picker.geometry(f"+{px}+{py}")

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
        # CTkImage is required for CTkButton so images scale correctly on HighDPI displays.
        def _ctk_img(pil_img, size):
            return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)

        metro_img = resize_by_width(Image.open(resource_path("assets/Metro.png")).convert("RGBA"), WHITE_ICON_SIZE)
        metro_white = self._make_image_white(metro_img)
        self.metro_color_photo = _ctk_img(metro_img, (WHITE_ICON_SIZE, metro_img.height))
        self.metro_white_photo = _ctk_img(metro_white, (WHITE_ICON_SIZE, metro_white.height))

        def _tb(filename):
            img = resize_by_width(Image.open(resource_path(f"assets/{filename}")).convert("RGBA"), ICON_SIZE)
            return _ctk_img(img, (ICON_SIZE, img.height))

        # Load toolbar icons for Dark / Star / Cap / Cloud / Captures / Ability
        self.tb_dark_photo      = _tb("Moon.png")
        self.tb_star_photo      = _tb("Spark_pylon_Capture.png")
        self.tb_cap_photo       = _tb("Cap.png")
        self.tb_cloud_photo     = _tb("Cloud.png")
        self.tb_captures_photo  = _tb("Star.png")
        self.tb_ability_photo   = _tb("Dark.png")
        self.tb_moon_dark_photo = _tb("Moon_Dark.png")
        # Lock + Peace button uses unlock.png (showing unlocked = icons visible) and lock.png (hidden)
        self.tb_unlock_photo    = _tb("unlock.png")
        self.tb_lock_photo      = _tb("lock.png")
        # Moon Tick icon button — 40% larger than standard toolbar icons
        MOONTICK_ICON_SIZE = round(ICON_SIZE * 1.4)  # ~40px
        _moontick_img = resize_by_width(Image.open(resource_path("assets/moontickcap.png")).convert("RGBA"), MOONTICK_ICON_SIZE)
        self.tb_moontick_cap_photo = _ctk_img(_moontick_img, (MOONTICK_ICON_SIZE, _moontick_img.height))

        # Clock icon for the "Toggle Timer" button — drawn in code (no asset file
        # needed) and sized noticeably larger than the standard toolbar icons.
        def _make_clock_icon(size, color="#ffffff"):
            from PIL import ImageDraw
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            stroke = max(2, size // 11)
            pad = stroke
            draw.ellipse((pad, pad, size - pad, size - pad), outline=color, width=stroke)
            cx = cy = size / 2
            draw.line((cx, cy, cx, cy - size * 0.24), fill=color, width=stroke)
            draw.line((cx, cy, cx + size * 0.30, cy), fill=color, width=max(2, size // 13))
            return img

        CLOCK_ICON_SIZE = MOONTICK_ICON_SIZE  # same size as Moon Tick icon (~40px)
        _clock_img = _make_clock_icon(CLOCK_ICON_SIZE)
        self.tb_clock_photo = _ctk_img(_clock_img, (CLOCK_ICON_SIZE, CLOCK_ICON_SIZE))

        # Toolbar frame is no longer shown — buttons moved to Settings window
        # (images are still loaded above for use in Settings and toggle logic)
        pass

    # ------------------------------------------------------------------
    # Row placement helpers (req #4)
    # ------------------------------------------------------------------
    def _repack_special_rows(self):
        """
        Enforce exact row order in _kingdoms_col:
          Cap (if visible) → Cascade…Bowser → Dark (if visible) → Star (if visible)
        """
        first_kingdom = self.moon_rows[0]   # Cascade
        last_kingdom = self.moon_rows[-1]   # Bowser

        # --- Cap: directly above Cascade ---
        if self.cap_enabled:
            self.cap_row.pack_forget()
            self.cap_row.pack(before=first_kingdom, pady=5, anchor="w")
        else:
            self.cap_row.pack_forget()

        # --- Dark: directly below Bowser ---
        if self.dark_enabled:
            self.dark_row.pack_forget()
            self.dark_row.pack(after=last_kingdom, pady=5, anchor="w")
        else:
            self.dark_row.pack_forget()

        # --- Star: directly below Dark (if visible) else below Bowser ---
        if self.star_enabled:
            self.star_row.pack_forget()
            if self.dark_enabled:
                self.star_row.pack(after=self.dark_row, pady=5, anchor="w")
            else:
                self.star_row.pack(after=last_kingdom, pady=5, anchor="w")
        else:
            self.star_row.pack_forget()

        # Keep compact total label at the correct position
        if self.compact_view:
            self._repack_compact_total_label()

    # ------------------------------------------------------------------
    # Toggle handlers (req #4 + #6)
    # ------------------------------------------------------------------
    def toggle_cap_row(self):
        """Cap button: only shows/hides the Cap counter on the right sidebar."""
        self.sidebar_cap_visible = not self.sidebar_cap_visible
        if self.sidebar_cap_visible:
            self._reapply_settings_to_simple_row(self.sidebar_cap_row, "Cap")
        self._repack_sidebar_rows()
        self._notify_obs_sidebar_rows()
        self.save_state()
        self._refresh_settings_obs_optional_btn()

    def toggle_sidebar_captures_row(self):
        """Captures button: shows/hides the Spark_pylon counter on the right sidebar."""
        self.sidebar_captures_visible = not self.sidebar_captures_visible
        if self.sidebar_captures_visible:
            self.sidebar_star_row.apply_white_mode(self.white_icons)
            self.sidebar_star_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Star"))
        self._repack_sidebar_rows()
        self._notify_obs_sidebar_rows()

    def toggle_sidebar_ability_row(self):
        """Ability button: shows/hides the Long_Jump counter on the right sidebar."""
        self.sidebar_ability_visible = not self.sidebar_ability_visible
        if self.sidebar_ability_visible:
            self.sidebar_ability_row.apply_white_mode(self.white_icons)
            self.sidebar_ability_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Dark Side"))
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
        if self.cloud_enabled:
            self._reapply_settings_to_simple_row(self.cloud_row, "Cloud")
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
        if self.star_enabled:
            self._reapply_settings_to_simple_row(self.star_row, "Star")
        self._repack_special_rows()
        self._notify_obs_special_rows()
        self._reapply_all_settings_to_obs()
        self.save_state()
        self._refresh_settings_obs_optional_btn()

    def toggle_dark_row(self):
        self.dark_enabled = not self.dark_enabled
        self._repack_special_rows()
        if self.dark_enabled:
            # Reapply all current settings to the newly shown dark row
            self._reapply_settings_to_moon_row(self.dark_row, "Moon Kingdom")
        self._notify_obs_special_rows()
        self._reapply_all_settings_to_obs()
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
            # Reapply all settings so newly created OBS rows respect current toggles
            self._reapply_all_settings_to_obs()

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
    # Moon Tick Icon toggle
    # ------------------------------------------------------------------
    def toggle_moon_tick(self):
        """Show or hide the moontick icon next to each kingdom row."""
        self.moon_tick_enabled = not self.moon_tick_enabled
        # Standard kingdom rows
        for i, row in enumerate(self.moon_rows):
            kname = self._kingdom_names[i] if i < len(self._kingdom_names) else ""
            asset = KINGDOM_MOONTICK_ASSET.get(kname)
            row.apply_moontick(self.moon_tick_enabled, asset)
        # Dark row (Moon Kingdom)
        self.dark_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Moon Kingdom"))
        # Cap / Cloud / Star special simple counter rows (left column)
        self.cap_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Cap"))
        self.cloud_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Cloud"))
        self.star_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Star"))
        # Sidebar rows (right column): Cap, Star (Capture), Dark Side (Ability)
        self.sidebar_cap_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Cap"))
        self.sidebar_star_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Star"))
        self.sidebar_ability_row.apply_moontick(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET.get("Dark Side"))
        # OBS
        if self.obs and self.obs.winfo_exists():
            self.obs.set_moontick_visible(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET)
        # Update settings button
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_moon_tick_btn()

    # ------------------------------------------------------------------
    # Dynamic settings reapplication
    # All settings that can be toggled are re-applied any time a row is
    # shown/hidden so users never need to reapply manually.
    # ------------------------------------------------------------------
    def _reapply_settings_to_moon_row(self, row, kingdom_name):
        """Apply all current settings to a single MoonRow."""
        # Lock + Peace visibility
        if self.lock_peace_hidden:
            row.lock_icon.grid_remove()
            row.peace_icon.grid_remove()
        else:
            row.lock_icon.grid()
            row.peace_icon.grid()
        # White icons
        row.apply_white_mode(self.white_icons)
        # Moon tick
        asset = KINGDOM_MOONTICK_ASSET.get(kingdom_name)
        row.apply_moontick(self.moon_tick_enabled, asset)
        # Compact view
        row.apply_compact(self.compact_view)

    def _reapply_settings_to_simple_row(self, row, key):
        """Apply all current settings to a SimpleCounterRow."""
        row.apply_white_mode(self.white_icons)
        asset = KINGDOM_MOONTICK_ASSET.get(key)
        row.apply_moontick(self.moon_tick_enabled, asset)

    def _reapply_all_settings_to_obs(self):
        """After OBS is opened or an OBS row is added, push all current settings to it."""
        if not (self.obs and self.obs.winfo_exists()):
            return
        # Lock + peace
        self.obs.set_lock_peace_visible(not self.lock_peace_hidden)
        # Peace lock rows
        self.obs.set_peace_lock_visible(self.peace_lock_visible and not self.peace_lock_obs_hidden)
        # Icons (Moon Cave / Cave Skip)
        self.obs.set_icons_visible(self.icons_visible)
        # Moon total
        self.obs.set_moon_total_visible(not self.total_moon_tracker_hidden)
        # Moontick
        self.obs.set_moontick_visible(self.moon_tick_enabled, KINGDOM_MOONTICK_ASSET)
        # Timer
        self.obs.set_timer_visible(self.timer_visible)
        self._update_timer_display()

    def toggle_lock_peace(self):
        """Hide or show the Lock and Peace icons in all MoonRows (main + OBS)."""
        self.lock_peace_hidden = not self.lock_peace_hidden
        for row in self.moon_rows:
            if self.lock_peace_hidden:
                row.lock_icon.grid_remove()
                row.peace_icon.grid_remove()
            else:
                row.lock_icon.grid()
                row.peace_icon.grid()
        # Also hide/show dark_row lock+peace icons
        if self.lock_peace_hidden:
            self.dark_row.lock_icon.grid_remove()
            self.dark_row.peace_icon.grid_remove()
        else:
            self.dark_row.lock_icon.grid()
            self.dark_row.peace_icon.grid()
        # Update Settings button icon
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_lock_peace_btn()
        # Sync OBS
        if self.obs and self.obs.winfo_exists():
            self.obs.set_lock_peace_visible(not self.lock_peace_hidden)

    def toggle_total_moon_tracker(self):
        """Hide or show the Moon Tracker panel (title + total label + entry) in main and OBS.
        Notes and Settings buttons are always visible and unaffected."""
        self.total_moon_tracker_hidden = not self.total_moon_tracker_hidden
        if self.total_moon_tracker_hidden:
            self.tracker_frame.grid_remove()
        else:
            self.tracker_frame.grid()
        # Sync OBS
        if self.obs and self.obs.winfo_exists():
            self.obs.set_moon_total_visible(not self.total_moon_tracker_hidden)
        # Update Settings button label if open
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_moon_tracker_btn()

    # ------------------------------------------------------------------
    # Timer (manual duration counter — Toggle Timer in Settings)
    # ------------------------------------------------------------------
    TIMER_INTERVALS = [
        ("1s", 1), ("5s", 5), ("10s", 10), ("20s", 20),
        ("1m", 60), ("5m", 300), ("10m", 600), ("1h", 3600),
    ]

    def _format_timer(self, total_seconds):
        ms = int(round((total_seconds % 1) * 1000))
        h, rem = divmod(int(total_seconds), 3600)
        m, s = divmod(rem, 60)
        if self.timer_ms_enabled:
            if h:
                return f"{h}:{m:02d}:{s:02d}.{ms:03d}"
            return f"{m:02d}:{s:02d}.{ms:03d}"
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _build_timer_widgets(self):
        """Build the (initially hidden) Timer frame that lives below Settings in Main View."""
        small_font = ("Fredoka", 9)

        self.timer_frame_main = tk.Frame(self._buttons_frame, bg=BG_COLOR)

        self.timer_label_main = tk.Label(
            self.timer_frame_main, text=self._format_timer(self.timer_seconds),
            bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG
        )
        self.timer_label_main.pack(pady=(10, 4))

        self.timer_start_btn = ctk.CTkButton(
            self.timer_frame_main, text="Start Timer",
            command=self.toggle_timer_running,
            width=120, height=28, corner_radius=8, font=FONT_NORMAL,
            fg_color="#1f9d55", hover_color="#178a47", cursor="hand2"
        )
        self.timer_start_btn.pack(pady=(0, 4))

        # Reset Timer button — only visible when timer is running
        self.timer_reset_btn = ctk.CTkButton(
            self.timer_frame_main, text="Reset Timer",
            command=self._confirm_reset_timer,
            width=120, height=28, corner_radius=8, font=FONT_NORMAL,
            fg_color="#cc0000", hover_color="#aa0000", cursor="hand2"
        )
        # Not packed yet — shown only when timer is running

        btn_grid = tk.Frame(self.timer_frame_main, bg=BG_COLOR)
        btn_grid.pack()
        for col, (label, secs) in enumerate(self.TIMER_INTERVALS):
            tk.Label(btn_grid, text=label, bg=BG_COLOR, fg=TEXT_COLOR,
                     font=small_font).grid(row=0, column=col, padx=1)
            ctk.CTkButton(
                btn_grid, text="+", width=24, height=18, font=small_font,
                corner_radius=4, fg_color=TOOLBAR_BG, hover_color="#1a5fc8",
                command=lambda s=secs: self.adjust_timer(s)
            ).grid(row=1, column=col, padx=1, pady=1)
            ctk.CTkButton(
                btn_grid, text="-", width=24, height=18, font=small_font,
                corner_radius=4, fg_color="#444444", hover_color="#222222",
                command=lambda s=secs: self.adjust_timer(-s)
            ).grid(row=2, column=col, padx=1, pady=1)

        # Milliseconds row — hidden until toggle_timer_ms() shows it
        MS_INTERVALS = [
            ("100ms", 0.1), ("500ms", 0.5), ("1ms", 0.001),
        ]
        self._ms_intervals = MS_INTERVALS
        self._ms_btn_grid = tk.Frame(self.timer_frame_main, bg=BG_COLOR)
        for col, (label, ms) in enumerate(MS_INTERVALS):
            tk.Label(self._ms_btn_grid, text=label, bg=BG_COLOR, fg=TEXT_COLOR,
                     font=small_font).grid(row=0, column=col, padx=1)
            ctk.CTkButton(
                self._ms_btn_grid, text="+", width=36, height=18, font=small_font,
                corner_radius=4, fg_color=TOOLBAR_BG, hover_color="#1a5fc8",
                command=lambda s=ms: self.adjust_timer(s)
            ).grid(row=1, column=col, padx=1, pady=1)
            ctk.CTkButton(
                self._ms_btn_grid, text="-", width=36, height=18, font=small_font,
                corner_radius=4, fg_color="#444444", hover_color="#222222",
                command=lambda s=ms: self.adjust_timer(-s)
            ).grid(row=2, column=col, padx=1, pady=1)
        # Not packed yet — toggle_timer_ms() controls visibility

        # _add_ms_btn removed from main view; toggle is in Settings only

    def adjust_timer(self, delta_seconds):
        """Add or subtract a preset interval; the Timer can never go negative."""
        self.timer_seconds = max(0, self.timer_seconds + delta_seconds)
        self._update_timer_display()

    def toggle_timer_running(self):
        """Start or pause the auto-running timer (counts up once per second)."""
        self.timer_running = not self.timer_running
        if self.timer_running:
            if hasattr(self, "timer_start_btn"):
                self.timer_start_btn.configure(
                    text="Pause Timer", fg_color="#cc8400", hover_color="#a86c00"
                )
            # Show red Reset Timer button below Pause Timer
            if hasattr(self, "timer_reset_btn"):
                self.timer_reset_btn.pack(after=self.timer_start_btn, pady=(0, 4))
            self._timer_tick()
        else:
            if hasattr(self, "timer_start_btn"):
                self.timer_start_btn.configure(
                    text="Start Timer", fg_color="#1f9d55", hover_color="#178a47"
                )
            # Hide Reset Timer button when paused
            if hasattr(self, "timer_reset_btn"):
                self.timer_reset_btn.pack_forget()
            if self._timer_after_id is not None:
                self.after_cancel(self._timer_after_id)
                self._timer_after_id = None

    def _confirm_reset_timer(self):
        """Show a Yes/No popup asking if the user really wants to reset the timer."""
        popup = tk.Toplevel(self)
        popup.title("Confirm")
        popup.configure(bg=BG_COLOR)
        popup.geometry("320x130")
        popup.update_idletasks()
        popup.wait_visibility()
        popup.grab_set()
        tk.Label(popup, text="Are you sure you want to Reset the Timer?",
                 bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_NORMAL,
                 wraplength=280).pack(pady=(18, 10))
        btn_row = tk.Frame(popup, bg=BG_COLOR)
        btn_row.pack()
        def _do_reset():
            popup.destroy()
            # Stop timer if running
            if self.timer_running:
                self.toggle_timer_running()
            self.timer_seconds = 0
            self._update_timer_display()
        ctk.CTkButton(btn_row, text="Yes", font=FONT_NORMAL, corner_radius=10,
                      fg_color="#cc0000", hover_color="#aa0000", width=100,
                      command=_do_reset).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="No", font=FONT_NORMAL, corner_radius=10,
                      fg_color="#444444", hover_color="#222222", width=100,
                      command=popup.destroy).pack(side="left", padx=8)

    def toggle_timer_ms(self):
        """Show or hide the milliseconds +/- row in the Timer widget."""
        self.timer_ms_enabled = not self.timer_ms_enabled
        if self.timer_ms_enabled:
            self._ms_btn_grid.pack(pady=(4, 0))
        else:
            self._ms_btn_grid.pack_forget()
        # Refresh the display to add/remove ms component
        self._update_timer_display()
        # Update Settings window if open (to sync the Timer button appearance)
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            pass  # Settings "Toggle Timer" button label stays the same


    def _timer_tick(self):
        """Internal: advance the running timer by 10ms and reschedule."""
        if not self.timer_running:
            return
        self.timer_seconds += 0.01
        self._update_timer_display()
        self._timer_after_id = self.after(10, self._timer_tick)

    def _update_timer_display(self):
        text = self._format_timer(self.timer_seconds)
        if hasattr(self, "timer_label_main"):
            self.timer_label_main.config(text=text)
        if self.obs and self.obs.winfo_exists() and hasattr(self.obs, "timer_label_obs"):
            self.obs.timer_label_obs.config(text=text)

    def toggle_timer(self):
        """Show or hide the Timer below Settings (Main View) and below Cave Skip & Bowser (OBS)."""
        self.timer_visible = not self.timer_visible
        if self.timer_visible:
            self.timer_frame_main.pack(pady=(6, 0))
            self._update_timer_display()
        else:
            if self.timer_running:
                self.toggle_timer_running()
            self.timer_frame_main.pack_forget()
        if self.obs and self.obs.winfo_exists():
            self.obs.set_timer_visible(self.timer_visible)
        # Show/hide the "Add Milliseconds to Timer" button in Settings
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            sw = self.settings_window
            if hasattr(sw, "_timer_ms_btn") and sw._timer_ms_btn is not None:
                if self.timer_visible:
                    sw._timer_ms_btn.pack(fill="x", pady=3)
                else:
                    sw._timer_ms_btn.pack_forget()

    def toggle_compact_view(self):
        """Toggle Compact View: hide right sidebar, shrink non-kingdom UI, show inline total."""
        if not self.compact_view:
            # Enabling — show confirmation popup first
            popup = tk.Toplevel(self)
            popup.title("Compact View")
            popup.configure(bg=BG_COLOR)
            popup.geometry("320x130")
            popup.update_idletasks()
            popup.wait_visibility()
            popup.grab_set()
            tk.Label(popup, text="Are you sure you want to enable Compact View?",
                     bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_NORMAL,
                     wraplength=280).pack(pady=(18, 10))
            btn_row = tk.Frame(popup, bg=BG_COLOR)
            btn_row.pack()
            ctk.CTkButton(btn_row, text="Yes", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#1f6feb", hover_color="#1a5fc8", width=100,
                          command=lambda: [popup.destroy(), self._apply_compact_view(True)]
                          ).pack(side="left", padx=8)
            ctk.CTkButton(btn_row, text="No", font=FONT_NORMAL, corner_radius=10,
                          fg_color="#444444", hover_color="#222222", width=100,
                          command=popup.destroy).pack(side="left", padx=8)
        else:
            # Disabling — no confirmation needed
            self._apply_compact_view(False)

    def _apply_compact_view(self, on):
        """Internal: actually apply or remove Compact View."""
        self.compact_view = on

        # Show/hide right sidebar
        if on:
            self.right_sidebar.grid_remove()
        else:
            self.right_sidebar.grid()

        # Apply compact sizing to all MoonRows (standard + dark/Moon Kingdom)
        all_rows = list(self.moon_rows) + [self.dark_row]
        for row in all_rows:
            row.apply_compact(on)

        # Place or remove the compact total label
        self._compact_total_label.pack_forget()
        if on:
            self._update_compact_total_label()
            self._repack_compact_total_label()

        # In compact view: hide _captures_col from right_sidebar and show compact clone.
        # In normal view: _captures_col stays in right_sidebar row 2.
        if on and self.icons_visible:
            self._captures_col.grid_remove()
            self._repack_captures_compact()
        else:
            # Un-display compact clone
            try:
                self._captures_col_compact.pack_forget()
            except Exception:
                pass
            if self.icons_visible:
                self._captures_col.grid(row=2, column=0, pady=(8, 0))

        # When compact view is enabled, hide peace lock rows (they'd be clipped)
        if on and self.peace_lock_visible:
            for peace_row in self.peace_lock_rows:
                peace_row.grid_remove()
        elif not on and self.peace_lock_visible:
            kingdom_names = list(KINGDOM_PEACE_CAPTURES.keys())
            for i, peace_row in enumerate(self.peace_lock_rows):
                kname = kingdom_names[i] if i < len(kingdom_names) else ""
                if KINGDOM_PEACE_CAPTURES.get(kname):
                    peace_row.grid()

        # Update Settings window button label and button visibility
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_compact_view_btn()
            self.settings_window.apply_compact_buttons(on)

    def _repack_captures_compact(self):
        """In compact mode: show _captures_col_compact in left_column below compact total label."""
        if not self.compact_view or not self.icons_visible:
            return
        # Sync state from sidebar captures to compact clones before showing
        self._sync_compact_captures()
        self._captures_col_compact.pack(after=self._compact_total_label, pady=(4, 8))

    def _sync_compact_captures(self):
        """Copy toggle state from sidebar CaptureRow/AbilityRow icons to compact clones."""
        # CaptureRow: parabones, banzai, wire, bowser toggle icons
        for attr in ("parabones_icon", "banzai_icon", "wire_icon", "bowser_icon"):
            src = getattr(self.left_captures, attr, None)
            dst = getattr(self._left_captures_compact, attr, None)
            if src and dst and src.active != dst.active:
                dst.toggle()
        # AbilityRow: jump, cap, wall toggle icons
        for attr in ("jump_icon", "cap_icon", "wall_icon"):
            src = getattr(self.right_captures, attr, None)
            dst = getattr(self._right_captures_compact, attr, None)
            if src and dst and src.active != dst.active:
                dst.toggle()

    def _repack_compact_total_label(self):
        """Pack the compact total label right after dark_row if visible, else after last kingdom."""
        self._compact_total_label.pack_forget()
        if not self.compact_view:
            return
        if self.dark_enabled:
            self._compact_total_label.pack(after=self.dark_row, pady=(2, 4))
        else:
            last = self.moon_rows[-1]
            self._compact_total_label.pack(after=last, pady=(2, 4))

    def _update_compact_total_label(self):
        """Sync compact total label text with the collective tracker."""
        total = sum(row.count for row in self.moon_rows)
        if self.dark_enabled:
            total += self.dark_row.count
        target = self.collective_target_var.get().strip() or "?"
        self._compact_total_label.config(text=f"{total} / {target}")
        if self.compact_view:
            self.after(300, self._update_compact_total_label)

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
            self.open_obs_bg_picker()
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
            peace_lock_rows=self.peace_lock_rows,
            peace_lock_visible=self.peace_lock_visible and not self.peace_lock_obs_hidden,
            timer_visible=self.timer_visible,
            timer_text=self._format_timer(self.timer_seconds),
        )
        fade_in(self.obs)
        self.open_obs_bg_picker()
        # Push all current settings to the freshly opened OBS window
        self._reapply_all_settings_to_obs()

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

    def open_obs_bg_picker(self):
        """Open a small panel for choosing the OBS background colour."""
        # Reuse existing window if already open
        if hasattr(self, "_obs_bg_picker") and self._obs_bg_picker.winfo_exists():
            self._obs_bg_picker.lift()
            return

        win = tk.Toplevel(self)
        self._obs_bg_picker = win
        win.title("Change OBS BG")
        win.configure(bg=BG_COLOR)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW",
                     lambda: fade_out(win, on_done=win.destroy))

        outer = tk.Frame(win, bg=BG_COLOR)
        outer.pack(padx=16, pady=14)

        # ── Left column: preset colour buttons ──
        left = tk.Frame(outer, bg=BG_COLOR)
        left.grid(row=0, column=0, padx=(0, 20), sticky="n")

        tk.Label(left, text="Presets", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 13, "bold")).pack(pady=(0, 8))

        def _preset(color):
            if self.obs and self.obs.winfo_exists():
                self.obs.set_bg_color(color)

        # Red
        ctk.CTkButton(
            left, text="Red", width=100, height=34, corner_radius=10,
            fg_color="#cc0000", hover_color="#aa0000",
            font=FONT_NORMAL, command=lambda: _preset("#FF0000")
        ).pack(pady=4)

        # Green
        ctk.CTkButton(
            left, text="Green", width=100, height=34, corner_radius=10,
            fg_color="#2a7a2a", hover_color="#1f5c1f",
            font=FONT_NORMAL, command=lambda: _preset("#00FF00")
        ).pack(pady=4)

        # Blue
        ctk.CTkButton(
            left, text="Blue", width=100, height=34, corner_radius=10,
            fg_color="#1f4fa0", hover_color="#163880",
            font=FONT_NORMAL, command=lambda: _preset("#0000FF")
        ).pack(pady=4)

        # Orange
        ctk.CTkButton(
            left, text="Orange", width=100, height=34, corner_radius=10,
            fg_color="#b35a00", hover_color="#8a4400",
            font=FONT_NORMAL, command=lambda: _preset("#FF6600")
        ).pack(pady=4)

        # Magenta
        ctk.CTkButton(
            left, text="Magenta", width=100, height=34, corner_radius=10,
            fg_color="#8b008b", hover_color="#6a006a",
            font=FONT_NORMAL, command=lambda: _preset("#FF00FF")
        ).pack(pady=4)

        # Aqua
        ctk.CTkButton(
            left, text="Aqua", width=100, height=34, corner_radius=10,
            fg_color="#007a7a", hover_color="#005c5c",
            font=FONT_NORMAL, command=lambda: _preset("#00FFFF")
        ).pack(pady=4)

        # Info tooltip below Aqua
        info_frame = tk.Frame(left, bg=BG_COLOR)
        info_frame.pack(pady=(4, 0))

        info_lbl = tk.Label(
            info_frame, text="ℹ", bg=BG_COLOR, fg="#aaaaaa",
            font=("Fredoka", 15, "bold"), cursor="hand2"
        )
        info_lbl.pack()

        tooltip_win = [None]

        def _show_tip(event):
            if tooltip_win[0] and tooltip_win[0].winfo_exists():
                return
            tip = tk.Toplevel(win)
            tooltip_win[0] = tip
            tip.overrideredirect(True)
            tip.configure(bg="#333333")
            tip.attributes("-topmost", True)
            msg = "Recommended: Add a grey transparent\nbackground to the tracker in OBS so\nthe tracker is not obscured!"
            tk.Label(tip, text=msg, bg="#333333", fg="#ffffff",
                     font=("Fredoka", 11), justify="left",
                     padx=8, pady=6).pack()
            x = event.x_root + 10
            y = event.y_root + 10
            tip.geometry(f"+{x}+{y}")

        def _hide_tip(event):
            if tooltip_win[0] and tooltip_win[0].winfo_exists():
                tooltip_win[0].destroy()
                tooltip_win[0] = None

        info_lbl.bind("<Enter>", _show_tip)
        info_lbl.bind("<Leave>", _hide_tip)

        # ── Right column: custom hex entry ──
        right = tk.Frame(outer, bg=BG_COLOR)
        right.grid(row=0, column=1, sticky="n")

        tk.Label(right, text="Custom Colour", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Fredoka", 13, "bold")).pack(pady=(0, 8))

        tk.Label(right, text="Hex code  (e.g. #181818)", bg=BG_COLOR, fg="#aaaaaa",
                 font=("Fredoka", 11)).pack()

        hex_var = tk.StringVar(value="#")
        hex_entry = ctk.CTkEntry(right, width=130, height=34, corner_radius=10,
                                  textvariable=hex_var, font=FONT_NORMAL,
                                  placeholder_text="#RRGGBB")
        hex_entry.pack(pady=(4, 8))

        # Live preview swatch
        swatch = tk.Label(right, text="      ", bg=BG_COLOR,
                          relief="flat", width=6, height=1)
        swatch.pack(pady=(0, 6))

        def _update_swatch(*_):
            val = hex_var.get().strip()
            try:
                win.winfo_rgb(val)          # raises if invalid
                swatch.config(bg=val)
            except Exception:
                swatch.config(bg=BG_COLOR)

        hex_var.trace_add("write", _update_swatch)

        def _apply_custom():
            val = hex_var.get().strip()
            try:
                win.winfo_rgb(val)
                if self.obs and self.obs.winfo_exists():
                    self.obs.set_bg_color(val)
            except Exception:
                pass

        ctk.CTkButton(
            right, text="Apply", width=100, height=34, corner_radius=10,
            fg_color="#1f6feb", hover_color="#1a5fc8",
            font=FONT_NORMAL, command=_apply_custom
        ).pack()

        # Toggle OBS BG — below Apply
        ctk.CTkButton(
            right, text="Toggle OBS BG", width=100, height=34, corner_radius=10,
            fg_color="#2a7a2a", hover_color="#1f5c1f",
            font=FONT_NORMAL, command=self.toggle_obs_bg
        ).pack(pady=(8, 0))

        fade_in(win)
        # Position the picker above the OBS overlay once both exist
        self.after(50, self._position_obs_bg_picker)

    def _position_obs_bg_picker(self):
        """Position the Change OBS BG picker directly above the OBS overlay window."""
        picker = getattr(self, "_obs_bg_picker", None)
        if not (picker and picker.winfo_exists()):
            return
        obs = self.obs
        if not (obs and obs.winfo_exists()):
            return
        obs.update_idletasks()
        picker.update_idletasks()
        ox = obs.winfo_x()
        oy = obs.winfo_y()
        ow = obs.winfo_width()
        ph = picker.winfo_height()
        pw = picker.winfo_width()
        # Centre picker horizontally over OBS, sit just above it
        px = ox + (ow - pw) // 2
        py = max(0, oy - ph - 8)
        picker.geometry(f"+{px}+{py}")

    def toggle_peace_lock(self):
        """Show/hide the Peace Ability Lock capture icons next to each kingdom row."""
        self.peace_lock_visible = not self.peace_lock_visible
        kingdom_names = list(KINGDOM_PEACE_CAPTURES.keys())
        for i, peace_row in enumerate(self.peace_lock_rows):
            kname = kingdom_names[i] if i < len(kingdom_names) else ""
            tokens = KINGDOM_PEACE_CAPTURES.get(kname, [])
            if tokens:  # only show rows that have captures defined
                if self.peace_lock_visible:
                    peace_row.grid()
                else:
                    peace_row.grid_remove()
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_peace_lock_btn()
            self.settings_window.refresh_peace_lock_obs_btn()
        if self.obs and self.obs.winfo_exists():
            self.obs.set_peace_lock_visible(self.peace_lock_visible)

    def toggle_peace_lock_obs(self):
        """Show/hide the Peace Ability Lock rows in OBS only (does not affect main view)."""
        self.peace_lock_obs_hidden = not self.peace_lock_obs_hidden
        if self.obs and self.obs.winfo_exists():
            self.obs.set_peace_lock_visible(
                self.peace_lock_visible and not self.peace_lock_obs_hidden
            )
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_peace_lock_obs_btn()

    def toggle_capture_icons(self):
        """Show/hide Moon Cave, Cave Skip, Capture count & Ability count. Toggles button label too."""
        self.icons_visible = not self.icons_visible
        if self.icons_visible:
            if self.compact_view:
                # In compact mode, show compact clone in left_column instead of sidebar
                self._repack_captures_compact()
            else:
                self._captures_col.grid(row=2, column=0, pady=(8, 0))
            if self.sidebar_captures_visible:
                self.sidebar_star_row.grid()
            if self.sidebar_ability_visible:
                self.sidebar_ability_row.grid()
            self._hide_ability_text.set("Toggle Global Ability Lock")
        else:
            if self.compact_view:
                try:
                    self._captures_col_compact.pack_forget()
                except Exception:
                    pass
            else:
                self._captures_col.grid_remove()
            self.sidebar_star_row.grid_remove()
            self.sidebar_ability_row.grid_remove()
            self._hide_ability_text.set("Toggle Global Ability Lock")
        # Update Settings window button label if open
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_hide_ability_btn()
        self._refresh_settings_obs_optional_btn()
        if self.obs and self.obs.winfo_exists():
            self.obs.set_icons_visible(self.icons_visible)

    # ------------------------------------------------------------------
    # Reset all settings to defaults (used by RESET button)
    # ------------------------------------------------------------------
    def _reset_all_settings(self):
        """Reset all toggleable settings to their default state."""
        # Unhide Total Moon Tracker
        if self.total_moon_tracker_hidden:
            self.toggle_total_moon_tracker()
        # Disable White Icons
        if self.white_icons:
            self.toggle_white_icons()
        # Disable Moon Tick Icon
        if self.moon_tick_enabled:
            self.toggle_moon_tick()
        # Show Lock + Peace
        if self.lock_peace_hidden:
            self.toggle_lock_peace()
        # Hide Cap row
        if self.cap_enabled:
            self.toggle_cap_row()
        # Hide Cloud row
        if self.cloud_enabled:
            self.toggle_cloud_row()
        # Hide Dark (Moon Kingdom) row
        if self.dark_enabled:
            self.toggle_dark_row()
        # Show Ability Lock (icons visible)
        if not self.icons_visible:
            self.toggle_capture_icons()
        # Hide sidebar captures row
        if self.sidebar_captures_visible:
            self.toggle_sidebar_captures_row()
        # Hide sidebar ability row
        if self.sidebar_ability_visible:
            self.toggle_sidebar_ability_row()
        # Unhide optional OBS kingdoms
        if self.obs_optional_hidden:
            self.toggle_obs_optional()
        # Hide Peace Ability Lock
        if self.peace_lock_visible:
            self.toggle_peace_lock()
        # Unhide Peace Lock in OBS
        if self.peace_lock_obs_hidden:
            self.toggle_peace_lock_obs()
        # Disable Compact View
        if self.compact_view:
            self._apply_compact_view(False)
        # Hide Timer and reset its duration to 0
        if self.timer_visible:
            self.toggle_timer()
        self.timer_seconds = 0
        # Also reset milliseconds mode
        if self.timer_ms_enabled:
            self.toggle_timer_ms()
        self._update_timer_display()
        # Update Settings window if open
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.refresh_moon_tracker_btn()
            self.settings_window.refresh_white_icon_button()
            self.settings_window.refresh_moon_tick_btn()
            self.settings_window.refresh_lock_peace_btn()
            self.settings_window.refresh_compact_view_btn()
            self.settings_window.refresh_hide_ability_btn()
            self.settings_window.refresh_obs_optional_btn()
            self.settings_window.refresh_peace_lock_btn()
            self.settings_window.refresh_peace_lock_obs_btn()

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
        # Reset all peace lock capture icons (registry sync is handled inside reset())
        for peace_row in self.peace_lock_rows:
            peace_row.reset()
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

        # Strip the absolute runtime 'icon' path from each kingdom before saving.
        # resource_path() produces a temp path that changes every PyInstaller run,
        # so saving it breaks the Notes page on the next launch.
        loading_zones_safe = {}
        for kname, kdata in self.loading_zones.items():
            kdata_safe = {k: v for k, v in kdata.items() if k != "icon"}
            kdata_safe["zones"] = kdata["zones"]
            loading_zones_safe[kname] = kdata_safe

        data = {
            "loading_zones": loading_zones_safe,
            "cap_enabled": self.cap_enabled,
            "cloud_enabled": self.cloud_enabled,
            "star_enabled": self.star_enabled,
            "dark_enabled": self.dark_enabled,
            "moon_tick_enabled": self.moon_tick_enabled,
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
                # Only restore per-zone user state (note, icon, icon2, collapsed).
                # Never overwrite the kingdom-level 'icon' key — it holds an absolute
                # resource_path() value that changes each PyInstaller run, and restoring
                # a stale path is what causes the FileNotFoundError in the Notes page.
                saved_lz = data["loading_zones"]
                for kname, kdata in saved_lz.items():
                    if kname not in self.loading_zones:
                        continue
                    for zone, zdata in kdata.get("zones", {}).items():
                        if zone in self.loading_zones[kname]["zones"]:
                            self.loading_zones[kname]["zones"][zone].update(zdata)

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

            # Restore moon tick state — called after rows are packed so icons apply correctly
            if data.get("moon_tick_enabled", False):
                self.toggle_moon_tick()

        except Exception as e:
            print("Failed to load state:", e)


if __name__ == "__main__":
    TrackerApp().mainloop()
