"""Windows offline alarm playback. No cloud services or Python voice packages.

'Voice' uses Windows built-in System.Speech through a hidden PowerShell process.
'Sound' loops a bundled .wav file via built-in winsound. Both play until acknowledged.
"""
from __future__ import annotations
import base64
import os
import subprocess
import threading
from pathlib import Path


class AlarmNotifier:
    def __init__(self, sound_path: Path):
        self.sound_path = Path(sound_path)
        self.active: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._process = None
        self._process_alarm_id = None
        self._sound_running = False
        self._voice_unavailable = False
        self._voice_thread = threading.Thread(target=self._voice_loop, daemon=True, name="BssAlarmVoice")
        self._voice_thread.start()

    def trigger(self, alarm: dict):
        if alarm.get("alert_mode", "Off") == "Off":
            return
        with self._lock:
            self.active[alarm["id"]] = {"name": alarm["name"], "alert_mode": alarm["alert_mode"]}
        self._sync_sound()
        self._wake.set()

    def acknowledge(self, alarm_id: str):
        with self._lock:
            self.active.pop(alarm_id, None)
        self._interrupt_voice(alarm_id)
        self._sync_sound()
        self._wake.set()

    def sync(self, alarms: list[dict]):
        by_id = {a["id"]: a for a in alarms if a.get("enabled")}
        with self._lock:
            for aid in list(self.active):
                if aid not in by_id or by_id[aid].get("alert_mode") == "Off":
                    del self.active[aid]
                else:
                    self.active[aid] = {"name": by_id[aid]["name"], "alert_mode": by_id[aid]["alert_mode"]}
        self._interrupt_voice_if_inactive()
        self._sync_sound()
        self._wake.set()

    def is_alerting(self, aid: str) -> bool:
        with self._lock:
            return aid in self.active

    def _sync_sound(self):
        if os.name != "nt":
            return
        with self._lock:
            needs_sound = any(a["alert_mode"] == "Sound" or
                              (self._voice_unavailable and a["alert_mode"] == "Voice")
                              for a in self.active.values())
            if needs_sound == self._sound_running:
                return
            try:
                import winsound
                if needs_sound:
                    winsound.PlaySound(str(self.sound_path),
                                       winsound.SND_FILENAME | winsound.SND_ASYNC |
                                       winsound.SND_LOOP | winsound.SND_NODEFAULT)
                else:
                    winsound.PlaySound(None, 0)
                self._sound_running = needs_sound
            except (OSError, RuntimeError):
                self._sound_running = False

    def _interrupt_voice(self, alarm_id: str):
        with self._lock:
            if self._process_alarm_id == alarm_id and self._process is not None:
                self._process.terminate()

    def _interrupt_voice_if_inactive(self):
        with self._lock:
            aid = self._process_alarm_id
            if aid is not None and (aid not in self.active or self.active[aid]["alert_mode"] != "Voice"):
                if self._process is not None:
                    self._process.terminate()

    def _speak(self, aid: str, name: str):
        if os.name != "nt":
            self._stop.wait(0.6)
            return
        # The alarm name is a PowerShell single-quoted *string*, never program text.
        literal = name.replace("'", "''")
        command = ("Add-Type -AssemblyName System.Speech; "
                   "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                   "$voice.Speak('" + literal + "'); $voice.Dispose()")
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        try:
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, ValueError):
            self._voice_unavailable = True
            self._sync_sound()
            self._stop.wait(1)
            return
        with self._lock:
            self._process = proc
            self._process_alarm_id = aid
            if aid not in self.active or self._stop.is_set():
                proc.terminate()
        try:
            proc.wait(timeout=35)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        finally:
            if proc.returncode and not self._stop.is_set() and self.is_alerting(aid):
                self._voice_unavailable = True
                self._sync_sound()
            with self._lock:
                if self._process is proc:
                    self._process = None
                    self._process_alarm_id = None

    def _voice_loop(self):
        while not self._stop.is_set():
            with self._lock:
                voices = [(aid, data["name"]) for aid, data in self.active.items()
                          if data["alert_mode"] == "Voice"]
            if not voices:
                self._wake.wait(0.4)
                self._wake.clear()
                continue
            for aid, name in voices:
                if self._stop.is_set():
                    return
                with self._lock:
                    data = self.active.get(aid)
                    if not data or data["alert_mode"] != "Voice":
                        continue
                    name = data["name"]
                self._speak(aid, name)
                if self._stop.wait(.4):
                    return

    def close(self):
        self._stop.set()
        self._wake.set()
        with self._lock:
            self.active.clear()
            if self._process is not None:
                self._process.terminate()
        self._sync_sound()
        self._voice_thread.join(timeout=1.5)
