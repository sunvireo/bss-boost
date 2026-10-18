"""Independent, frameless in-game overlays for hotbar buttons and alarm timers.

The hotbar keeps seven fixed slot columns even when some buttons are hidden;
this makes the remaining buttons stay aligned with their Roblox slots.
Alarms live in a second native window, which can be moved and hidden separately.
"""
from __future__ import annotations

import time
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QRegion
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .config import human_time
from .overlay_geometry import clamp_overlay_position


OVERLAY_FLAGS = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                 Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)


def _full_display(window):
    """Return full screen rectangle, not the work area limited by the taskbar."""
    screen = (QApplication.screenAt(window.frameGeometry().center())
              or window.screen() or QApplication.primaryScreen())
    return screen.geometry() if screen is not None else None


class _DraggableOverlayItem:
    """Right-drag any visible pill/chip to move its OWN overlay window."""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = self.overlay_owner.pos()
            self.overlay_owner._dragging = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and (event.buttons() & Qt.MouseButton.RightButton):
            self.overlay_owner.move(self._window_origin + event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self._drag_origin is not None:
            self._drag_origin = None
            self.overlay_owner._dragging = False
            self.overlay_owner.remember_position()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class AutoPill(_DraggableOverlayItem, QPushButton):
    def __init__(self, key: int, toggle, overlay):
        super().__init__("AUTO: OFF")
        self.key = key
        self.overlay_owner = overlay
        self._drag_origin = None
        self._window_origin = None
        self.clicked.connect(lambda: toggle(key))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"Toggle automatic use for Roblox slot {key}")
        self.setToolTip(f"Slot {key}: left-click to toggle. Right-drag to move the red buttons.")


class HotbarOverlay(QWidget):
    def __init__(self, store, clock, notifier, scheduler, toggle_slot):
        super().__init__(None, OVERLAY_FLAGS)
        self.setObjectName("BssCleanOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Visual transparency only: never make this window ignore mouse input.
        # Earlier versions used WindowTransparentForInput and could not be dragged
        # reliably again after disabling it; the feature has been removed.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.store, self.scheduler = store, scheduler
        self.buttons: dict[int, AutoPill] = {}
        self.button_holders: dict[int, QWidget] = {}
        self._dragging = False
        self.setStyleSheet("""
            QWidget#BssCleanOverlay { background: transparent; }
            QPushButton#AutoPill {
                font-family: 'Gotham', 'Segoe UI', Arial;
                font-size: 9px; font-weight: 400;
                color: rgba(0, 0, 0, 89);
                background: rgba(255, 0, 0, 51);
                border: none; border-radius: 9px; padding: 0;
            }
            QPushButton#AutoPill[active="true"] {
                color: rgba(0, 0, 0, 168);
                background: rgba(154, 232, 92, 230); border: none;
            }
            QPushButton#AutoPill:hover { border: none; }
        """)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.button_area = QWidget()
        self.button_layout = QHBoxLayout(self.button_area)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        for key in range(1, 8):
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.addStretch(1)
            button = AutoPill(key, toggle_slot, self)
            button.setObjectName("AutoPill")
            holder_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            holder_layout.addStretch(1)
            self.button_layout.addWidget(holder)
            self.button_holders[key] = holder
            self.buttons[key] = button
        main.addWidget(self.button_area)

    def remember_position(self):
        self.store.settings["overlay_x"] = self.x()
        self.store.settings["overlay_y"] = self.y()
        self.store.save()

    def render(self):
        prefs = self.store.settings
        slots = self.store.profile["slots"]
        assigned_any = any(s["item"].strip().lower() not in ("", "empty") for s in slots)
        shown_slots = {s["key"] for s in slots if s.get("overlay_visible", True)}
        show = prefs["overlay_hotbar_visible"] and assigned_any and bool(shown_slots)
        if not show:
            self.hide()
            return

        scale = prefs["overlay_scale"] / 100.0
        w = max(53, round(53 * scale))
        h = max(19, round((32 if prefs["overlay_countdowns"] else 19) * scale))
        step = w + round(prefs["overlay_spacing"] * scale)
        self.button_area.setFixedSize(7 * step, h)
        self.setFixedSize(7 * step, h)
        now = time.monotonic()
        for slot in slots:
            key = slot["key"]
            button = self.buttons[key]
            self.button_holders[key].setFixedSize(step, h)
            button.setFixedSize(w, h)
            # Hide the real button but NOT its fixed-width slot column.
            button.setVisible(key in shown_slots)
            assigned = slot["item"].strip().lower() not in ("", "empty")
            active = assigned and slot["enabled"]
            caption = "AUTO: ON" if active else "AUTO: OFF"
            if prefs["overlay_countdowns"] and active:
                if not self.scheduler.running:
                    extra = "READY"
                elif self.scheduler.paused:
                    extra = "PAUSED"
                else:
                    left = max(0, self.scheduler.next_due.get(key, now) - now)
                    extra = f"{left:.1f}s" if left < 60 else human_time(left)
                caption += "\n" + extra
            button.setText(caption)
            button.setToolTip(f"{slot['item']} — slot {key}\nLeft-click: toggle AUTO\nRight-drag: move hotbar buttons")
            if button.property("active") != active:
                button.setProperty("active", active)
                button.style().unpolish(button)
                button.style().polish(button)

        if not self.isVisible():
            self.show()
        self.layout().activate()
        self.button_layout.activate()
        # Only visible pills capture mouse events; hidden slot locations pass through.
        region = QRegion()
        for key in shown_slots:
            button = self.buttons[key]
            region = region.united(QRegion(QRect(button.mapTo(self, QPoint(0, 0)), button.size())))
        self.setMask(region)

        screen = _full_display(self)
        if screen is None:
            return
        if prefs["overlay_x"] >= 0 and prefs["overlay_y"] >= 0:
            x, y = prefs["overlay_x"], prefs["overlay_y"]
        else:
            anchor = prefs["overlay_corner"]
            x = screen.center().x() - self.width() // 2 if "center" in anchor.lower() else (
                screen.left() + 16 if "left" in anchor.lower() else screen.right() - self.width() - 16)
            y = screen.top() + 20 if anchor.startswith("Top") else screen.bottom() - self.height() - 59
        x, y = clamp_overlay_position(x, y, screen.left(), screen.top(),
                                      screen.width(), screen.height(), self.width(), self.height())
        if not self._dragging and self.pos() != QPoint(x, y):
            self.move(x, y)


