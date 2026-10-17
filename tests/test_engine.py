import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bss_booster.engine import AlarmClock, Scheduler, WindowsKeyboard
from bss_booster.config import make_alarm


def sample():
    return [{"key": 2, "item": "Gumdrops", "enabled": True, "interval": 2., "delay": 0.},
            {"key": 4, "item": "Stingers", "enabled": True, "interval": 10., "delay": 0.},
            {"key": 6, "item": "Glitter", "enabled": False, "interval": 20., "delay": 0.}]


def test_independent_timers_and_disabled_slot():
    s = Scheduler()
    s.start(sample(), now=100)
    assert s.due(now=100) == [2, 4]
    assert s.due(now=101) == []
    assert s.due(now=102) == [2]
    assert s.due(now=110) == [2, 4]
    assert 6 not in s.due(now=999)


def test_suspended_when_not_focused_no_burst():
    s = Scheduler(); s.start(sample(), now=1)
    assert s.due(now=1, can_send=False) == []
    assert s.due(now=100) == [2,4]
    assert s.due(now=100.01) == []


def test_pause_resume_preserves_remaining_time():
    s = Scheduler(); s.start(sample(), now=10)
    s.due(now=10)
    s.pause(now=11)
    assert s.due(now=100) == []
    s.resume(now=111)
    assert s.due(now=111) == []
    assert s.due(now=112) == [2]
    s.stop()
    assert s.due(now=10000) == []


def test_edit_rule_while_macro_running():
    s = Scheduler(); s.start(sample(), now=0)
    s.due(now=0)
    rules = sample()
    rules[1]["interval"] = 3
    s.configure(rules, now=2)
    assert s.due(now=2) == [2, 4]
    assert s.due(now=4) == [2]
    assert s.due(now=5) == [4]


def test_alarm_pause_resume_repeat():
    a = make_alarm("Glitter", 60, repeat=True)
    c = AlarmClock(); c.configure([a])
    c.start(a, now=10)
    assert c.time_left(a["id"], now=12) == 58
    c.pause(a["id"], now=15)
    assert c.time_left(a["id"], now=50) == 55
    c.start(a, now=50)
    assert c.tick([a], now=104) == []
    assert c.tick([a], now=105) == [a["id"]]
    assert c.time_left(a["id"], now=110) == 55


def test_alarm_once_and_reset():
    a = make_alarm("Convert", 10)
    c = AlarmClock(); c.configure([a]); c.start(a, now=0)
    assert c.tick([a], now=10) == [a["id"]]
    assert c.time_left(a["id"], now=11) == 0
    c.reset(a)
    assert c.time_left(a["id"], now=11) == 10


def test_native_send_has_safe_non_windows_behavior():
    if sys.platform != "win32":
        assert WindowsKeyboard.send(2) is False
        assert WindowsKeyboard.focused("Roblox") is False
