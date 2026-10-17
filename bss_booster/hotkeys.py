"""Windows RegisterHotKey for global macro actions and per-alarm reset buttons."""
from __future__ import annotations
import ctypes
import os
from PySide6.QtCore import QAbstractNativeEventFilter
from .hotkey_codec import parse_hotkey


class WindowsHotkeys(QAbstractNativeEventFilter):
    MACRO = {9001: "start", 9002: "pause", 9003: "stop"}

    def __init__(self, handler, alarm_handler):
        super().__init__()
        self.handler = handler
        self.alarm_handler = alarm_handler
        self.registered: list[int] = []
        self.alarms: dict[int, str] = {}
        self.failures: list[str] = []

    def register(self, alarms: list[dict]):
        self.failures.clear()
        if os.name != "nt":
            return
        user32 = ctypes.windll.user32
        used = {(0, key) for key in (0x70, 0x71, 0x72)}
        for ident, key in ((9001, 0x70), (9002, 0x71), (9003, 0x72)):
            if user32.RegisterHotKey(None, ident, 0x4000, key):
                self.registered.append(ident)
            else:
                self.failures.append(f"F{ident-9000} (macro)")
        for n, alarm in enumerate(alarms):
            combination = parse_hotkey(alarm.get("keybind", ""))
            if not combination or not alarm.get("enabled", False):
                continue
            mods, vk = combination
            if (mods, vk) in used:
                self.failures.append(alarm["name"] + " (duplicate shortcut)")
                continue
            used.add((mods, vk))
            ident = 10000 + n
            if user32.RegisterHotKey(None, ident, mods | 0x4000, vk):
                self.registered.append(ident)
                self.alarms[ident] = alarm["id"]
            else:
                self.failures.append(alarm["name"] + " (shortcut unavailable)")

    def unregister(self):
        if os.name == "nt":
            for ident in self.registered:
                ctypes.windll.user32.UnregisterHotKey(None, ident)
        self.registered.clear()
        self.alarms.clear()

    def nativeEventFilter(self, eventType, message):
        try:
            kind = bytes(eventType).decode("ascii", errors="ignore")
        except (TypeError, ValueError):
            kind = str(eventType)
        if os.name == "nt" and kind in ("windows_dispatcher_MSG", "windows_generic_MSG"):
            from ctypes import wintypes
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312:
                    if msg.wParam in self.MACRO:
                        self.handler(self.MACRO[msg.wParam])
                        return True, 0
                    if msg.wParam in self.alarms:
                        self.alarm_handler(self.alarms[msg.wParam])
                        return True, 0
            except (TypeError, ValueError):
                pass
        return False, 0