class AlarmChip(_DraggableOverlayItem, QLabel):
    def __init__(self, overlay):
        super().__init__()
        self.overlay_owner = overlay
        self._drag_origin = None
        self._window_origin = None
        self.setObjectName("AlarmChip")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip("Right-drag to move the alarm timers separately from the hotbar buttons.")


class AlarmOverlay(QWidget):
    """Own topmost window, independent screen position and visibility from hotbar."""
    def __init__(self, store, clock, notifier):
        super().__init__(None, OVERLAY_FLAGS)
        self.setObjectName("BssAlarmOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Visual transparency only: never make this window ignore mouse input.
        # Earlier versions used WindowTransparentForInput and could not be dragged
        # reliably again after disabling it; the feature has been removed.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.store, self.clock, self.notifier = store, clock, notifier
        self._dragging = False
        self._alarm_widgets: dict[str, AlarmChip] = {}
        self._alarm_order: tuple[str, ...] = ()
        self.setStyleSheet("""
            QWidget#BssAlarmOverlay { background: transparent; }
            QLabel#AlarmChip {
                font-family: 'Gotham', 'Segoe UI', Arial;
                background: rgba(250, 247, 251, 215);
                color: #292733; border: 1px solid rgba(104, 87, 124, 60);
                border-radius: 12px; padding: 6px 12px; font-size: 12px;
            }
        """)
        self.alarm_layout = QHBoxLayout(self)
        self.alarm_layout.setContentsMargins(0, 0, 0, 0)
        self.alarm_layout.setSpacing(4)

    def remember_position(self):
        self.store.settings["alarm_overlay_x"] = self.x()
        self.store.settings["alarm_overlay_y"] = self.y()
        self.store.save()

    def render(self):
        prefs = self.store.settings
        alarms = ([a for a in self.store.profile["alarms"] if a["enabled"] and a["overlay"]]
                  if prefs["overlay_alarms_visible"] else [])
        if not alarms:
            self.hide()
            return
        ids = tuple(a["id"] for a in alarms)
        if ids != self._alarm_order:
            for chip in self._alarm_widgets.values():
                self.alarm_layout.removeWidget(chip)
                chip.deleteLater()
            self._alarm_widgets.clear()
            for alarm in alarms:
                chip = AlarmChip(self)
                self.alarm_layout.addWidget(chip)
                self._alarm_widgets[alarm["id"]] = chip
            self._alarm_order = ids
        for alarm in alarms:
            remaining = ("ALARM!" if self.notifier.is_alerting(alarm["id"])
                         else human_time(self.clock.time_left(alarm["id"])))
            self._alarm_widgets[alarm["id"]].setText(f"{alarm['name'][:22]}  {remaining}")
        self.alarm_layout.activate()
        self.adjustSize()
        if not self.isVisible():
            self.show()
        self.alarm_layout.activate()
        region = QRegion()
        for chip in self._alarm_widgets.values():
            region = region.united(QRegion(QRect(chip.mapTo(self, QPoint(0, 0)), chip.size())))
        self.setMask(region)
        screen = _full_display(self)
        if screen is None:
            return
        if prefs["alarm_overlay_x"] >= 0 and prefs["alarm_overlay_y"] >= 0:
            x, y = prefs["alarm_overlay_x"], prefs["alarm_overlay_y"]
        else:
            # Above the hotbar by default, not anchored to or moved with it.
            x = screen.center().x() - self.width() // 2
            y = screen.bottom() - self.height() - 148
        x, y = clamp_overlay_position(x, y, screen.left(), screen.top(),
                                      screen.width(), screen.height(), self.width(), self.height())
        if not self._dragging and self.pos() != QPoint(x, y):
            self.move(x, y)
