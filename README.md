# Bss Booster v1.4.0 — Windows boosting macro

A customizable Bee Swarm Simulator boosting helper with a **light, Revolution-Macro-inspired desktop UI** and **transparent red AUTO buttons**, designed to sit beneath the real Roblox hotbar. Built with Python and PySide6; no network access is needed to run the finished app. Unaffiliated with Roblox or Bee Swarm Simulator.

## First-time setup (4 steps)

1. Open **Hotbar** and select the item you have in each numbered Roblox slot (1–7). Every slot starts Empty and OFF on a fresh install.
2. For each item, set **Every** to the repeat interval in seconds, and **Delay** to the delay before the first use (zero is immediate). Tick **Use** to arm it. Each timer is independent.
3. Set Roblox to **windowed or borderless**. Enable **Show red AUTO buttons** and **right-drag any red button** to position the row beneath the real hotbar. Use **Settings → Button size / Distance between buttons** to align the row. The overlay does not read or redraw Roblox's inventory icons; it only shows the red AUTO buttons.
4. Click a red **AUTO: OFF** button to change it to **AUTO: ON**, or turn a slot on from the Hotbar page. Press **F1** to actually start boosting, **F2** to pause, **F3** to stop. By default keys are only sent when a window containing `Roblox` is focused.

### Overlay design

- Seven individually clickable red pill buttons, with separate **Show Slot 1–7** checkboxes in **Hotbar → Choose which AUTO buttons appear on-screen**. Hide an individual pill without disabling that item's actual macro. Invisible pills leave their original column empty: the other buttons never slide sideways. Background **#FF0000 at 20% opacity**; button text **35% opacity**, set in **Gotham Regular** when installed on your system, otherwise Segoe UI. No black panel, background bar or title strip.
- Optional countdown on each red AUTO button. Disabled/unconfigured slots display `AUTO: OFF`.
- **Right-drag any red button** to reposition the whole overlay, including to the *actual bottom of your screen*. Unlike previous versions, the position is not clamped above the Windows taskbar. New position saves immediately and loads next time. You can also use **Move to screen bottom** on the Hotbar or Settings page; size (60–150%) and spacing (0–80 px) remain configurable.
- **Show red AUTO buttons** and **Show alarm timers** have separate switches. Show both, either one, or neither. The Hotbar page also has **Show all 7 / Hide all 7** quick buttons and per-slot visibility checkboxes. These visibility options are saved with each profile; macro 'Use' and 'Show' are independent. Hiding a display NEVER stops the associated macro or running alarms.
- Optional **click-through mode** in Settings lets game clicks pass through the buttons, but disables mouse toggling until you switch it off.
- **Alarms are in their own transparent always-on-top window**, independent of the hotbar window. **Right-drag an alarm chip to move all alarm timers** without moving the red pills. **Right-drag a red pill** to move only the hotbar overlay. Each window remembers its own position on restart; use **Reset alarm overlay position** in Alarms or Settings to re-center alarms. Each alarm also has its own individual Overlay checkbox.
- The overlay is an independent always-on-top utility window. Some exclusive-fullscreen games cover it; use borderless/windowed Roblox. The Windows taskbar itself may cover a button dragged behind the taskbar when the taskbar is visible.

### Alarms

- Add alarms with your own name, hours/minutes/seconds, Repeat, On/Off, and individual **Overlay** display switch.
- Set an individual **single-key reset shortcut**, e.g. `G`, `8`, `Space`, `F4` or combinations like `Ctrl+Alt+1`. `F1–F3` are reserved for the macro. A global single-key shortcut can intercept a game control; don't use a hotbar number you need in Roblox.
- Choose **Sound**, **Voice** or **Off**. Sound loops the bundled WAV; Voice repeats the alarm name using **Windows offline text-to-speech** (not cloud AI). Alarms keep their sound/voice and time progression even when hidden. Reset or its keybind silences and restarts that alarm; Silence stops only the sound.
- Individual alarms can run independently of the boosting macro; an optional Setting lets you start enabled alarms with the macro.

### Other features

- One-click **Enable all assigned** / **Disable all** slots; clear instructions and tooltips for beginners.
- Multiple saved presets; profile cloning, import, export. Switching profiles stops the macro.
- Live Status log and sent-key counts; configurable Roblox window title, animations, light/dark theme.
- Local settings and profiles save automatically and on exit in `%LOCALAPPDATA%\BssBooster\booster_settings.json`; an update preserves existing settings. First-time installs have empty hotbar and no alarms.
- The macro **never starts by itself** when you launch the app. Saved alarm durations are retained but actively ticking alarms are not resumed across restart.

## Windows executable without Python on your PC

**Easiest:** Follow [`BUILD_WITHOUT_PYTHON.md`](BUILD_WITHOUT_PYTHON.md). Upload the project contents to a new GitHub repository and open **Actions → Build Bss Booster Windows EXE and Installer → Run workflow**. The GitHub Windows runner compiles the standalone portable **`BssBooster.exe`** and installer **`BssBoosterSetup.exe`** under the completed build's **Artifacts**. The finished EXEs run without Python or a GitHub login.

**If Python is already installed:** run `run_windows.bat` to launch the source app, `build_windows.bat` to produce the portable EXE, or `build_installer_windows.bat` to produce the complete installer (uses Inno Setup 6).

**This ZIP contains source and the EXE builder, not a precompiled EXE.** Windows builds must be completed and tested on Windows. Cloud builds also run a PySide6 GUI smoke test as well as the settings/scheduler tests before compiling the EXEs.

## What to expect and limitations

- This does not copy in-game icons or inspect the Roblox inventory. The red buttons are aligned visually beneath it using position and spacing controls.
- Simulated keypresses use the Windows `SendInput` API. Some games may ignore synthetic input; Roblox behaviour isn't guaranteed. Bss Booster has no memory-reading, anti-cheat bypass or game injection features.
- Macro triggers at independent user-defined intervals. If Roblox loses focus, input stops when foreground protection is on; missed presses don't burst on refocus.
- If you can't click overlay AUTO buttons, disable **Click-through mode** in Settings. If they aren't visible, configure at least one item, then enable the overlay. Moving them is done by **right-dragging** a red button.
- Gotham Regular is commercial typography: Bss Booster uses it when it is already installed, but the font is **not redistributed** with the project.
- Windows TTS is a system speech synthesizer, not a remote AI service. Voice playback requires Windows speech support; if it fails, Bss Booster falls back to the alarm sound.
- Windows SmartScreen may warn about unsigned EXEs built through your own GitHub repository. Only run files you trust.

## Project structure

- `bss_booster/ui.py` — main desktop window, Hotbar/Timers/Alarms/Profiles/Status/Settings pages
- `bss_booster/overlay.py` — independent transparent windows for seven aligned hotbar buttons and separately draggable alarms
- `bss_booster/config.py` — preferences, profiles, settings validation and atomic saving
- `bss_booster/engine.py` — independent macro scheduler and alarm clock
- `bss_booster/notifier.py` — repeating sound and Windows offline spoken alarms
- `bss_booster/hotkeys.py` / `hotkey_codec.py` — Windows macro hotkeys and one-key alarm reset
- `bss_booster/theme.py` — main UI light/dark palettes
- `.github/workflows/windows-release.yml` — Windows build and tests
- `tests/` — configuration/scheduler tests and Windows GUI smoke test
