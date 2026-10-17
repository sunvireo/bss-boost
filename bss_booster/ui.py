"""Bss Booster graphical interface — screenshot-inspired compact desktop layout."""
from __future__ import annotations
import copy
import json
import os
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QGraphicsOpacityEffect, QHBoxLayout, QInputDialog, QKeySequenceEdit, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from .config import ITEMS, Store, human_time, make_alarm, validated_profile
from .engine import AlarmClock, Scheduler, WindowsKeyboard
from .hotkeys import WindowsHotkeys
from .hotkey_codec import normalize_hotkey
from .notifier import AlarmNotifier
from .overlay import HotbarOverlay, AlarmOverlay
from .overlay_geometry import bottom_edge_y, clamp_overlay_position
from .theme import stylesheet

PAGES = ["Hotbar", "Timers", "Alarms", "Profiles", "Status", "Settings"]
SYMBOLS = {"Hotbar": "◈", "Timers": "◷", "Alarms": "♧", "Profiles": "▤", "Status": "⌁", "Settings": "⚙"}


def row(*widgets, spacing=10, margins=(0, 0, 0, 0)) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    for widget in widgets:
        if widget is not None:
            layout.addWidget(widget)
    return layout


def column(*widgets, spacing=10) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def label(text: str, kind: str = "", parent=None) -> QLabel:
    widget = QLabel(str(text), parent)
    if kind:
        widget.setObjectName(kind)
    return widget


def btn(text: str, callback=None, kind: str = "", tooltip: str = "") -> QPushButton:
    widget = QPushButton(text)
    if kind:
        widget.setObjectName(kind)
    if tooltip:
        widget.setToolTip(tooltip)
    if callback:
        widget.clicked.connect(callback)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def checkbox(name, value: bool, on_change) -> QCheckBox:
    widget = QCheckBox(name)
    widget.setChecked(value)
    widget.toggled.connect(on_change)
    return widget


def spin(low: int, high: int, val: int, handler, width: int = 72) -> QSpinBox:
    widget = QSpinBox()
    widget.setRange(low, high)
    widget.setValue(val)
    widget.setFixedWidth(width)
    widget.valueChanged.connect(handler)
    return widget


def panel(object_name="Panel") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(object_name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)
    return frame, layout


def line() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #eae5e8; border: 0; border-top: 1px solid #eae5e8;")
    f.setFixedHeight(1)
    return f


