"""Parsing/validation for safe, single-stroke global Windows hotkeys."""
from __future__ import annotations

MODS = {"ctrl": 0x0002, "control": 0x0002, "alt": 0x0001,
        "shift": 0x0004, "win": 0x0008, "meta": 0x0008}
NAMED = {"space": 0x20, "tab": 0x09, "home": 0x24, "end": 0x23,
         "insert": 0x2D, "delete": 0x2E, "up": 0x26, "down": 0x28,
         "left": 0x25, "right": 0x27, "pgup": 0x21, "pgdown": 0x22,
         "esc": 0x1B, "escape": 0x1B, "backspace": 0x08, "enter": 0x0D,
         "return": 0x0D}


def parse_hotkey(text: str) -> tuple[int, int] | None:
    if not isinstance(text, str) or not text.strip():
        return None
    parts = [p.strip().lower() for p in text.split("+")]
    if len(parts) != len(set(parts)) or not all(parts):
        return None
    mods = 0
    keys = []
    for part in parts:
        if part in MODS:
            if mods & MODS[part]:
                return None
            mods |= MODS[part]
        else:
            keys.append(part)
    if len(keys) != 1:
        return None
    key = keys[0]
    if len(key) == 1 and key.isascii() and key.isalnum():
        vk = ord(key.upper())
    elif key in NAMED:
        vk = NAMED[key]
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        n = int(key[1:])
        # F1, F2 and F3 are always reserved for macro Start / Pause / Stop.
        if n <= 3:
            return None
        vk = 0x70 + n - 1
    else:
        return None
    # Bare letters and numbers are allowed. Windows global shortcuts may
    # consume those keys while this application is open; show a UI warning.
    return (mods, vk)


def normalize_hotkey(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    parsed = parse_hotkey(value)
    if parsed is None:
        return ""
    mod, vk = parsed
    prefix = "+".join(label for bit, label in ((2, "Ctrl"), (1, "Alt"), (4, "Shift"), (8, "Meta")) if mod & bit)
    if 0x70 <= vk <= 0x87:
        key = f"F{vk-0x70+1}"
    elif vk in NAMED.values():
        key = next(k for k, v in NAMED.items() if v == vk).title()
    else:
        key = chr(vk)
    return f"{prefix}+{key}" if prefix else key
