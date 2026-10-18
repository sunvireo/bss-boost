"""Portable model validation, preset management, and atomic JSON persistence."""
from __future__ import annotations
import copy
import json
import os
import tempfile
import uuid
from pathlib import Path

ITEMS = [
    "Empty", "Gumdrops", "Jelly Beans", "Stingers", "Coconuts", "Glitter",
    "Field Dice", "Smooth Dice", "Loaded Dice", "Super Smoothie", "Tropical Drink",
    "Purple Potion", "Glue", "Oil", "Enzymes", "Extracts", "Blue Extract",
    "Red Extract", "Snowflakes", "Marshmallow Bee", "Ticket", "Other",
]


def make_slot(key: int) -> dict:
    # First launch is genuinely blank: no example items or activated schedules.
    # Intervals are stored only as an editor fallback until a user assigns an item.
    return {"key": key, "item": "Empty", "enabled": False, "overlay_visible": True, "interval": 10.0, "delay": 0.0}


def make_alarm(name: str, duration: int, repeat: bool = False) -> dict:
    return {"id": uuid.uuid4().hex, "name": name, "duration": duration,
            "enabled": True, "overlay": True, "repeat": repeat,
            "alert_mode": "Sound", "keybind": ""}


def default_profile() -> dict:
    return {"slots": [make_slot(i) for i in range(1, 8)], "alarms": []}


def default_data() -> dict:
    return {"schema": 2, "active_profile": "Default", "profiles": {"Default": default_profile()},
            "settings": {"target_title": "Roblox", "focus_only": True,
                         "overlay_visible": True, "overlay_corner": "Bottom center",
                         "overlay_opacity": 93, "hotkeys": True, "animations": True,
                         "theme": "Light", "start_alarms_with_macro": False,
                         "overlay_hotbar_visible": True, "overlay_alarms_visible": True,
                         "overlay_countdowns": False, "overlay_spacing": 22,
                         "overlay_scale": 100, "overlay_x": -1, "overlay_y": -1,
                         "alarm_overlay_x": -1, "alarm_overlay_y": -1,
                         }}


def clamp_number(value, default, low, high):
    try:
        val = float(value)
        if val != val or val in (float("inf"), float("-inf")):
            return default
        return max(low, min(high, val))
    except (ValueError, TypeError, OverflowError):
        return default


def validated_slot(raw: dict, key: int) -> dict:
    base = make_slot(key)
    if not isinstance(raw, dict):
        return base
    item = str(raw.get("item", base["item"]))[:65].strip()
    base.update(item=item or "Empty",
                enabled=raw.get("enabled") is True,
                overlay_visible=raw.get("overlay_visible", True) is True,
                interval=round(clamp_number(raw.get("interval"), base["interval"], .1, 86400), 2),
                delay=round(clamp_number(raw.get("delay"), 0, 0, 86400), 2))
    return base


def validated_alarm(raw: dict) -> dict:
    base = make_alarm("Alarm", 60)
    if not isinstance(raw, dict):
        return base
    rawid = raw.get("id")
    base["id"] = str(rawid)[:64] if isinstance(rawid, str) and rawid else uuid.uuid4().hex
    base["name"] = str(raw.get("name", "Alarm"))[:70].strip() or "Alarm"
    base["duration"] = int(clamp_number(raw.get("duration"), 60, 1, 3599999))
    for field in ("enabled", "overlay", "repeat"):
        base[field] = raw.get(field, base[field]) is True
    # v1 stored a sound boolean; continue loading all existing user presets.
    mode = raw.get("alert_mode", "Sound" if raw.get("sound") else "Off")
    base["alert_mode"] = mode if mode in ("Off", "Sound", "Voice") else "Off"
    from .hotkey_codec import normalize_hotkey
    base["keybind"] = normalize_hotkey(raw.get("keybind", ""))
    return base


