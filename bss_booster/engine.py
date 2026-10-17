"""Independent interval scheduler, Roblox focus check, and Windows native key injection.

Pure scheduler is independently unit tested. Injection never types without a user
pressing Start and, by default, a foreground title containing Roblox.
"""
from __future__ import annotations
import ctypes
import os
import time
from dataclasses import dataclass


class Scheduler:
    def __init__(self):
        self.slots = []
        self.next_due = {}
        self.running = False
        self.paused = False
        self.pause_started = 0.0

    def configure(self, slots: list[dict], now: float | None = None):
        now = time.monotonic() if now is None else now
        old = {int(v["key"]): v for v in self.slots}
        self.slots = [dict(x) for x in slots]
        for rule in self.slots:
            key = int(rule["key"])
            if key not in self.next_due or old.get(key) != rule:
                self.next_due[key] = now + float(rule["delay"])
        for key in set(self.next_due) - {int(v["key"]) for v in self.slots}:
            del self.next_due[key]

    def start(self, slots: list[dict], now: float | None = None):
        now = time.monotonic() if now is None else now
        self.slots = []
        self.next_due = {}
        self.configure(slots, now)
        self.running, self.paused = True, False

    def pause(self, now: float | None = None):
        if self.running and not self.paused:
            self.paused = True
            self.pause_started = time.monotonic() if now is None else now

    def resume(self, now: float | None = None):
        if self.running and self.paused:
            now = time.monotonic() if now is None else now
            delta = now - self.pause_started
            self.next_due = {k: val + delta for k, val in self.next_due.items()}
            self.paused = False

    def stop(self):
        self.running, self.paused = False, False
        self.next_due.clear()

    def due(self, now: float | None = None, can_send: bool = True) -> list[int]:
        if not self.running or self.paused or not can_send:
            return []
        now = time.monotonic() if now is None else now
        ready = []
        for rule in self.slots:
            key = int(rule["key"])
            if not rule["enabled"] or rule["item"].strip().lower() == "empty":
                continue
            if now >= self.next_due.get(key, now):
                ready.append(key)
                # No burst/catch-up after unfocusing or lag.
                self.next_due[key] = now + max(.1, float(rule["interval"]))
        return ready


class WindowsKeyboard:
    """SendInput with scan codes (foreground-only). Available on Windows."""
    @staticmethod
    def focused(target_title: str) -> bool:
        if os.name != "nt":
            return False
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        buffer = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return bool(target_title.strip()) and target_title.casefold() in buffer.value.casefold()

    @staticmethod
    def send(key: int) -> bool:
        if os.name != "nt":
            return False
        from ctypes import wintypes
        ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ULONG_PTR)]
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]
        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]
        class INPUT_UNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]
        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("payload", INPUT_UNION)]
        if key < 0 or key > 9:
            return False
        vk = ord(str(key))
        user32 = ctypes.windll.user32
        scan = user32.MapVirtualKeyW(vk, 0)
        if not scan:
            return False
        down = INPUT(1, INPUT_UNION(ki=KEYBDINPUT(0, scan, 0x0008, 0, 0)))
        up = INPUT(1, INPUT_UNION(ki=KEYBDINPUT(0, scan, 0x0008 | 0x0002, 0, 0)))
        arr = (INPUT * 2)(down, up)
        user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        user32.SendInput.restype = wintypes.UINT
        return user32.SendInput(2, arr, ctypes.sizeof(INPUT)) == 2


@dataclass
class AlarmRuntime:
    remaining: float
    deadline: float = 0.0
    running: bool = False


class AlarmClock:
    def __init__(self):
        self.runtime: dict[str, AlarmRuntime] = {}

    def configure(self, alarms: list[dict]):
        ids = set()
        for alarm in alarms:
            aid = alarm["id"]
            ids.add(aid)
            if aid not in self.runtime:
                self.runtime[aid] = AlarmRuntime(float(alarm["duration"]))
        for aid in set(self.runtime) - ids:
            del self.runtime[aid]

    def start(self, alarm: dict, now: float | None = None):
        if not alarm["enabled"]:
            return
        now = time.monotonic() if now is None else now
        rt = self.runtime.setdefault(alarm["id"], AlarmRuntime(float(alarm["duration"])))
        if not rt.running:
            if rt.remaining <= 0:
                rt.remaining = float(alarm["duration"])
            rt.deadline = now + rt.remaining
            rt.running = True

    def pause(self, aid: str, now: float | None = None):
        rt = self.runtime.get(aid)
        if rt and rt.running:
            now = time.monotonic() if now is None else now
            rt.remaining = max(0.0, rt.deadline - now)
            rt.running = False

    def reset(self, alarm: dict):
        self.runtime[alarm["id"]] = AlarmRuntime(float(alarm["duration"]))

    def stop_all(self):
        for rt in self.runtime.values():
            rt.running = False

    def time_left(self, aid: str, now: float | None = None) -> float:
        rt = self.runtime.get(aid)
        if not rt:
            return 0.0
        if not rt.running:
            return rt.remaining
        now = time.monotonic() if now is None else now
        return max(0.0, rt.deadline - now)

    def tick(self, alarms: list[dict], now: float | None = None) -> list[str]:
        now = time.monotonic() if now is None else now
        finished = []
        for alarm in alarms:
            rt = self.runtime.get(alarm["id"])
            if not rt or not rt.running or not alarm["enabled"]:
                continue
            if rt.deadline <= now:
                finished.append(alarm["id"])
                if alarm["repeat"]:
                    rt.deadline = now + alarm["duration"]
                    rt.remaining = float(alarm["duration"])
                else:
                    rt.running = False
                    rt.remaining = 0.0
        return finished
