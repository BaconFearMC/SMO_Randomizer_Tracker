import tkinter as tk
from PIL import Image, ImageTk
import customtkinter as ctk
import os
import sys
import json
import re

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("system")

STATE_FILE = "tracker_state.json"

FONT_NORMAL = ("Arial Rounded MT Bold", 14)
FONT_ZONES = font=('Arial Rounded MT Bold', 12)
FONT_BIG = ("Arial Rounded MT Bold", 16, "bold")

BG_COLOR = "#181818"
TEXT_COLOR = "#ffffff"

DEFAULT_SETTINGS = {
    "show_moon_total":   True,
    "moon_requirement":  124,
    "show_icon_colors":  True,
    "show_ability_lock": True,
    "show_captures":     True,
    "show_save_buttons": True,
    "obs_bg_color":      "#00FF00",
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

def make_image_white(img):
    """Return a copy of img with all non-transparent pixels turned white."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white.putalpha(a)
    return white

# -------------------------
# Clickable toggle image
# -------------------------
class ToggleImage(tk.Label):
    def __init__(self, parent, locked_img, unlocked_img, bg=BG_COLOR):
        self.locked = ImageTk.PhotoImage(resize_by_width(Image.open(locked_img), 20))
        self.unlocked = ImageTk.PhotoImage(resize_by_width(Image.open(unlocked_img), 20))

        super().__init__(parent, image=self.locked, cursor="hand2",  bg=bg)

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

        super().__init__(parent, image=self.locked, cursor="hand2",  bg=bg)

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

        # Lock & Peace toggles
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

        # Load images
        raw = resize_by_width(Image.open(kingdom_img_path), 40)
        self.kingdom_photo_color = ImageTk.PhotoImage(raw)
        self.kingdom_photo_white = ImageTk.PhotoImage(make_image_white(raw.copy()))
        self.kingdom_photo = self.kingdom_photo_color  # active version

        self.kingdom_label = tk.Label(self, image=self.kingdom_photo, bg=BG_COLOR, fg=TEXT_COLOR)
        self.kingdom_label.grid(row=0, column=3)

        ctk.CTkButton(self, text="-", command=self.decrement, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=6, padx=5)

        self.label = tk.Label(self, text="0 / ?", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BIG)
        self.label.grid(row=0, column=7, padx=5)

        ctk.CTkButton(self, text="+", command=self.increment, width=40, height=40, corner_radius=12, font=FONT_BIG).grid(row=0, column=8, padx=5)

        # Entry with StringVar — supports both manual-save and auto-save modes
        self.max_var = tk.StringVar()
        self.max_var.trace_add("write", self._on_max_change)
        self.entry = ctk.CTkEntry(self, width=50, height=35, corner_radius=10,
                                  textvariable=self.max_var, placeholder_text="?", font=FONT_BIG)
        self.entry.grid(row=0, column=9, padx=5)

        # Save button — shown when save-buttons setting is ON
        self.save_btn = ctk.CTkButton(self, text="Save", command=self.save_max,
                                      width=70, height=40, corner_radius=12, font=FONT_BIG)
        self.save_btn.grid(row=0, column=11, pady=2)

    # ── icon color ───────────────────────────────
    def set_icon_color(self, show_color: bool):
        """Switch kingdom image between colored and white versions."""
        self.kingdom_photo = (self.kingdom_photo_color if show_color
                              else self.kingdom_photo_white)
        self.kingdom_label.config(image=self.kingdom_photo)

    # ── save-button visibility ────────────────────
    def show_save_button(self):
        self.save_btn.grid(row=0, column=11, pady=2)

    def hide_save_button(self):
        self.save_btn.grid_remove()

    # ── auto-save trace ───────────────────────────
    def _on_max_change(self, *_):
        """When save buttons are hidden, auto-update max on every keystroke."""
        if getattr(self.app, "_loading", False):
            return
        if not self.app.settings.get("show_save_buttons", True):
            val = self.max_var.get()
            self.max_val = int(val) if val.isdigit() else None
            self.update_label()
            self.app.save_state()

    def update_label(self):
        max_display = self.max_val if self.max_val is not None else "?"
        self.label.config(text=f"{self.count} / {max_display}")

    def increment(self):
        self.count += 1
        self.update_label()

    def decrement(self):
        self.count = max(0, self.count - 1)
        self.update_label()

    def save_max(self):
        val = self.max_var.get()
        if val.isdigit():
            self.max_val = int(val)
            self.update_label()
            self.app.save_state()

    def reset(self):
        self.count   = 0
        self.max_val = None
        self.max_var.set("")
        self.update_label()
        self.lock_icon.reset()
        self.peace_icon.reset()


class CaptureRow(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)

        # Lock & Peace toggles
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

        # Lock & Peace toggles
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

        ctk.CTkButton(self, text="Notes", width=40, height=40, corner_radius=12,
                      font=FONT_NORMAL,
                      command=self.app.open_loading_zone_window).grid(row=1, column=0, padx=2)

        self.wall_icon = ToggleCaptures(
            self,
            resource_path("assets/Wall_Jump_Locked.png"),
            resource_path("assets/Wall_Jump.png")
        )
        self.wall_icon.grid(row=1, column=1, padx=2)

    def apply_icon_visibility(self, show: bool):
        """Show or hide ability-lock icons; Notes button position is unaffected."""
        if show:
            self.jump_icon.grid(row=0, column=0, padx=2)
            self.cap_icon.grid(row=0, column=1, padx=2)
            self.wall_icon.grid(row=1, column=1, padx=2)
        else:
            self.jump_icon.grid_remove()
            self.cap_icon.grid_remove()
            self.wall_icon.grid_remove()

    def reset(self):
        self.jump_icon.reset()
        self.cap_icon.reset()
        self.wall_icon.reset()

# -------------------------
# OBS Overlay Window
# -------------------------
class OBSMoonRow(tk.Frame):
    def __init__(self, parent, moon_row, bg_color):
        super().__init__(parent, bg=bg_color)

        self.moon_row = moon_row
        self.bg_color = bg_color

        # Lock
        self.lock_label = tk.Label(self, image=moon_row.lock_icon.locked, bg=bg_color)
        self.lock_label.grid(row=0, column=0, padx=2)

        # Peace
        self.peace_label = tk.Label(self, image=moon_row.peace_icon.locked, bg=bg_color)
        self.peace_label.grid(row=0, column=1, padx=2)

        # Kingdom
        self.kingdom_label = tk.Label(self, image=moon_row.kingdom_photo, bg=bg_color)
        self.kingdom_label.grid(row=0, column=2, padx=2)

        # Count text
        self.text = tk.Label(self, text="0 / ?", fg=TEXT_COLOR, bg=bg_color, font=FONT_BIG, width=5, anchor="center")
        self.text.grid(row=0, column=4)

        self.update()

    def update(self):
        # Update text
        max_val = self.moon_row.max_val if self.moon_row.max_val is not None else "?"
        self.text.config(text=f"{self.moon_row.count} / {max_val}")

        # Update icons
        self.lock_label.config(
            image=self.moon_row.lock_icon.unlocked
            if self.moon_row.lock_icon.active
            else self.moon_row.lock_icon.locked
        )

        self.peace_label.config(
            image=self.moon_row.peace_icon.unlocked
            if self.moon_row.peace_icon.active
            else self.moon_row.peace_icon.locked
        )

        self.kingdom_label.config(image=self.moon_row.kingdom_photo)

        # Refresh periodically
        self.after(200, self.update)

    def set_bg(self, bg_color):
        self.bg_color = bg_color
        self.config(bg=bg_color)
        for w in (self.lock_label, self.peace_label, self.kingdom_label, self.text):
            w.config(bg=bg_color)

class OBSCaptureColumn(tk.Frame):
    def __init__(self, parent, capture_row, bg_color):
        super().__init__(parent, bg=bg_color)
        self.icons  = [capture_row.parabones_icon, capture_row.banzai_icon, capture_row.wire_icon]
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
        for lbl in self.labels:
            lbl.config(bg=bg_color)

class OBSAbilityColumn(tk.Frame):
    def __init__(self, parent, ability_row, bg_color):
        super().__init__(parent, bg=bg_color)
        self.icons  = [ability_row.jump_icon, ability_row.cap_icon, ability_row.wall_icon]
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
        for lbl in self.labels:
            lbl.config(bg=bg_color)

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
            font=("Arial", 14, "bold"),
            anchor="center"
        )
        # self.pack(fill="x", padx=8, pady=(10, 4))

    def set_bg(self, bg_color):
        self.config(bg=bg_color)

class OBSWindow(tk.Toplevel):
    def __init__(self, parent, moon_rows, capture_row, ability_row):
        super().__init__(parent)
        self.app = parent          # TrackerApp reference
        self.moon_rows_ref = moon_rows       # for total calculation

        self.title("OBS Overlay")
        self.attributes("-topmost", True)
        self.geometry("350x550")

        self.bg_mode = "dark" 
        self.bg_color = BG_COLOR
        self.config(bg=self.bg_color)

        self.main = tk.Frame(self, bg=self.bg_color)
        self.main.pack(fill="both", expand=True)

        # ── Left column — moon rows ──────────────────
        self.moon_frame = tk.Frame(self.main, bg=self.bg_color)
        self.moon_frame.grid(row=0, column=0, padx=8, sticky="n")

        self.moon_obs_rows = []
        for row in moon_rows:
            obs_row = OBSMoonRow(self.moon_frame, row, self.bg_color)
            obs_row.pack(pady=2, padx=6, anchor="w")
            self.moon_obs_rows.append(obs_row)

        # ── Right column ─────────────────────────────
        self.right = tk.Frame(self.main, bg=self.bg_color)
        self.right.grid(row=0, column=1, padx=12, sticky="n")

        # Capture section (Moon Cave header + icons)
        self.capture_section = tk.Frame(self.right, bg=self.bg_color)
        self.capture_section.pack()

        self.moon_cave_header = SectionHeader(self.capture_section, "Moon Cave")
        self.moon_cave_header.pack(fill="x", padx=8, pady=(10, 4))

        self.capture_col = OBSCaptureColumn(self.capture_section, capture_row, self.bg_color)
        self.capture_col.pack(pady=(0, 20))

        # Ability section (Cave Skip header + icons)
        self.ability_section = tk.Frame(self.right, bg=self.bg_color)
        self.ability_section.pack()

        self.cave_skip_header = SectionHeader(self.ability_section, "Cave Skip")
        self.cave_skip_header.pack(fill="x", padx=8, pady=(10, 4))

        self.ability_col = OBSAbilityColumn(self.ability_section, ability_row, self.bg_color)
        self.ability_col.pack(pady=(0, 20))

        # Bowser row
        self.bowser_row = OBSBowserRow(self.right, capture_row, self.bg_color)
        self.bowser_row.pack()

        # Total moon count label (bottom of right column)
        req = self.app.settings.get("moon_requirement", 124)
        self.moon_total_label = tk.Label(
            self.right, text=f"0 / {req}",
            fg=TEXT_COLOR, bg=self.bg_color, font=FONT_BIG)
        self.moon_total_label.pack(pady=(10, 4))

        # Start total update loop
        self._update_total()

        # Apply initial settings visibility
        self._repack_right_column()

    # ── total update loop ─────────────────────────
    def _update_total(self):
        total = sum(row.count for row in self.moon_rows_ref)
        req = self.app.settings.get("moon_requirement", 124)
        self.moon_total_label.config(text=f"{total} / {req}")
        self.after(200, self._update_total)

    # ── right-column visibility ───────────────────
    def _repack_right_column(self):
        """Unpack everything, then repack only what current settings say to show."""
        s = self.app.settings
        self.capture_section.pack_forget()
        self.ability_section.pack_forget()
        self.bowser_row.pack_forget()
        self.moon_total_label.pack_forget()

        if s.get("show_captures", True):
            self.capture_section.pack()
        if s.get("show_ability_lock", True):
            self.ability_section.pack()
        if s.get("show_captures", True):
            self.bowser_row.pack()
        if s.get("show_moon_total", True):
            self.moon_total_label.pack(pady=(10, 4))

    def apply_moon_total_visibility(self, _show):
        self._repack_right_column()

    def apply_capture_visibility(self, _show):
        self._repack_right_column()

    def apply_ability_visibility(self, _show):
        self._repack_right_column()

    def toggle_bg(self):
        if self.bg_mode == "dark":
            self.bg_mode  = "green"
            new_color = self.app.settings.get("obs_bg_color", "#00FF00")
        else:
            self.bg_mode  = "dark"
            new_color = BG_COLOR
        self.bg_color = new_color
        self._set_all_bg(new_color)

    def _set_all_bg(self, color: str):
        self.config(bg=color)
        self.main.config(bg=color)
        self.moon_frame.config(bg=color)
        self.right.config(bg=color)
        self.capture_section.config(bg=color)
        self.ability_section.config(bg=color)
        for row in self.moon_obs_rows:
            row.set_bg(color)
        self.moon_cave_header.set_bg(color)
        self.capture_col.set_bg(color)
        self.cave_skip_header.set_bg(color)
        self.ability_col.set_bg(color)
        self.bowser_row.set_bg(color)
        self.moon_total_label.config(bg=color)

# -------------------------
# Loading Zone Window
# -------------------------
class LoadingZoneWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Loading Zone Notes")
        self.geometry("800x800")
        # self.attributes("-fullscreen", True)
        self.configure(bg=BG_COLOR)

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

    def build_columns(self):
        self.columns = {}

        for col, (kingdom, data) in enumerate(self.parent.loading_zones.items()):
            frame = KingdomColumn(
                self.content,
                kingdom,
                data,
                self.parent
            )
            frame.grid(row=0, column=col, padx=20, sticky="n")
            self.columns[kingdom] = frame

    def bind_events(self):
        # Windows / macOS
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        # Linux
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

        self.visible = tk.BooleanVar(value=True)

        # Header
        header = tk.Frame(self, bg=BG_COLOR)
        header.pack()

        icon = ImageTk.PhotoImage(
            resize_by_height(Image.open(data["icon"]), 20)
        )
        self.icon = icon  # keep ref

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
            for zone in zones[col_idx : col_idx + MAX_PER_COL]:
                LoadingZoneRow(col_frame, name, zone, data, app).pack(anchor="w", pady=4)

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

        self.icon_img = ImageTk.PhotoImage(
            resize_by_height(Image.open(resource_path("assets/Moon.png")), 18)
        )
        self.dark_icon = ImageTk.PhotoImage(
            resize_by_height(Image.open(resource_path("assets/Moon_Dark.png")), 18)
        )

        top = tk.Frame(self, bg=BG_COLOR)
        top.pack(anchor="w")


        
        self.icon_label = tk.Label(top, image=self.icon_img, bg=BG_COLOR, cursor="hand2")
        self.icon_label.pack(side="left")
        self.icon_label.bind("<Button-1>", lambda e: self.open_icon_picker(self.icon_label))
        self.icon_photo = self.icon_img

        # elif self.num > 1:
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

        # Restore collapsed state
        if self.state["collapsed"]:
            self.name_label.config(fg="gray")
            self.text.pack_forget()
            self.icon_label.config(image=self.dark_icon)

        # Restore icon
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

        # Position near the mouse
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        win.geometry(f"+{x}+{y}")

        win.focus_force()
        win.bind("<FocusOut>", lambda e: win.destroy())

        icons = ["Cascade.png", "Sand.png", "Lake.png", "Wooded.png", "Lost.png", "Metro.png", "Snow.png", "Seaside.png", "Luncheon.png", "Ruin.png", "Bowser.png", "Cap.png", "Dark.png", "Star.png", "Moon.png", "Moon_Dark.png", "checkmark.png", "xmark.png"]
        win.images = []  # prevent GC

        for idx, icon in enumerate(icons):
            img = ImageTk.PhotoImage(resize_by_height(Image.open(resource_path(f"assets/{icon}")),20))

            lbl = tk.Label(win, image=img, bg="#222222", cursor="hand2")
            row = idx // 6
            col = idx % 6
            lbl.grid(row=row, column=col, padx=4, pady=4)

            win.images.append(img)

            lbl.bind("<Button-1>", lambda e, i=icon, im=img: self.set_icon(i, im, target_label, win))

    def set_icon(self, icon_name, image, target_label, win):
        target_label.config(image=image)
        if target_label == self.icon_label:
            self.icon_photo    = image
            self.state["icon"] = icon_name
        elif hasattr(self, "icon_label2") and target_label == self.icon_label2:
            self.icon_photo2    = image
            self.state["icon2"] = icon_name
        self.app.save_state()
        win.destroy()

# -------------------------
# Settings Window
# -------------------------
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent

        self.title("Settings")
        self.geometry("420x370")
        self.configure(bg=BG_COLOR)
        self.attributes("-topmost", True)

        self._build()

    def _build(self):
        s = self.app.settings

        ctk.CTkLabel(self, text="⚙  Settings", font=FONT_BIG).pack(pady=(16, 10))

        self._toggle_row("Toggle Total Moon Count", "show_moon_total",   s["show_moon_total"])
        self._toggle_row("Toggle Icon Colors",       "show_icon_colors",  s["show_icon_colors"])
        self._toggle_row("Toggle Ability Lock",      "show_ability_lock", s["show_ability_lock"])
        self._toggle_row("Toggle Captures",          "show_captures",     s["show_captures"])
        self._toggle_row("Toggle Save Buttons",      "show_save_buttons", s["show_save_buttons"])

        self._text_save_row(
            "Total Moon Requirement", "moon_requirement",
            str(s["moon_requirement"]), "124",
            self._validate_int,
        )
        self._text_save_row(
            "OBS BG Color", "obs_bg_color",
            s["obs_bg_color"], "#00FF00",
            self._validate_hex,
        )

    # ── row builders ─────────────────────────────
    def _toggle_row(self, label: str, key: str, initial: bool):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=4)

        ctk.CTkLabel(row, text=label, font=FONT_NORMAL, anchor="w").pack(
            side="left", fill="x", expand=True)

        var = tk.BooleanVar(value=initial)
        sw  = ctk.CTkSwitch(row, text="", variable=var,
                             onvalue=True, offvalue=False,
                             command=lambda k=key, v=var: self._on_toggle(k, v))
        sw.pack(side="right")
        sw.select() if initial else sw.deselect()

    def _text_save_row(self, label: str, key: str, current: str,
                       placeholder: str, validator):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=4)

        ctk.CTkLabel(row, text=label, font=FONT_NORMAL, anchor="w").pack(
            side="left", fill="x", expand=True)

        entry = ctk.CTkEntry(row, width=100, height=32, corner_radius=8,
                             placeholder_text=placeholder, font=FONT_NORMAL)
        entry.pack(side="left", padx=(0, 4))
        entry.insert(0, current)

        ctk.CTkButton(row, text="Save", width=60, height=32, corner_radius=8,
                      font=FONT_NORMAL,
                      command=lambda e=entry, k=key, v=validator: self._on_save(k, e, v)
                      ).pack(side="left")

    # ── handlers ─────────────────────────────────
    def _on_toggle(self, key: str, var: tk.BooleanVar):
        self.app.settings[key] = var.get()
        self.app.apply_all_settings()
        self.app.save_state()

    def _on_save(self, key: str, entry: ctk.CTkEntry, validator):
        result = validator(entry.get().strip())
        if result is not None:
            self.app.settings[key] = result
            self.app.apply_all_settings()
            self.app.save_state()

    # ── validators ───────────────────────────────
    @staticmethod
    def _validate_int(val: str):
        if val.isdigit():
            n = int(val)
            return n if n > 0 else None
        return None

    @staticmethod
    def _validate_hex(val: str):
        return val if re.match(r"^#[0-9A-Fa-f]{6}$", val) else None
    
# -------------------------
# Main App
# -------------------------
class TrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Moon Tracker")
        self.geometry("450x800")

        self.configure(bg=BG_COLOR)
        self.settings = dict(DEFAULT_SETTINGS)
        self._loading  = False
        frame = tk.Frame(self, bg=BG_COLOR)
        label = tk.Label(self, bg=BG_COLOR, fg=TEXT_COLOR)

        # Icons
        icon_frame = tk.Frame(self, bg=BG_COLOR)
        icon_frame.pack(pady=15)

        # Moon row
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
                    "Employees": {"num": 1}, #Shop crouch zone
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

        self.moon_rows = []
        for name, (k_img, m_img) in KINGDOMS.items():
            row = MoonRow(self, k_img, app=self)
            row.pack(pady=5)
            self.moon_rows.append(row)

        self.moon_rows[-1].pack(pady=5)

        controls_frame = tk.Frame(self, bg=BG_COLOR)
        controls_frame.pack(pady=15, fill="x")
        controls_frame.grid_columnconfigure(1, weight=1)

        self.left_captures = CaptureRow(controls_frame)
        self.left_captures.grid(row=0, column=0, padx=15)

        button_frame = tk.Frame(controls_frame, bg=BG_COLOR)
        button_frame.grid(row=0, column=1, padx=20)

        self.obs = None
        self._settings_window = None

        ctk.CTkButton(button_frame, text="Open OBS Overlay", command=self.open_obs, font=FONT_NORMAL).pack(pady=5)
        ctk.CTkButton(button_frame, text="Toggle OBS BG", command=self.toggle_obs_bg, font=FONT_NORMAL).pack()
        ctk.CTkButton(button_frame, text="Clear", command=self.reset_all_moons, font=FONT_NORMAL).pack(pady=5)
        ctk.CTkButton(button_frame, text="Settings", command=self.open_settings, font=FONT_NORMAL).pack()

        self.right_captures = AbilityRow(controls_frame, app=self)
        self.right_captures.grid(row=0, column=2, padx=15)

        self.load_state()
        self.apply_all_settings()

    def open_obs(self):
        if not self.obs or not self.obs.winfo_exists():
            self.obs = OBSWindow(self, self.moon_rows, self.left_captures, self.right_captures)

    def open_loading_zone_window(self):
        if not hasattr(self, "lz_window") or not self.lz_window.winfo_exists():
            self.lz_window = LoadingZoneWindow(self)

    def toggle_obs_bg(self):
        if self.obs and self.obs.winfo_exists():
            self.obs.toggle_bg()

    # ── Settings window ──────────────────────────
    def open_settings(self):
        if self._settings_window is None or not self._settings_window.winfo_exists():
            self._settings_window = SettingsWindow(self)
        else:
            self._settings_window.focus()

    def apply_all_settings(self):
        """Apply every setting to the UI; called on load and on any settings change."""
        s = self.settings
        self.apply_icon_colors(s["show_icon_colors"])
        self.apply_save_buttons(s["show_save_buttons"])
        self._apply_tracker_capture_visibility(s["show_captures"])
        self._apply_tracker_ability_visibility(s["show_ability_lock"])
        if self.obs and self.obs.winfo_exists():
            self.obs.apply_moon_total_visibility(s["show_moon_total"])
            self.obs.apply_capture_visibility(s["show_captures"])
            self.obs.apply_ability_visibility(s["show_ability_lock"])
            # If OBS is currently showing green, immediately apply any new custom color
            if self.obs.bg_mode == "green":
                new_color = s.get("obs_bg_color", "#00FF00")
                self.obs.bg_color = new_color
                self.obs._set_all_bg(new_color)

    def apply_icon_colors(self, show: bool):
        for row in self.moon_rows:
            row.set_icon_color(show)

    def apply_save_buttons(self, show: bool):
        for row in self.moon_rows:
            row.show_save_button() if show else row.hide_save_button()

    def _apply_tracker_capture_visibility(self, show: bool):
        if show:
            self.left_captures.grid(row=0, column=0, padx=15)
        else:
            self.left_captures.grid_remove()

    def _apply_tracker_ability_visibility(self, show: bool):
        self.right_captures.apply_icon_visibility(show)

    # ── Reset ────────────────────────────────────
    def reset_all_moons(self):
        # Use _loading to suppress auto-saves triggered by max_var.set("")
        self._loading = True
        try:
            for row in self.moon_rows:
                row.reset()
            self.left_captures.reset()
            self.right_captures.reset()
            for kingdom in self.loading_zones.values():
                for zone in kingdom["zones"].values():
                    zone["note"]      = ""
                    zone["icon"]      = "Moon.png"
                    zone["icon2"]     = "Moon.png"
                    zone["collapsed"] = False
        finally:
            self._loading = False

        # Preserve settings in the state file; clear everything else
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"settings": self.settings}, f, indent=2)
        except Exception as e:
            print("Failed to save cleared state:", e)
# -------------------------
# Save State
# -------------------------
    def save_state(self):
        data = {
            "settings":      self.settings,
            "loading_zones": self.loading_zones,
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

            # Merge saved settings; missing keys fall back to defaults
            if "settings" in data:
                for key, default in DEFAULT_SETTINGS.items():
                    self.settings[key] = data["settings"].get(key, default)

            if "loading_zones" in data:
                self.loading_zones = data["loading_zones"]

            self._loading = True
            try:
                for row, saved in zip(self.moon_rows, data.get("moons", [])):
                    row.count   = saved.get("count", 0)
                    row.max_val = saved.get("max")
                    # Update the entry display without triggering auto-save
                    row.max_var.set(str(row.max_val) if row.max_val is not None else "")

                    lock = saved.get("lock", False)
                    row.lock_icon.active = lock
                    row.lock_icon.config(
                        image=row.lock_icon.unlocked if lock else row.lock_icon.locked)

                    peace = saved.get("peace", False)
                    row.peace_icon.active = peace
                    row.peace_icon.config(
                        image=row.peace_icon.unlocked if peace else row.peace_icon.locked)

                    row.update_label()
            finally:
                self._loading = False

        except Exception as e:
            print("Failed to load state:", e)
            self._loading = False

if __name__ == "__main__":
    TrackerApp().mainloop()