def validated_profile(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return default_profile()
    incoming = raw.get("slots", [])
    known = {}
    if isinstance(incoming, list):
        for candidate in incoming:
            if isinstance(candidate, dict):
                try:
                    key = int(candidate.get("key", -1))
                except (ValueError, TypeError, OverflowError):
                    continue
                if 1 <= key <= 9 and key not in known:
                    known[key] = candidate
    # 7-slot UI, with 1..7 matching the Roblox example.
    slots = [validated_slot(known.get(i), i) for i in range(1, 8)]
    alarms = []
    ids = set()
    incoming_alarms = raw.get("alarms", [])
    for candidate in (incoming_alarms if isinstance(incoming_alarms, list) else [])[:100]:
        alarm = validated_alarm(candidate)
        if alarm["id"] in ids:
            alarm["id"] = uuid.uuid4().hex
        ids.add(alarm["id"])
        alarms.append(alarm)
    return {"slots": slots, "alarms": alarms}


def validated_data(raw) -> dict:
    base = default_data()
    if not isinstance(raw, dict) or raw.get("schema") != 2:
        return base
    candidate_profiles = raw.get("profiles", {})
    if isinstance(candidate_profiles, dict):
        valid = {}
        for name, obj in list(candidate_profiles.items())[:50]:
            if isinstance(name, str) and name.strip() and isinstance(obj, dict):
                valid[name[:50]] = validated_profile(obj)
        if valid:
            base["profiles"] = valid
    current = raw.get("active_profile")
    if current in base["profiles"]:
        base["active_profile"] = current
    else:
        base["active_profile"] = next(iter(base["profiles"]))
    settings = raw.get("settings", {})
    if isinstance(settings, dict):
        for key in ("focus_only", "overlay_visible", "hotkeys", "animations", "start_alarms_with_macro",
                    "overlay_hotbar_visible", "overlay_alarms_visible", "overlay_countdowns"):
            if isinstance(settings.get(key), bool):
                base["settings"][key] = settings[key]
        for key, choices in (("overlay_corner", ["Top left", "Top center", "Top right", "Bottom left", "Bottom center", "Bottom right"]),
                             ("theme", ["Light", "Dark"])):
            if settings.get(key) in choices:
                base["settings"][key] = settings[key]
        if isinstance(settings.get("target_title"), str):
            base["settings"]["target_title"] = settings["target_title"][:90]
        base["settings"]["overlay_opacity"] = int(clamp_number(
            settings.get("overlay_opacity"), 93, 40, 100))
        # Migration: previously the overlay had only one visibility toggle.
        if "overlay_hotbar_visible" not in settings:
            base["settings"]["overlay_hotbar_visible"] = base["settings"]["overlay_visible"]
        if "overlay_alarms_visible" not in settings:
            base["settings"]["overlay_alarms_visible"] = base["settings"]["overlay_visible"]
        base["settings"]["overlay_scale"] = int(clamp_number(settings.get("overlay_scale"), 100, 60, 150))
        raw_spacing = settings.get("overlay_spacing", 22)
        if raw_spacing == 39:
            raw_spacing = 22
        base["settings"]["overlay_spacing"] = int(clamp_number(raw_spacing, 22, 0, 80))
        for axis in ("overlay_x", "overlay_y", "alarm_overlay_x", "alarm_overlay_y"):
            base["settings"][axis] = int(clamp_number(settings.get(axis), -1, -1, 20000))
    return base


def config_path() -> Path:
    if os.name == "nt":
        root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if root:
            return Path(root) / "BssBooster" / "booster_settings.json"
    return Path.home() / ".bss_booster" / "booster_settings.json"


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else config_path()
        self.data = default_data()
        self.load()

    @property
    def profile(self) -> dict:
        return self.data["profiles"][self.data["active_profile"]]

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def load(self) -> None:
        try:
            if self.path.exists():
                self.data = validated_data(json.loads(self.path.read_text(encoding="utf-8")))
        except (ValueError, OSError, UnicodeError):
            # Save existing corrupt file untouched until a user changes a setting.
            self.data = default_data()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Same-directory temp file, then atomic replace. No truncated config on crash.
        fd, tmp = tempfile.mkstemp(prefix=".booster_", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(self.data, out, indent=2, ensure_ascii=False)
                out.write("\n")
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def clone_profile(self, name: str) -> bool:
        name = name.strip()[:50]
        if not name or name in self.data["profiles"]:
            return False
        self.data["profiles"][name] = copy.deepcopy(self.profile)
        self.data["active_profile"] = name
        self.save()
        return True


def human_time(seconds: float) -> str:
    val = max(0, int(seconds + 0.999))
    h, remainder = divmod(val, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
