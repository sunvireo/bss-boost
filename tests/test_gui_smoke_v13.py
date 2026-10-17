"""Runs with PySide6 on the GitHub Windows builder. Skipped without PySide6."""
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from bss_booster.config import Store, make_alarm
from bss_booster.ui import BoosterWindow


def test_gui_and_overlay_can_render(tmp_path):
    app = QApplication.instance() or QApplication([])
    project = Path(__file__).resolve().parents[1]
    store = Store(tmp_path / 'settings.json')
    win = BoosterWindow(store, project / 'assets' / 'bss_booster_icon.png')
    try:
        slot = store.profile['slots'][1]
        slot.update(item='Gumdrops', enabled=False, interval=2.0)
        win._changed()
        assert win.overlay.buttons[2].text().startswith('AUTO: OFF')
        # Clicking the overlay enables just this slot and persists on close.
        win.overlay.buttons[2].click()
        assert slot['enabled'] is True
        assert win.overlay.buttons[2].text().startswith('AUTO: ON')
        store.settings['overlay_hotbar_visible'] = False
        win.overlay.render()
        assert not win.overlay.button_area.isVisible()
        alarm = make_alarm('Glitter', 30)
        store.profile['alarms'].append(alarm)
        win.clock.configure(store.profile['alarms'])
        win.clock.start(alarm, 100)
        win.overlay.render()
        assert len(win.alarm_overlay._alarm_widgets) == 1
        assert win.alarm_overlay.isVisible()
        store.settings['overlay_alarms_visible'] = False
        win.overlay.render()
        assert not win.alarm_overlay.isVisible()
        assert win.clock.time_left(alarm['id'], 115) == 15
        # Hiding a slot is purely visual; its column stays in place.
        store.settings['overlay_hotbar_visible'] = True
        slot['overlay_visible'] = False
        win._changed()
        assert win.overlay.buttons[2].isHidden()
        assert win.overlay.button_holders[2].width() == win.overlay.button_holders[3].width()
        assert slot['enabled'] is True
        slot['overlay_visible'] = True
        win._changed()
        assert not win.overlay.buttons[2].isHidden()
        store.settings['overlay_alarms_visible'] = True
        win.alarm_overlay.render()
        assert win.alarm_overlay.isVisible()
        win.show_page('Settings')
        win.show_page('Timers')
        win.show_page('Alarms')
    finally:
        win.close()
        app.processEvents()
