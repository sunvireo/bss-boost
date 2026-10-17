import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bss_booster.config import Store, make_alarm, validated_data, validated_profile
from bss_booster.engine import AlarmClock
from bss_booster.hotkey_codec import parse_hotkey, normalize_hotkey
from bss_booster.notifier import AlarmNotifier


def test_alarm_defaults_reset_keys_and_sound(tmp_path):
    data = validated_data({"schema": 2, "profiles": {"Default": {"alarms": [], "slots": []}}})
    assert data["profiles"]["Default"]["alarms"] == []
    s = Store(tmp_path / 'new.json')
    alarms = s.profile['alarms']
    assert alarms == []  # no sample alarms on the first launch
    assert [a['item'] for a in s.profile['slots']] == ['Empty'] * 7
    assert all(not a['enabled'] for a in s.profile['slots'])


def test_alarm_modes_persist_and_migrate_from_v1(tmp_path):
    s = Store(tmp_path / 'config.json')
    a = make_alarm('Glitter', 900)
    s.profile['alarms'].append(a)
    a['alert_mode'] = 'Voice'
    a['keybind'] = 'Ctrl+Shift+G'
    s.save()
    other = Store(s.path)
    assert other.profile['alarms'][0]['alert_mode'] == 'Voice'
    assert other.profile['alarms'][0]['keybind'] == 'Ctrl+Shift+G'
    migrated = validated_profile({"alarms": [{"name": "Old1", "sound": True},
                                             {"name": "Old2", "sound": False}], "slots": []})
    assert [a['alert_mode'] for a in migrated['alarms']] == ['Sound', 'Off']


def test_keybind_validation():
    assert parse_hotkey('Ctrl+Alt+1') == (0x0003, ord('1'))
    assert parse_hotkey('F12') == (0, 0x7B)
    assert parse_hotkey('Meta+Shift+G') == (0x000C, ord('G'))
    assert parse_hotkey('Ctrl+Alt+G') == (0x0003, ord('G'))
    assert parse_hotkey('G') == (0, ord('G'))
    assert parse_hotkey('2') == (0, ord('2'))
    assert parse_hotkey('Space') == (0, 0x20)
    assert parse_hotkey('Escape') == (0, 0x1B)
    for invalid in ('F1', 'F2', 'F3', 'Ctrl', 'Ctrl+Ctrl+G', 'Ctrl+Alt+G+H', '', 'Ctrl+Alt+'):
        assert parse_hotkey(invalid) is None
    assert normalize_hotkey('control+alt+g') == 'Ctrl+Alt+G'
    assert normalize_hotkey('g') == 'G'
    assert normalize_hotkey('7') == '7'
    assert normalize_hotkey('Ctrl+Alt+F2') == ''


def test_reset_and_restart_clock():
    a = make_alarm('Convert', 5)
    c = AlarmClock(); c.configure([a]); c.start(a, now=1)
    assert c.tick([a], now=6) == [a['id']]
    c.reset(a); c.start(a, now=10)
    assert c.tick([a], now=11) == []
    assert c.tick([a], now=15) == [a['id']]


def test_notifier_lifecycle_off_windows(tmp_path):
    notifier = AlarmNotifier(tmp_path / 'any.wav')
    a = make_alarm('Glitter', 4)
    try:
        notifier.trigger(a)
        assert notifier.is_alerting(a['id'])
        notifier.acknowledge(a['id'])
        assert not notifier.is_alerting(a['id'])
        notifier.trigger(a)
        notifier.sync([])
        assert not notifier.is_alerting(a['id'])
    finally:
        notifier.close()
