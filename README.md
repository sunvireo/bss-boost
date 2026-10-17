# Bss Booster — Windows desktop macro + overlay (v1.2)

Bss Booster is a locally running PySide6 Windows 11 application with a clean, pale layout inspired by the reference app. **It is not affiliated with Roblox or Bee Swarm Simulator.**

## Features

- **Hotbar:** 7 visual slots matching keys **1–7**. Select a supplied item (or type a custom name), enable/disable each slot, and set an independent **repeat interval (0.1–86,400 seconds)** and **first-use delay (0–86,400 seconds)**.
- **Boosting macro:** Start (F1), pause (F2), stop (F3). Every enabled key runs on its own timer. Windows `SendInput` generates actual key down/up events. **All slots start empty and OFF**; nothing is pressed until you enable one and select Start.
- **Foreground safety:** Keys are sent **only if the active window title contains `Roblox`**, by default. Switch from Bss Booster into your Roblox window after pressing Start. Customize the title filter or turn the protection off in Settings (not recommended).
- **Timers:** On the first launch this page is empty; assign an item in Hotbar to create its editable schedule. Review intervals, delays and use counts here.
- **Alarms:** Create, rename, enable, pause, reset or delete countdown alarms with durations in hours/minutes/seconds. Optional repeat, per-alarm global reset keybind, selectable looping **Sound / Voice / Off** alert, and floating overlay for each alarm. Sound and offline Windows TTS repeat until you use that alarm’s reset keybind or click Silence / Reset.
- **Always-on-top overlay:** Title-free black bar shows each of the seven hotbar slots with live next-use countdowns (READY / PAUSED / OFF when appropriate), plus alarm names and countdowns underneath. Overlay hides itself when nothing has been configured. Position and opacity are adjustable. Overlay does not intentionally capture mouse input. **For games use borderless/windowed mode:** exclusive fullscreen may cover the overlay.
- **Profiles:** Duplicate, switch, import and export separate sets of hotbar rules + alarm definitions. Switching profiles stops any running macro.
- **Status:** Live key counts and session activity log.
- **Settings:** Windows global function-key shortcuts and per-alarm reset shortcuts, focus safety, overlay behaviour, light/dark theme, animations, and whether alarms start with the macro.
- **Local configuration:** Auto-saved during editing and on close, then reloaded next launch. Stored as JSON at `%LOCALAPPDATA%\BssBooster\booster_settings.json`. Profiles and alarm definitions persist. **Active countdown progress and the running macro are intentionally not resumed after restart.** The app does not need internet once dependencies are installed.

## Get the EXE without installing Python (recommended)

The installer and portable EXE **do not need Python installed to run**. To *build* them without installing Python yourself, follow **`BUILD_WITHOUT_PYTHON.md`**. A preconfigured GitHub Actions workflow builds `BssBooster.exe` and `BssBoosterSetup.exe` on a Windows cloud build machine and lets you download both. No local Python installation is required. A GitHub account and internet connection are required for this build.

**This source ZIP does not already contain a precompiled Windows EXE**. GitHub Actions compiles the EXEs for you. You can also build them locally if you already have Python.

## Windows 11 quick start (source mode: Python required)

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/). Check **Add python.exe to PATH** during setup.
2. Extract this ZIP **first** (do not run BAT files from inside a zipped folder).
3. Double-click `run_windows.bat`. The first run creates a `.venv` folder and downloads PySide6, so an internet connection is required **once**.
4. In Bss Booster, open **Hotbar**, select items for your in-game slots 1–7, enable the desired slots, and set intervals. Everything starts blank on first launch.
5. Press **Start (F1)** and switch focus to Roblox. F2 pauses; F3 stops. If your game isn't responding, read the notes below.

## Make a standalone Windows EXE

Double-click `build_windows.bat` **on a Windows PC**. This installs PyInstaller into the project's `.venv` and produces:

`dist\BssBooster.exe`

