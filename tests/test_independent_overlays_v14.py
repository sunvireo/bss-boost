"""Regression coverage for per-slot overlay visibility and separate alarm position."""
from bss_booster.config import Store, default_data, make_alarm, validated_data
from bss_booster.engine import AlarmClock, Scheduler


def test_new_slots_default_to_visible_without_enabling_auto():
    profile = default_data()['profiles']['Default']
    assert all(slot['overlay_visible'] is True for slot in profile['slots'])
    assert all(slot['enabled'] is False for slot in profile['slots'])


def test_old_saved_profile_defaults_hidden_flag_to_visible():
    old = default_data()
    for slot in old['profiles']['Default']['slots']:
        slot.pop('overlay_visible')
    loaded = validated_data(old)
    assert all(slot['overlay_visible'] for slot in loaded['profiles']['Default']['slots'])


def test_hidden_slots_do_not_change_macro_schedule():
    data = default_data()
    slot = data['profiles']['Default']['slots'][1]
    slot.update(item='Gumdrops', enabled=True, interval=2.0, overlay_visible=False)
    scheduler = Scheduler()
    scheduler.start(data['profiles']['Default']['slots'], now=100.0)
    assert 2 in scheduler.next_due
    assert slot['enabled']


def test_independent_alarm_coordinates_and_per_slot_flags_save(tmp_path):
    path = tmp_path / 'booster.json'
    store = Store(path)
    slots = store.profile['slots']
    slots[0].update(item='Gumdrops', enabled=True, overlay_visible=False)
    slots[1]['overlay_visible'] = True
    slots[6]['overlay_visible'] = False
    store.settings.update(overlay_x=101, overlay_y=901,
                          alarm_overlay_x=675, alarm_overlay_y=150)
    store.profile['alarms'].append(make_alarm('Glitter', 35))
    store.save()
    reloaded = Store(path)
    assert [s['overlay_visible'] for s in reloaded.profile['slots']] == [False, True, True, True, True, True, False]
    assert reloaded.profile['slots'][0]['enabled']
    assert (reloaded.settings['overlay_x'], reloaded.settings['overlay_y']) == (101, 901)
    assert (reloaded.settings['alarm_overlay_x'], reloaded.settings['alarm_overlay_y']) == (675, 150)
    assert reloaded.profile['alarms'][0]['name'] == 'Glitter'


def test_alarm_overlay_hidden_does_not_stop_alarm():
    data = default_data()
    data['settings']['overlay_alarms_visible'] = False
    alarm = make_alarm('Convert', 25)
    clock = AlarmClock()
    clock.configure([alarm])
    clock.start(alarm, 200.0)
    assert clock.time_left(alarm['id'], 210.0) == 15
    assert clock.tick([alarm], 225.0) == [alarm['id']]


def test_bad_alarm_overlay_coordinates_are_clamped():
    data = default_data()
    data['settings'].update(alarm_overlay_x=999999, alarm_overlay_y=-200)
    valid = validated_data(data)['settings']
    assert valid['alarm_overlay_x'] == 20000
    assert valid['alarm_overlay_y'] == -1
