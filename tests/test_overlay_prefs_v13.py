"""New overlay preferences must be independent, safe and persistent."""
import json
from pathlib import Path

from bss_booster.config import Store, default_data, make_alarm, validated_data
from bss_booster.engine import AlarmClock


def test_blank_install_has_no_macro_or_alarm_rules():
    cfg = default_data()
    profile = cfg['profiles']['Default']
    assert not profile['alarms']
    assert len(profile['slots']) == 7
    assert all(not x['enabled'] and x['item'] == 'Empty' for x in profile['slots'])


def test_independent_alarms_and_hotbar_visibility():
    cfg = default_data()
    cfg['settings']['overlay_hotbar_visible'] = False
    cfg['settings']['overlay_alarms_visible'] = True
    restored = validated_data(cfg)
    assert not restored['settings']['overlay_hotbar_visible']
    assert restored['settings']['overlay_alarms_visible']
    restored['settings']['overlay_hotbar_visible'] = True
    restored['settings']['overlay_alarms_visible'] = False
    again = validated_data(restored)
    assert again['settings']['overlay_hotbar_visible']
    assert not again['settings']['overlay_alarms_visible']


def test_legacy_overlay_off_migrates_both_sections():
    old = default_data()
    old['settings']['overlay_visible'] = False
    for key in ('overlay_hotbar_visible','overlay_alarms_visible'):
        del old['settings'][key]
    migrated = validated_data(old)
    assert not migrated['settings']['overlay_hotbar_visible']
    assert not migrated['settings']['overlay_alarms_visible']


def test_legacy_overlay_on_migrates_both_sections():
    old = default_data()
    for key in ('overlay_hotbar_visible','overlay_alarms_visible'):
        del old['settings'][key]
    migrated = validated_data(old)
    assert migrated['settings']['overlay_hotbar_visible']
    assert migrated['settings']['overlay_alarms_visible']


def test_overlay_dimensions_validated():
    cfg = default_data()
    cfg['settings'].update(overlay_scale=1000, overlay_spacing=-700, overlay_x=-100, overlay_y=999999)
    settings = validated_data(cfg)['settings']
    assert settings['overlay_scale'] == 150
    assert settings['overlay_spacing'] == 0
    assert settings['overlay_x'] == -1
    assert settings['overlay_y'] == 20000


def test_hidden_alarms_continue_to_count_down():
    cfg = default_data()
    cfg['settings']['overlay_alarms_visible'] = False
    a = make_alarm('Glitter', 30)
    clock = AlarmClock()
    clock.configure([a])
    clock.start(a, 100.0)
    assert clock.time_left(a['id'], 115.0) == 15.0
    assert clock.tick([a], 130.0) == [a['id']]


def test_overlay_options_survive_restart(tmp_path):
    path = tmp_path / 'prefs.json'
    store = Store(path)
    store.settings.update(overlay_hotbar_visible=False, overlay_alarms_visible=True,
                          overlay_clickthrough=True, overlay_countdowns=True,
                          overlay_scale=90, overlay_spacing=23, overlay_x=200, overlay_y=820)
    store.profile['slots'][1].update(item='Gumdrops', enabled=True, interval=2.0)
    store.save()
    new = Store(path)
    for key in ('overlay_hotbar_visible', 'overlay_alarms_visible', 'overlay_clickthrough',
                'overlay_countdowns', 'overlay_scale', 'overlay_spacing', 'overlay_x', 'overlay_y'):
        assert new.settings[key] == store.settings[key]
    assert new.profile['slots'][1]['item'] == 'Gumdrops'
    assert new.profile['slots'][1]['interval'] == 2.0