This is the full packaged app; it should not require Python on the computer where it runs. The build needs Windows because Windows EXEs cannot be built directly on Linux using standard PyInstaller. You can rename the file or pin it to the taskbar. Windows SmartScreen may show a warning for an unsigned app you build yourself; only run software you trust.

## Create a proper Windows setup installer (recommended)

To make **`BssBoosterSetup.exe`**, which installs Bss Booster like a normal Windows program:

1. On your **Windows 11 PC**, install [Python 3.11 or newer](https://www.python.org/downloads/windows/) and check **Add Python to PATH**. If Python is already installed, skip this step.
2. Extract this ZIP, then double-click **`build_installer_windows.bat`**. Do not launch it from inside the ZIP.
3. The builder downloads Python dependencies and first creates `dist\BssBooster.exe`. An internet connection is required for this build step.
4. If [Inno Setup 6](https://jrsoftware.org/isdl.php) isn't installed, the builder offers to install it using Windows Package Manager (`winget`), when available. Otherwise, install Inno Setup 6 manually and run the builder again.
5. Find your **real installer** here: **`dist\installer\BssBoosterSetup.exe`**.

Double-click `BssBoosterSetup.exe` to open the installation wizard. The installer:

- installs to your Windows user account (no administrator rights normally needed);
- adds **Bss Booster** to the **Start menu**;
- offers a **desktop shortcut** (optional checkbox during installation);
- registers an **uninstaller** in Windows Settings > Apps > Installed apps;
- offers to launch Bss Booster when installation finishes.

You can send just **`BssBoosterSetup.exe`** to another Windows user; they do **not** need Python, PyInstaller or Inno Setup to install or run it. User settings are stored at `%LOCALAPPDATA%\BssBooster\booster_settings.json`; uninstalling the program does not intentionally delete your personal saved profiles/settings. If upgrading, keep the same installer `AppId` in `BssBooster.iss` to let the installer update the previous install.

**Important:** This ZIP contains a *builder for an installer*, not a precompiled setup EXE. Standard PyInstaller and Inno Setup create Windows executables on **Windows**. A local Windows build and install test is still required. An unsigned homemade installer may trigger Windows SmartScreen warnings.

## What happens when you upgrade from an older Bss Booster?

**Existing user setups are kept.** The blank-start defaults only apply when no saved configuration exists. If you previously used Bss Booster v1.1, its current hotbar and alarm presets stay as they were when the new app is installed. To start from scratch, clear the items/alarms manually in the app or (with the app closed) back up and remove `%LOCALAPPDATA%\BssBooster\booster_settings.json`.

## Single-key alarm shortcuts

On the Alarms page, click **Reset shortcut** and press just one key (such as `G`, `8`, `Space` or `F4`). Modifier combinations are still supported. `F1`, `F2` and `F3` are always reserved for Start/Pause/Stop. Windows may refuse reserved keys. **Important: using a plain letter or number as a global shortcut can swallow that key from Roblox and other programs.** Choose a key you do not use for gameplay, or use a modified combination if that happens. The shortcut only runs while Bss Booster is open and global shortcuts are enabled.

## Controls and behavior

| Action | Shortcut (Windows) | Behavior |
|---|---|---|
| Start / Resume | F1 | Begins per-slot schedules; uses configured first-use delays. |
| Pause | F2 | Pauses all macro intervals and remembers how much time remains. |
| Stop | F3 | Stops macro. Starting again resets intervals. |
| Alarm Start/Pause/Reset | Alarm row buttons | Reset now silences and restarts the full countdown. |
| Per-alarm reset | Configurable on Alarms page, e.g. G, 8, Space or Ctrl+Alt+1 | Works globally while the app runs; silences audio and resets & restarts the selected alarm. |
| + in left sidebar | Click | Create an alarm. |

**Example:** If your Gumdrops are on key 2 and your Stingers are on key 4, set key 2 every 2.0 seconds and key 4 every 10.0 seconds, tick both Use boxes, Start, then focus Roblox. Both intervals run independently. The first use happens immediately unless you set a first-use delay. When you switch out of Roblox with foreground safety enabled, keys stop being sent. When you switch back, each overdue slot fires at most once and re-schedules from then (no input burst).

## Important limitations

- **Windows-only key input:** The PySide6 interface may open on other desktop OSes, but keyboard injection and system-wide Windows hotkeys are implemented for Windows.
- **Game compatibility:** Roblox/other games may ignore simulated `SendInput` keystrokes depending on their input pipeline or security systems; the code cannot guarantee the game will accept input. Try regular windowed or borderless mode, and ensure window title matches Settings. No anti-cheat bypass, game injection, memory reading, or exploit features are included.
- **Overlay visibility:** Some games in exclusive fullscreen appear above always-on-top utility windows. Use borderless/windowed display mode to see the overlay.
- **Global hotkeys:** Other applications may already own a requested key combination. If Windows registration fails, use the on-screen button or choose another shortcut. Macro F1/F2/F3 are reserved; each alarm accepts Ctrl/Alt/Shift combinations or F4–F12. Hotkeys can be disabled in Settings.
- **Focus protection:** Turning it off makes simulated keypresses enter whatever application is focused. Keep it on for safety.
- **App permissions:** Normal user permissions should be sufficient. Windows may restrict synthesized input into elevated applications; avoid running Roblox and this app at different integrity levels.
- **Timers vs boost effects:** Bss Booster repeats keys on your chosen schedule; it cannot determine actual in-game cooldowns or inventories. Select reasonable timings yourself and comply with the rules of the game you use it with.
- **Voice option:** This is Windows' built-in offline **text-to-speech (TTS)**, not a generated AI voice. It speaks the chosen alarm name repeatedly until acknowledged. If unavailable, it falls back to the repeating alarm WAV sound. The bundled WAV uses no network access.
- **Audio acknowledgement:** The **Silence** button stops the alarm audio; **Reset**, the reset shortcut, or **Start** also silence the alarm. **Reset** restarts its countdown immediately. Alerts stay active until acknowledged, even if the associated countdown is configured to repeat.
- **Session counts** and running alarm progress reset when reopening the application. Alarm configurations and profiles persist.

## Project files

```
BssBoosterV1/
├── main.py                     # Desktop entry point
├── requirements.txt            # PySide6 dependency
├── run_windows.bat             # Start app in a Python virtual environment
├── build_windows.bat           # Create dist/BssBooster.exe with PyInstaller
├── build_installer_windows.bat # One-click Windows installer builder
├── BssBooster.iss              # Inno Setup installer definition
├── assets/
│   ├── bss_booster_icon.png    # App icon
│   ├── bss_booster_icon.ico    # Windows executable icon
│   └── booster_alarm.wav       # Looping alarm sound
├── bss_booster/
│   ├── config.py               # Safe JSON saves / profiles / validation
│   ├── engine.py               # Scheduler, alarm clock and Windows SendInput
│   ├── hotkeys.py              # Windows global macro & alarm shortcuts
│   ├── hotkey_codec.py         # Shortcut parsing/validation
│   ├── notifier.py             # Looping WAV & offline Windows TTS
│   ├── theme.py                # Reference-like light theme and optional dark theme
│   └── ui.py                   # Pages, widgets, floating overlay and wiring
└── tests/
    ├── test_config.py
    ├── test_engine.py
    └── test_alarms_v11.py
```

Cloud-build instructions: `BUILD_WITHOUT_PYTHON.md`; cloud pipeline: `.github/workflows/windows-release.yml`.

## Editing the UI

Most controls and page layouts are in `bss_booster/ui.py`. Colours and spacing are in `bss_booster/theme.py`. Run `run_windows.bat` to preview your changes. If you want the exact look of a new screenshot in a future iteration, send it and these components can be adjusted.

## Tests

The pure-Python scheduler and settings tests are run with `python -m pytest tests` if pytest is installed. Because GUI testing and creation of a Windows EXE require PySide6 on a Windows desktop, those steps must be tested on Windows; unit tests and Python syntax checks passed here, but the interface, voice output, installer, and actual Windows EXEs have not been built/tested in this environment.
