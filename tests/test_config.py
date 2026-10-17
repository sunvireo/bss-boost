import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bss_booster.config import Store, human_time, validated_data, validated_profile, make_alarm


def test_default_profile_and_save(tmp_path):
    file = tmp_path / "app" / "config.json"
    s = Store(file)
    assert len(s.profile["slots"]) == 7
    assert all(not slot["enabled"] for slot in s.profile["slots"])
    s.profile["slots"][1]["enabled"] = True
    s.profile["slots"][1]["interval"] = 2.0
    s.settings["overlay_corner"] = "Bottom left"
    s.save()
    other = Store(file)
    assert other.profile["slots"][1]["enabled"]
    assert other.profile["slots"][1]["interval"] == 2.0
    assert other.settings["overlay_corner"] == "Bottom left"


def test_profile_clone_independent(tmp_path):
    s = Store(tmp_path / "cfg.json")
    assert s.clone_profile("Red boost")
    s.profile["slots"][0]["item"] = "Glitter"
    assert s.data["profiles"]["Default"]["slots"][0]["item"] == "Empty"
    assert not s.clone_profile("Red boost")
    assert not s.clone_profile("  ")


def test_corrupt_json_does_not_crash(tmp_path):
    file = tmp_path / "bad.json"
    file.write_text("{broken", encoding="utf-8")
    assert Store(file).profile["slots"][0]["key"] == 1


def test_bad_data_clamped_and_alarm_ids_unique():
    raw = {"schema": 2, "active_profile": "X", "profiles": {"X": {"slots": [
        {"key": 2, "item": "Stingers", "interval": 0, "delay": -50, "enabled": True}],
        "alarms": [{"id": "dupe", "name": "One", "duration": -2},
                   {"id": "dupe", "name": "Two", "duration": 80000000}]}}}
    parsed = validated_data(raw)
    assert parsed["profiles"]["X"]["slots"][1]["interval"] == 0.1
    assert parsed["profiles"]["X"]["slots"][1]["delay"] == 0
    alarms = parsed["profiles"]["X"]["alarms"]
    assert alarms[0]["id"] != alarms[1]["id"]
    assert alarms[0]["duration"] == 1
    assert alarms[1]["duration"] == 3599999


def test_human_time():
    assert human_time(0) == "00:00"
    assert human_time(2.5) == "00:03"
    assert human_time(3661) == "01:01:01"