class BoosterWindow(QMainWindow):
    def __init__(self, store: Store, icon_path: Path):
        super().__init__()
        self.store = store
        self.scheduler = Scheduler()
        self.clock = AlarmClock()
        self.clock.configure(self.store.profile["alarms"])
        self.notifier = AlarmNotifier(icon_path.parent / "booster_alarm.wav")
        self.overlay = HotbarOverlay(store, self.clock, self.notifier, self.scheduler, self._toggle_overlay_slot)
        self.alarm_overlay = AlarmOverlay(store, self.clock, self.notifier)
        self.current_page = ""
        self.slot_tiles = {}
        self.slot_focus = {}
        self.slot_counts = {n: 0 for n in range(1, 8)}
        self.timer_count_labels = {}
        self.alarm_time_labels = {}
        self.log_lines = []
        self.animation = None
        self.setWindowTitle("Bss Booster")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(950, 635)
        self.resize(1150, 755)
        self.setStyleSheet(stylesheet(store.settings["theme"]))
        self._build_shell(icon_path)
        self._render_overlays()
        self._save_later = QTimer(self)
        self._save_later.setSingleShot(True)
        self._save_later.setInterval(360)
        self._save_later.timeout.connect(self.store.save)
        self._pulse = QTimer(self)
        self._pulse.setInterval(90)
        self._pulse.timeout.connect(self._tick)
        self._pulse.start()
        self.hotkeys = WindowsHotkeys(self._action_by_name, self._restart_by_alarm_id)
        QApplication.instance().installNativeEventFilter(self.hotkeys)
        QTimer.singleShot(0, self._sync_hotkeys)
        # Application shortcuts work while the window is focused, including on non-Windows.
        for key, action in (("F1", self.start_macro), ("F2", self.pause_macro), ("F3", self.stop_macro)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(action)
        self.show_page("Hotbar")
        self._log("Ready. Set up an item, click its red AUTO button or enable it here, then press F1.")

    def _build_shell(self, icon_path):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)
        top = QWidget()
        top.setObjectName("TopBar")
        top.setFixedHeight(49)
        nav = QHBoxLayout(top)
        nav.setSpacing(0)
        nav.setContentsMargins(8, 0, 10, 0)
        self.top_buttons = {}
        for page in PAGES:
            b = btn(SYMBOLS[page] + "  " + page, lambda _=False, p=page: self.show_page(p), "NavTab")
            nav.addWidget(b)
            self.top_buttons[page] = b
        nav.addStretch(1)
        self.top_search = btn("⌕", lambda: self.show_page("Settings"), "SoftPurple", "Open settings")
        self.top_search.setFixedSize(34, 34)
        nav.addWidget(self.top_search)
        outer.addWidget(top)

        middle = QWidget()
        middle_row = QHBoxLayout(middle)
        middle_row.setSpacing(0)
        middle_row.setContentsMargins(0, 0, 0, 0)
        rail = QWidget()
        rail.setObjectName("LeftRail")
        rail.setFixedWidth(61)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(8, 9, 8, 10)
        rail_layout.setSpacing(9)
        self.rail_buttons = {}
        if icon_path.exists():
            logo = QLabel()
            pixmap = QIcon(str(icon_path)).pixmap(34, 34)
            logo.setPixmap(pixmap)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo = label("✿")
        logo.setFixedHeight(45)
        rail_layout.addWidget(logo)
        for page in ["Hotbar", "Timers", "Alarms", "Profiles", "Settings"]:
            b = btn(SYMBOLS[page], lambda _=False, p=page: self.show_page(p), "RailButton", page)
            b.setFixedHeight(37)
            rail_layout.addWidget(b)
            self.rail_buttons[page] = b
        rail_layout.addStretch(1)
        add = btn("+", self.add_alarm, "AddButton", "Create an alarm")
        add.setFixedSize(41, 41)
        rail_layout.addWidget(add)
        middle_row.addWidget(rail)
        self.stack = QStackedWidget()
        for _ in PAGES:
            self.stack.addWidget(QWidget())
        middle_row.addWidget(self.stack, 1)
        outer.addWidget(middle, 1)

        footer = QWidget()
        footer.setObjectName("BottomBar")
        footer.setFixedHeight(62)
        f = QHBoxLayout(footer)
        f.setContentsMargins(13, 7, 13, 7)
        f.setSpacing(10)
        status_box = QWidget()
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        status_head = row(label("Status"), spacing=5)
        self.status_label = label("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_head.addWidget(self.status_label, 1)
        status_layout.addLayout(status_head)
        self.activity_label = label("0 keys sent", "Muted")
        status_layout.addWidget(self.activity_label)
        status_box.setFixedWidth(178)
        f.addWidget(status_box)
        self.start_btn = btn("▶   Start     F1", self.start_macro, "Primary")
        self.pause_btn = btn("Ⅱ   Pause    F2", self.pause_macro)
        self.stop_btn = btn("■   Stop    F3", self.stop_macro)
        self.start_btn.setMinimumWidth(118)
        self.pause_btn.setMinimumWidth(112)
        self.stop_btn.setMinimumWidth(106)
        for b in (self.start_btn, self.pause_btn, self.stop_btn):
            f.addWidget(b)
        f.addStretch(1)
        preset_area = QWidget()
        preset_layout = QVBoxLayout(preset_area)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(3)
        preset_layout.addWidget(label("Preset", "Muted"))
        self.profile_selector = QComboBox()
        self.profile_selector.setFixedWidth(156)
        self.profile_selector.currentTextChanged.connect(self.switch_profile)
        preset_layout.addWidget(self.profile_selector)
        f.addWidget(preset_area)
        self.footer_settings = btn("⚙", lambda: self.show_page("Settings"), "SoftPurple", "Settings")
        self.footer_settings.setFixedSize(38, 38)
        f.addWidget(self.footer_settings)
        outer.addWidget(footer)
        self._fill_profile_selector()
        self._update_controls()

    def _fill_profile_selector(self):
        self.profile_selector.blockSignals(True)
        self.profile_selector.clear()
        self.profile_selector.addItems(self.store.data["profiles"].keys())
        self.profile_selector.setCurrentText(self.store.data["active_profile"])
        self.profile_selector.blockSignals(False)

    def _page(self, title: str, description: str):
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("PageBody")
        v = QVBoxLayout(body)
        v.setContentsMargins(24, 22, 24, 28)
        v.setSpacing(18)
        head = QWidget()
        header = QVBoxLayout(head)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(5)
        header.addWidget(label("BSS BOOSTER  /  " + title.upper(), "Eyebrow"))
        header.addWidget(label(title, "Title"))
        sub = label(description, "Subtitle")
        sub.setWordWrap(True)
        header.addWidget(sub)
        v.addWidget(head)
        scroll.setWidget(body)
        return scroll, v

    def show_page(self, page: str):
        if page not in PAGES:
            return
        index = PAGES.index(page)
        self.current_page = page
        self.slot_tiles = {}
        self.slot_focus = {}
        self.timer_count_labels = {}
        self.alarm_time_labels = {}
        builder = getattr(self, "_page_" + page.lower())
        screen = builder()
        old = self.stack.widget(index)
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, screen)
        self.stack.setCurrentIndex(index)
        for name, widget in self.top_buttons.items():
            self._property(widget, "active", name == page)
        for name, widget in self.rail_buttons.items():
            self._property(widget, "active", name == page)
        if self.store.settings["animations"]:
            effect = QGraphicsOpacityEffect(screen)
            screen.setGraphicsEffect(effect)
            fade = QPropertyAnimation(effect, b"opacity", self)
            fade.setStartValue(0.3)
            fade.setEndValue(1.0)
            fade.setDuration(180)
            fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade.finished.connect(lambda: screen.setGraphicsEffect(None) if self.stack.currentWidget() is screen else None)
            self.animation = fade
            fade.start()

    @staticmethod
    def _property(widget, name: str, value):
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _render_overlays(self):
        """Update both independent always-on-top windows."""
        self.overlay.render()
        self.alarm_overlay.render()

    def _changed(self):
        self._save_later.start()
        self._refresh_tiles()
        if self.scheduler.running:
            self.scheduler.configure(self.store.profile["slots"])
        self.notifier.sync(self.store.profile["alarms"])
        self._render_overlays()

    def _page_hotbar(self):
        scroll, v = self._page("Boosting hotbar", "First launch starts empty. Pick the item for each Roblox number key, choose a repeat interval, then tick Use.")
        steps, help_layout = panel()
        help_layout.addWidget(label("QUICK START  ·  3 SIMPLE STEPS", "Eyebrow"))
        instructions = label("1. Choose an item for a slot below.   2. Set 'Every' to how often it should be used.   3. Enable AUTO, then press Start (F1).", "Muted")
        instructions.setWordWrap(True)
        help_layout.addWidget(instructions)
        game_note = label("The floating red buttons are placed UNDER your actual Roblox hotbar. They do not copy or detect game items — assign the same items and keys here.", "Muted")
        game_note.setWordWrap(True)
        help_layout.addWidget(game_note)
        v.addWidget(steps)
        actions, actions_body = panel()
        tools = row(label("Overlay quick controls", "SectionTitle"))
        tools.addStretch(1)
        tools.addWidget(btn("Move overlay to default", self._reset_overlay_position, "SoftPurple", "Re-centre red buttons at the bottom of your screen"))
        tools.addWidget(btn("Move to screen bottom", self._move_overlay_to_screen_bottom, "SoftPurple", "Place the red buttons at the true bottom edge, including the taskbar area"))
        actions_body.addLayout(tools)
        actions_body.addWidget(checkbox("Show red AUTO buttons over Roblox", self.store.settings["overlay_hotbar_visible"],
                                        lambda on: self._set_setting("overlay_hotbar_visible", on)))
        actions_body.addWidget(checkbox("Show separate alarm timer overlay", self.store.settings["overlay_alarms_visible"],
                                        lambda on: self._set_setting("overlay_alarms_visible", on)))
        actions_body.addWidget(checkbox("Show next-use countdowns inside the AUTO buttons", self.store.settings["overlay_countdowns"],
                                        lambda on: self._set_setting("overlay_countdowns", on)))
        tip = label("Right-drag red buttons to move the hotbar. Right-drag an alarm timer to move alarms independently. Hidden buttons and alarms KEEP running.", "Muted")
        tip.setWordWrap(True)
        actions_body.addWidget(tip)
        v.addWidget(actions)
        visibility, visibility_body = panel()
        visibility_body.addWidget(label("Choose which AUTO buttons appear on-screen", "SectionTitle"))
        visibility_hint = label("Tick the slots you want to see. Hidden slots keep their Roblox positions and can still run normally. Use the 'Use' checkbox below to turn the actual macro on or off.", "Muted")
        visibility_hint.setWordWrap(True)
        visibility_body.addWidget(visibility_hint)
        visibility_row = QHBoxLayout()
        visibility_row.setSpacing(16)
        for slot in self.store.profile["slots"]:
            slot_key = slot["key"]
            visibility_row.addWidget(checkbox(f"Slot {slot_key}", slot.get("overlay_visible", True),
                                  lambda shown, target=slot: self._edit_slot(target, "overlay_visible", shown)))
        visibility_row.addStretch(1)
        visibility_body.addLayout(visibility_row)
        visibility_actions = row(
            btn("Show all 7", lambda: self._set_all_overlay_slots(True), "SoftPurple"),
            btn("Hide all 7", lambda: self._set_all_overlay_slots(False)))
        visibility_actions.addStretch(1)
        visibility_body.addLayout(visibility_actions)
        v.addWidget(visibility)
        p, body = panel()
        head = row(label("Your hotbar", "SectionTitle"))
        head.addStretch(1)
        head.addWidget(label("Click a slot to edit it below", "Muted"))
        body.addLayout(head)
        tiles = QHBoxLayout()
        tiles.setSpacing(9)
        for slot in self.store.profile["slots"]:
            k = slot["key"]
            b = btn("", lambda _=False, key=k: self._focus_slot(key), "HotbarKey")
            b.setMinimumHeight(91)
            b.setMinimumWidth(91)
            self.slot_tiles[k] = b
            tiles.addWidget(b, 1)
        body.addLayout(tiles)
        note = label("Slots match your Roblox number keys. Only enabled slots with an assigned item will fire.", "Muted")
        note.setWordWrap(True)
        body.addWidget(note)
        v.addWidget(p)
        p2, rules = panel()
        top = row(label("Item usage", "SectionTitle"))
        top.addStretch(1)
        top.addWidget(btn("Enable all assigned", lambda: self._toggle_all_slots(True), "SoftPurple"))
        top.addWidget(btn("Disable all", lambda: self._toggle_all_slots(False)))
        rules.addLayout(top)
        hint = label("Every = seconds between key presses.  Delay = seconds until the first key press after starting.", "Muted")
        hint.setWordWrap(True)
        rules.addWidget(hint)
        for slot in self.store.profile["slots"]:
            k = slot["key"]
            box = QFrame()
            box.setObjectName("SlotRow")
            lr = QHBoxLayout(box)
            lr.setContentsMargins(12, 11, 12, 11)
            lr.setSpacing(11)
            n = label(str(k), "Count")
            n.setFixedWidth(28)
            lr.addWidget(n)
            enabled = checkbox("Use", slot["enabled"], lambda checked, s=slot: self._edit_slot(s, "enabled", checked))
            lr.addWidget(enabled)
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(ITEMS)
            cb.setCurrentText(slot["item"])
            cb.setMinimumWidth(165)
            cb.currentTextChanged.connect(lambda value, s=slot: self._edit_slot(s, "item", value))
            lr.addWidget(cb, 2)
            self.slot_focus[k] = cb
            lr.addWidget(label("Every", "Muted"))
            every = QDoubleSpinBox()
            every.setDecimals(1)
            every.setRange(.1, 86400)
            every.setSuffix(" sec")
            every.setValue(slot["interval"])
            every.setMinimumWidth(101)
            every.valueChanged.connect(lambda value, s=slot: self._edit_slot(s, "interval", value))
            lr.addWidget(every)
            lr.addWidget(label("Delay", "Muted"))
            delay = QDoubleSpinBox()
            delay.setDecimals(1)
            delay.setRange(0, 86400)
            delay.setSuffix(" sec")
            delay.setValue(slot["delay"])
            delay.setMinimumWidth(101)
            delay.valueChanged.connect(lambda value, s=slot: self._edit_slot(s, "delay", value))
            lr.addWidget(delay)
            rules.addWidget(box)
        v.addWidget(p2)
        self._refresh_tiles()
        v.addStretch(1)
        return scroll

    def _focus_slot(self, key):
        widget = self.slot_focus.get(key)
        if widget:
            widget.setFocus()
            widget.showPopup()

    def _edit_slot(self, slot, name, value):
        slot[name] = value
        self._changed()

    def _toggle_overlay_slot(self, key: int):
        slot = next((s for s in self.store.profile["slots"] if s["key"] == key), None)
        if slot is None:
            return
        if slot["item"].strip().lower() in ("", "empty"):
            self.show_page("Hotbar")
            QMessageBox.information(self, "Set up this slot first",
                                    f"Choose an item for slot {key}, then click its red AUTO button again.")
            return
        slot["enabled"] = not slot["enabled"]
        self._changed()
        self._log(f"Slot {key} AUTO {'ON' if slot['enabled'] else 'OFF'} ({slot['item']})")

    def _set_all_overlay_slots(self, visible: bool):
        for slot in self.store.profile["slots"]:
            slot["overlay_visible"] = visible
        self._changed()
        self.show_page("Hotbar")
        self._log("Showing all hotbar overlay buttons" if visible else "Hiding all hotbar overlay buttons")

    def _toggle_all_slots(self, enabled: bool):
        for slot in self.store.profile["slots"]:
            slot["enabled"] = enabled and slot["item"].strip().lower() not in ("", "empty")
        self._changed()
        self.show_page("Hotbar")
        self._log("Enabled all configured slots" if enabled else "Disabled all slots")

    def _reset_overlay_position(self):
        self.store.settings["overlay_x"] = -1
        self.store.settings["overlay_y"] = -1
        self._changed()
        self._log("Overlay position reset to screen anchor")

    def _reset_alarm_overlay_position(self):
        self.store.settings["alarm_overlay_x"] = -1
        self.store.settings["alarm_overlay_y"] = -1
        self._changed()
        self._log("Alarm overlay position reset (hotbar position unchanged)")

    def _move_overlay_to_screen_bottom(self):
        """Allow positioning all the way to the physical screen edge."""
        self._render_overlays()
        screen = (QApplication.screenAt(self.overlay.frameGeometry().center())
                  or self.overlay.screen() or QApplication.primaryScreen())
        if screen is None:
            return
        r = screen.geometry()
        x, y = clamp_overlay_position(
            self.overlay.x(), bottom_edge_y(r.top(), r.height(), self.overlay.height()),
            r.left(), r.top(), r.width(), r.height(),
            self.overlay.width(), self.overlay.height())
        self.store.settings["overlay_x"] = x
        self.store.settings["overlay_y"] = y
        self._changed()
        self._log("Overlay moved to the bottom edge of the screen")

    def _refresh_tiles(self):
        for slot in self.store.profile["slots"]:
            tile = self.slot_tiles.get(slot["key"])
            if tile:
                item = slot["item"][:15]
                timer = f"{slot['interval']:g}s" if item.strip().lower() not in ("", "empty") else "—"
                tile.setText(f"{slot['key']}\n\n{item}\n{timer}")
                self._property(tile, "selected", bool(slot["enabled"]))

    def _page_timers(self):
        scroll, v = self._page("Macro timers", "Only configured hotbar items have schedules. Empty slots do not run any timers.")
        intro, intro_l = panel()
        head = row(label("Active timer schedule", "SectionTitle"))
        head.addStretch(1)
        head.addWidget(btn("Edit hotbar", lambda: self.show_page("Hotbar"), "SoftPurple"))
        intro_l.addLayout(head)
        intro_l.addWidget(label("Timers run only when the macro is started and the selected Roblox window is active.", "Muted"))
        v.addWidget(intro)
        configured = [slot for slot in self.store.profile["slots"]
                      if slot["item"].strip().lower() not in ("", "empty")]
        if not configured:
            empty, content = panel()
            content.addWidget(label("No timers yet", "SectionTitle"))
            content.addWidget(label("Your timers start empty. Go to Hotbar, choose an item and set its repeat interval.", "Muted"))
            content.addWidget(btn("Set up hotbar", lambda: self.show_page("Hotbar"), "SoftPurple"))
            v.addWidget(empty)
        for slot in configured:
            k = slot["key"]
            frame, vert = panel()
            head = row(label(f"Key {k}", "SectionTitle"), label(slot["item"], "Muted"))
            head.addStretch(1)
            count = label(str(self.slot_counts[k]) + " uses", "Muted")
            self.timer_count_labels[k] = count
            head.addWidget(count)
            vert.addLayout(head)
            settings = QHBoxLayout()
            settings.setSpacing(14)
            toggle = checkbox("Enabled", slot["enabled"], lambda value, s=slot: self._edit_slot(s, "enabled", value))
            settings.addWidget(toggle)
            settings.addWidget(label("Interval (sec)", "Muted"))
            interval = QDoubleSpinBox()
            interval.setDecimals(1)
            interval.setRange(.1, 86400)
            interval.setValue(slot["interval"])
            interval.valueChanged.connect(lambda value, s=slot: self._edit_slot(s, "interval", value))
            settings.addWidget(interval)
            settings.addWidget(label("First-use delay (sec)", "Muted"))
            delay = QDoubleSpinBox()
            delay.setDecimals(1)
            delay.setRange(0, 86400)
            delay.setValue(slot["delay"])
            delay.valueChanged.connect(lambda value, s=slot: self._edit_slot(s, "delay", value))
            settings.addWidget(delay)
            settings.addStretch(1)
            vert.addLayout(settings)
            v.addWidget(frame)
        v.addStretch(1)
        return scroll

    def _page_alarms(self):
        scroll, v = self._page("Alarms & overlay", "Set reset hotkeys, sound or voice alerts, and a separately movable alarm display.")
        toolbar, tools = panel()
        top = row(label("Your alarms", "SectionTitle"))
        top.addStretch(1)
        top.addWidget(btn("Start all", self.start_all_alarms, "SoftPurple"))
        top.addWidget(btn("+ New alarm", self.add_alarm, "Primary"))
        tools.addLayout(top)
        overlay_chk = checkbox("Show alarms in a separate movable overlay", self.store.settings["overlay_alarms_visible"],
                               lambda value: self._set_setting("overlay_alarms_visible", value))
        tools.addWidget(overlay_chk)
        tools.addWidget(btn("Reset alarm overlay position", self._reset_alarm_overlay_position, "SoftPurple"))
        tools.addWidget(label("A single key works (for example G or 8), or use a combination. Press it to silence and restart the countdown.", "Muted"))
        tools.addWidget(label("Warning: a single-key global shortcut may prevent Roblox or other apps from receiving that key while Bss Booster is open.", "Muted"))
        tools.addWidget(label("A hidden alarm still counts down AND plays Sound/Voice. You control display and sound separately. Use windowed/borderless for the overlay.", "Muted"))
        v.addWidget(toolbar)
        if not self.store.profile["alarms"]:
            empty, layout = panel()
            layout.addWidget(label("No alarms yet. Click + New alarm to add one."))
            v.addWidget(empty)
        for alarm in self.store.profile["alarms"]:
            frame, contents = panel("AlarmCard")
            arow = QHBoxLayout()
            arow.setSpacing(8)
            name = QLineEdit(alarm["name"])
            name.setMaxLength(70)
            name.setPlaceholderText("Alarm name")
            name.textEdited.connect(lambda text, a=alarm: self._edit_alarm(a, "name", text))
            name.setMinimumWidth(150)
            arow.addWidget(name, 1)
            timer = label(human_time(self.clock.time_left(alarm["id"])), "Timer")
            timer.setMinimumWidth(91)
            timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.alarm_time_labels[alarm["id"]] = timer
            arow.addWidget(timer)
            arow.addWidget(btn("▶", lambda _=False, a=alarm: self._alarm_start(a), "SoftPurple", "Start/resume"))
            arow.addWidget(btn("Ⅱ", lambda _=False, a=alarm: self._alarm_pause(a), "", "Pause"))
            arow.addWidget(btn("↺", lambda _=False, a=alarm: self._alarm_reset(a), "", "Silence + restart timer"))
            arow.addWidget(btn("Silence", lambda _=False, a=alarm: self._alarm_silence(a), "", "Stop alarm audio"))
            arow.addWidget(btn("Test", lambda _=False, a=alarm: self._alarm_test(a), "", "Test this alarm sound or voice"))
            arow.addWidget(btn("×", lambda _=False, a=alarm: self._alarm_delete(a), "Danger", "Delete"))
            contents.addLayout(arow)
            duration_line = QHBoxLayout()
            duration_line.setSpacing(9)
            duration_line.addWidget(checkbox("On", alarm["enabled"],
                                             lambda value, a=alarm: self._edit_alarm(a, "enabled", value)))
            duration_line.addSpacing(7)
            duration_line.addWidget(label("Duration", "Muted"))
            duration = alarm["duration"]
            h, rem = divmod(duration, 3600)
            m, s = divmod(rem, 60)
            hspin = QSpinBox(); hspin.setRange(0, 999); hspin.setValue(h); hspin.setSuffix(" h")
            mspin = QSpinBox(); mspin.setRange(0, 59); mspin.setValue(m); mspin.setSuffix(" m")
            sspin = QSpinBox(); sspin.setRange(0, 59); sspin.setValue(s); sspin.setSuffix(" s")
            for sp in (hspin, mspin, sspin):
                sp.setFixedWidth(73)
                duration_line.addWidget(sp)
            def duration_changed(_=None, a=alarm, hs=hspin, ms=mspin, ss=sspin):
                seconds = max(1, hs.value()*3600 + ms.value()*60 + ss.value())
                a["duration"] = seconds
                if not self.clock.runtime[a["id"]].running:
                    self.clock.reset(a)
                self._changed()
            for sp in (hspin, mspin, sspin):
                sp.valueChanged.connect(duration_changed)
            duration_line.addStretch(1)
            duration_line.addWidget(checkbox("Repeat", alarm["repeat"],
                                             lambda value, a=alarm: self._edit_alarm(a, "repeat", value)))
            duration_line.addWidget(checkbox("Show on screen", alarm["overlay"],
                                             lambda value, a=alarm: self._edit_alarm(a, "overlay", value)))
            contents.addLayout(duration_line)
            alert_line = QHBoxLayout()
            alert_line.setSpacing(12)
            alert_line.addWidget(label("Alert style", "Muted"))
            style = QComboBox()
            style.addItems(["Off", "Sound", "Voice"])
            style.setCurrentText(alarm["alert_mode"])
            style.setToolTip("Sound: bundled repeating chime. Voice: Windows speech repeats the alarm name.")
            style.currentTextChanged.connect(lambda value, a=alarm: self._edit_alarm(a, "alert_mode", value))
            alert_line.addWidget(style)
            alert_line.addSpacing(12)
            alert_line.addWidget(label("Reset shortcut", "Muted"))
            shortcut = QKeySequenceEdit()
            shortcut.setMaximumWidth(170)
            shortcut.setKeySequence(QKeySequence(alarm.get("keybind", "")))
            shortcut.setToolTip("Press one key (e.g. G or 8), F4–F12, or a combination. Warning: plain keys can block that key in Roblox while the app runs.")
            if hasattr(shortcut, "setMaximumSequenceLength"):
                shortcut.setMaximumSequenceLength(1)
            shortcut.editingFinished.connect(
                lambda a=alarm, widget=shortcut: self._set_alarm_keybind(a, widget))
            alert_line.addWidget(shortcut)
            alert_line.addWidget(btn("Clear", lambda _=False, a=alarm, w=shortcut: self._clear_alarm_keybind(a, w), "", "Remove alarm reset shortcut"))
            alert_line.addStretch(1)
            contents.addLayout(alert_line)
            v.addWidget(frame)
        v.addStretch(1)
        return scroll

    def _edit_alarm(self, alarm, key, value):
        alarm[key] = value
        if key == "enabled" and not value:
            self.clock.pause(alarm["id"])
            self.notifier.acknowledge(alarm["id"])
        self._changed()
        if key == "enabled":
            self._sync_hotkeys()

    def _set_alarm_keybind(self, alarm, widget):
        raw = widget.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        normalized = normalize_hotkey(raw)
        if raw and not normalized:
            QMessageBox.warning(self, "Unsupported shortcut",
                                "Press a single key (e.g. G, 8 or Space), F4–F12, "
                                "or a key combination. F1–F3 are reserved for the macro.")
            widget.setKeySequence(QKeySequence(alarm.get("keybind", "")))
            return
        if normalized and any(a["id"] != alarm["id"] and a.get("keybind") == normalized
                              for a in self.store.profile["alarms"]):
            QMessageBox.warning(self, "Shortcut already used",
                                f"Another alarm already uses {normalized}. Choose a different keybind.")
            widget.setKeySequence(QKeySequence(alarm.get("keybind", "")))
            return
        alarm["keybind"] = normalized
        self._changed()
        self._sync_hotkeys()
        if normalized:
            self._log(f"{alarm['name']} reset shortcut: {normalized}")

    def _clear_alarm_keybind(self, alarm, widget):
        alarm["keybind"] = ""
        widget.clear()
        self._changed()
        self._sync_hotkeys()

    def _restart_by_alarm_id(self, alarm_id: str):
        alarm = next((a for a in self.store.profile["alarms"] if a["id"] == alarm_id), None)
        if alarm and alarm["enabled"]:
            self._alarm_reset(alarm)

    def _alarm_test(self, alarm):
        if alarm["alert_mode"] == "Off":
            QMessageBox.information(self, "No alarm audio", "Select Sound or Voice first.")
            return
        self.notifier.trigger(alarm)
        self._render_overlays()
        self._log(f"Testing {alarm['alert_mode'].lower()} alert: {alarm['name']}")

    def _alarm_silence(self, alarm):
        self.notifier.acknowledge(alarm["id"])
        self._render_overlays()

    def _alarm_start(self, alarm):
        self.notifier.acknowledge(alarm["id"])
        self.clock.start(alarm)
        self._render_overlays()

    def _alarm_pause(self, alarm):
        self.notifier.acknowledge(alarm["id"])
        self.clock.pause(alarm["id"])
        self._render_overlays()

    def _alarm_reset(self, alarm):
        self.notifier.acknowledge(alarm["id"])
        self.clock.reset(alarm)
        self.clock.start(alarm)
        self._render_overlays()
        self._log(f"Restarted alarm: {alarm['name']}")

    def _alarm_delete(self, alarm):
        if QMessageBox.question(self, "Delete alarm", f"Delete '{alarm['name']}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.store.profile["alarms"][:] = [a for a in self.store.profile["alarms"] if a["id"] != alarm["id"]]
        self.clock.configure(self.store.profile["alarms"])
        self._changed()
        self._sync_hotkeys()
        self.show_page("Alarms")

    def add_alarm(self):
        name, ok = QInputDialog.getText(self, "New alarm", "Alarm name:", text="Custom alarm")
        if not ok or not name.strip():
            return
        a = make_alarm(name.strip(), 300)
        self.store.profile["alarms"].append(a)
        self.clock.configure(self.store.profile["alarms"])
        self._changed()
        self._sync_hotkeys()
        self.show_page("Alarms")
        self._log(f"Created alarm: {name.strip()}")

    def start_all_alarms(self):
        for a in self.store.profile["alarms"]:
            self.clock.start(a)
        self._render_overlays()
        self._log("Started all enabled alarms")

    def _page_profiles(self):
        scroll, v = self._page("Profiles", "Save different hotbar setups and alarm collections for different kinds of boosts.")
        p, body = panel()
        top = row(label("Boost presets", "SectionTitle"))
        top.addStretch(1)
        top.addWidget(btn("+ Duplicate current", self.add_profile, "Primary"))
        body.addLayout(top)
        body.addWidget(label("Switching presets safely stops your macro and loads that preset's slots and alarms.", "Muted"))
        for name, prof in self.store.data["profiles"].items():
            item, layout = panel("SlotRow")
            heading = row(label(name, "SectionTitle"))
            heading.addStretch(1)
            heading.addWidget(label(f"{sum(s['enabled'] for s in prof['slots'])} enabled slots   ·   {len(prof['alarms'])} alarms", "Muted"))
            if name == self.store.data["active_profile"]:
                heading.addWidget(label("●  ACTIVE", "Eyebrow"))
            else:
                heading.addWidget(btn("Load", lambda _=False, n=name: self.switch_profile(n), "SoftPurple"))
            layout.addLayout(heading)
            body.addWidget(item)
        options = row(btn("Import preset", self.import_profile), btn("Export current preset", self.export_profile),
                      btn("Delete active preset", self.delete_profile, "Danger"))
        options.addStretch(1)
        body.addLayout(options)
        v.addWidget(p)
        v.addStretch(1)
        return scroll

    def add_profile(self):
        name, ok = QInputDialog.getText(self, "New preset", "Name for a copy of the current preset:")
        if not ok:
            return
        if not self.store.clone_profile(name):
            QMessageBox.warning(self, "Preset name", "Enter a unique, non-empty name.")
            return
        self._activate_profile()

    def switch_profile(self, name: str):
        if not name or name == self.store.data["active_profile"] or name not in self.store.data["profiles"]:
            return
        self.store.data["active_profile"] = name
        self._activate_profile()

    def _activate_profile(self):
        self.scheduler.stop()
        self.slot_counts = {n: 0 for n in range(1, 8)}
        self.clock.stop_all()
        self.notifier.sync([])
        self.clock = AlarmClock()
        self.clock.configure(self.store.profile["alarms"])
        self.alarm_overlay.clock = self.clock
        self.alarm_overlay._alarm_order = ()
        self._fill_profile_selector()
        self._changed()
        self._sync_hotkeys()
        self.show_page(self.current_page or "Hotbar")
        self._update_controls()
        self._log("Loaded preset: " + self.store.data["active_profile"])

    def delete_profile(self):
        profiles = self.store.data["profiles"]
        if len(profiles) <= 1:
            QMessageBox.information(self, "Keep one preset", "You need at least one preset.")
            return
        current = self.store.data["active_profile"]
        if QMessageBox.question(self, "Delete preset", f"Delete preset '{current}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        del profiles[current]
        self.store.data["active_profile"] = next(iter(profiles))
        self._activate_profile()

    def export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export preset", "bss-booster-preset.json", "JSON (*.json)")
        if path:
            try:
                Path(path).write_text(json.dumps(self.store.profile, indent=2) + "\n", encoding="utf-8")
                self._log(f"Exported preset: {Path(path).name}")
            except OSError as exc:
                QMessageBox.critical(self, "Export failed", str(exc))

    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import preset", "", "JSON (*.json)")
        if not path:
            return
        try:
            if os.path.getsize(path) > 2_000_000:
                raise ValueError("Preset file is too large.")
            parsed = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(parsed, dict) or not isinstance(parsed.get("slots"), list):
                raise ValueError("Not a valid Bss Booster preset file.")
            candidate = validated_profile(parsed)
            suggested = Path(path).stem[:40]
            name, ok = QInputDialog.getText(self, "Import preset", "Name for imported preset:", text=suggested)
            if not ok or not name.strip():
                return
            name = name.strip()[:50]
            if name in self.store.data["profiles"]:
                QMessageBox.warning(self, "Already exists", "A preset with that name already exists.")
                return
            self.store.data["profiles"][name] = candidate
            self.store.data["active_profile"] = name
            self._activate_profile()
        except (OSError, ValueError, UnicodeError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))

    def _page_status(self):
        scroll, v = self._page("Status", "See what your macro has used and whether it is able to send hotbar keys.")
        grid = QHBoxLayout()
        grid.setSpacing(14)
        a, al = panel()
        al.addWidget(label("Macro state", "Muted"))
        self.big_status = label("Ready", "Count")
        al.addWidget(self.big_status)
        grid.addWidget(a)
        b, bl = panel()
        bl.addWidget(label("Keys sent", "Muted"))
        bl.addWidget(label(str(sum(self.slot_counts.values())), "Count"))
        grid.addWidget(b)
        c, cl = panel()
        cl.addWidget(label("Current preset", "Muted"))
        cl.addWidget(label(self.store.data["active_profile"], "Count"))
        grid.addWidget(c)
        v.addLayout(grid)
        logs, log_l = panel()
        log_l.addWidget(label("Session activity", "SectionTitle"))
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlainText("\n".join(self.log_lines))
        self.log_text.setMinimumHeight(230)
        log_l.addWidget(self.log_text)
        head = row(btn("Clear session log", self.clear_log))
        head.addStretch(1)
        log_l.addLayout(head)
        v.addWidget(logs)
        v.addStretch(1)
        return scroll

    def clear_log(self):
        self.log_lines.clear()
        if hasattr(self, "log_text") and self.current_page == "Status":
            self.log_text.clear()

    def _page_settings(self):
        scroll, v = self._page("Settings", "Choose how macros run, which overlay sections appear, and exactly how the red AUTO buttons line up.")
        p, layout = panel()
        layout.addWidget(label("Macro safety & controls", "SectionTitle"))
        layout.addWidget(checkbox("Only send keys while Roblox is the active window (recommended)",
                                   self.store.settings["focus_only"],
                                   lambda value: self._set_setting("focus_only", value)))
        layout.addWidget(label("Active window must contain this text:", "Muted"))
        field = QLineEdit(self.store.settings["target_title"])
        field.setPlaceholderText("Roblox")
        field.setMaximumWidth(350)
        field.textEdited.connect(lambda val: self._set_setting("target_title", val))
        layout.addWidget(field)
        layout.addWidget(checkbox("Enable global macro + alarm shortcuts (Windows)", self.store.settings["hotkeys"],
                                   lambda val: self._set_setting("hotkeys", val)))
        layout.addWidget(label("Alarm reset keys work globally while Bss Booster is open. Duplicate or system-reserved shortcuts may fail.", "Muted"))
        layout.addWidget(checkbox("Start enabled alarms when the macro starts", self.store.settings["start_alarms_with_macro"],
                                   lambda val: self._set_setting("start_alarms_with_macro", val)))
        v.addWidget(p)
        p, layout = panel()
        layout.addWidget(label("In-game hotbar & alarm overlay", "SectionTitle"))
        layout.addWidget(checkbox("Show red hotbar AUTO buttons", self.store.settings["overlay_hotbar_visible"],
                                   lambda val: self._set_setting("overlay_hotbar_visible", val)))
        layout.addWidget(checkbox("Show alarm timers (even without hotbar buttons)", self.store.settings["overlay_alarms_visible"],
                                   lambda val: self._set_setting("overlay_alarms_visible", val)))
        layout.addWidget(checkbox("Display hotbar countdowns inside AUTO buttons", self.store.settings["overlay_countdowns"],
                                   lambda val: self._set_setting("overlay_countdowns", val)))
        layout.addWidget(checkbox("Click-through mode (both overlays cannot be clicked or dragged)", self.store.settings["overlay_clickthrough"],
                                   lambda val: self._set_setting("overlay_clickthrough", val)))
        layout.addWidget(label("RIGHT-DRAG a red button to move the hotbar. RIGHT-DRAG an alarm chip to move alarms independently. Both positions save automatically.", "Muted"))
        layout.addWidget(btn("Reset overlay position", self._reset_overlay_position, "SoftPurple"))
        layout.addWidget(btn("Move hotbar to screen bottom", self._move_overlay_to_screen_bottom, "SoftPurple"))
        layout.addWidget(btn("Reset alarm overlay position (independent)", self._reset_alarm_overlay_position, "SoftPurple"))
        for setting_key, text, lower, upper in (
                ("overlay_scale", "Button size", 60, 150),
                ("overlay_spacing", "Distance between buttons", 0, 80)):
            settings_row = row(label(text))
            settings_row.addStretch(1)
            selector = QSpinBox()
            selector.setRange(lower, upper)
            selector.setValue(self.store.settings[setting_key])
            selector.setSuffix("%" if setting_key == "overlay_scale" else " px")
            selector.setFixedWidth(95)
            selector.valueChanged.connect(lambda value, key=setting_key: self._set_setting(key, value))
            settings_row.addWidget(selector)
            layout.addLayout(settings_row)
        corner = row(label("Screen position"))
        corner.addStretch(1)
        cb = QComboBox()
        cb.addItems(["Top left", "Top center", "Top right", "Bottom left", "Bottom center", "Bottom right"])
        cb.setCurrentText(self.store.settings["overlay_corner"])
        cb.currentTextChanged.connect(lambda val: self._set_setting("overlay_corner", val))
        corner.addWidget(cb)
        layout.addLayout(corner)
        v.addWidget(p)
        p, layout = panel()
        layout.addWidget(label("Appearance", "SectionTitle"))
        layout.addWidget(label("OFF buttons use #FF0000 at 20% opacity; ON buttons switch to a small green pill. Gotham Regular is used when installed (Segoe UI fallback).", "Muted"))
        rr = row(label("App theme"))
        rr.addStretch(1)
        theme = QComboBox()
        theme.addItems(["Light", "Dark"])
        theme.setCurrentText(self.store.settings["theme"])
        theme.currentTextChanged.connect(lambda val: self._set_setting("theme", val))
        rr.addWidget(theme)
        layout.addLayout(rr)
        layout.addWidget(checkbox("Enable subtle page animations", self.store.settings["animations"],
                                   lambda val: self._set_setting("animations", val)))
        layout.addWidget(label(f"Settings file: {self.store.path}", "Muted"))
        v.addWidget(p)
        v.addStretch(1)
        return scroll

    def _set_setting(self, key, value):
        self.store.settings[key] = value
        if key == "overlay_corner":
            # Choosing a new anchor overrides a prior manual right-drag position.
            self.store.settings["overlay_x"] = -1
            self.store.settings["overlay_y"] = -1
        self._changed()
        if key == "theme":
            self.setStyleSheet(stylesheet(value))
        if key == "hotkeys":
            self._sync_hotkeys()

    def _sync_hotkeys(self):
        if not hasattr(self, "hotkeys"):
            return
        self.hotkeys.unregister()
        if self.store.settings["hotkeys"]:
            self.hotkeys.register(self.store.profile["alarms"])
            if self.hotkeys.failures:
                self._log("Unavailable global shortcuts: " + ", ".join(self.hotkeys.failures))

    def _action_by_name(self, action):
        {"start": self.start_macro, "pause": self.pause_macro, "stop": self.stop_macro}[action]()

    def start_macro(self):
        if self.scheduler.running:
            if self.scheduler.paused:
                self.scheduler.resume()
                self._log("Boosting macro resumed")
            return
        active = [s for s in self.store.profile["slots"] if s["enabled"] and s["item"].strip().lower() != "empty"]
        if not active:
            self._log("No slots enabled. Enable a hotbar slot to start.")
            QMessageBox.information(self, "No active slots", "Enable at least one hotbar slot with an item before starting.")
            return
        self.scheduler.start(self.store.profile["slots"])
        if self.store.settings["start_alarms_with_macro"]:
            self.start_all_alarms()
        self._log(f"Boosting started ({len(active)} enabled slots). Switch to Roblox to send keys.")
        self._update_controls()

    def pause_macro(self):
        if self.scheduler.running and not self.scheduler.paused:
            self.scheduler.pause()
            self._log("Boosting macro paused")
        self._update_controls()

    def stop_macro(self):
        if self.scheduler.running:
            self.scheduler.stop()
            self._log("Boosting macro stopped")
        self._update_controls()

    def _tick(self):
        focused = (not self.store.settings["focus_only"] or
                   WindowsKeyboard.focused(self.store.settings["target_title"]))
        for key in self.scheduler.due(can_send=focused and os.name == "nt"):
            if WindowsKeyboard.send(key):
                self.slot_counts[key] += 1
                rule = next((r for r in self.store.profile["slots"] if r["key"] == key), None)
                self._log(f"Key {key}  ·  {rule['item'] if rule else 'Item'}")
            else:
                self._log(f"Unable to send key {key}. Check Windows permissions and focus.")
        finished = self.clock.tick(self.store.profile["alarms"])
        if finished:
            for aid in finished:
                alarm = next((a for a in self.store.profile["alarms"] if a["id"] == aid), None)
                if alarm:
                    self._log(f"Alarm finished: {alarm['name']}")
                    self.notifier.trigger(alarm)
        self._update_controls(focused)
        if self.current_page == "Alarms":
            for alarm in self.store.profile["alarms"]:
                lbl = self.alarm_time_labels.get(alarm["id"])
                if lbl:
                    lbl.setText("ALERT!" if self.notifier.is_alerting(alarm["id"]) else human_time(self.clock.time_left(alarm["id"])))
        if self.current_page == "Timers":
            for key, widget in self.timer_count_labels.items():
                widget.setText(str(self.slot_counts[key]) + " uses")
        self._render_overlays()

    def _update_controls(self, focused: bool | None = None):
        if not hasattr(self, "start_btn"):
            return
        if not self.scheduler.running:
            status = "Ready"
        elif self.scheduler.paused:
            status = "Paused"
        elif focused is False and self.store.settings["focus_only"]:
            status = "Waiting for Roblox"
        else:
            status = "Running"
        self.status_label.setText(status)
        self.activity_label.setText(f"{sum(self.slot_counts.values())} keys sent")
        self.start_btn.setEnabled(not self.scheduler.running or self.scheduler.paused)
        self.start_btn.setText("▶   Resume    F1" if self.scheduler.paused else "▶   Start     F1")
        self.pause_btn.setEnabled(self.scheduler.running and not self.scheduler.paused)
        self.stop_btn.setEnabled(self.scheduler.running)
        if self.current_page == "Status" and hasattr(self, "big_status"):
            self.big_status.setText(status)

    def _log(self, msg: str):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}]  {msg}"
        self.log_lines.append(entry)
        if len(self.log_lines) > 500:
            self.log_lines.pop(0)
        if self.current_page == "Status" and hasattr(self, "log_text"):
            self.log_text.appendPlainText(entry)

    def closeEvent(self, event):
        self._pulse.stop()
        self.scheduler.stop()
        self.notifier.close()
        self.hotkeys.unregister()
        QApplication.instance().removeNativeEventFilter(self.hotkeys)
        self.overlay.close()
        self.alarm_overlay.close()
        self.store.save()
        super().closeEvent(event)
