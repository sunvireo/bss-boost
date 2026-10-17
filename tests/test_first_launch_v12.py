"""New-first-run behavior must not damage existing saved configurations."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bss_booster.config import Store, make_alarm, make_slot, validated_data
from bss_booster.hotkey_codec import parse_hotkey, normalize_hotkey
from bss_booster.engine import Scheduler


def test_first_run_is_empty_and_inert(tmp_path):
    store = Store(tmp_path / 'fresh.json')
    assert len(store.profile['slots']) == 7
    assert store.profile['alarms'] == []
    assert all(slot['item'] == 'Empty' and not slot['enabled'] for slot in store.profile['slots'])
    scheduler = Scheduler()
    assert scheduler.due(now=400) == []
    scheduler.start(store.profile['slots'], now=10)
    assert scheduler.due(now=10) == []


def test_preserve_custom_existing_profile_after_upgrade(tmp_path):
    path = tmp_path / 'previous.json'
    store = Store(path)
    slot = store.profile['slots'][3]
    slot.update(item='Stingers', enabled=True, interval=9.5, delay=3)
    alarm = make_alarm('Precision', 180)
    alarm['keybind'] = 'P'
    store.profile['alarms'].append(alarm)
    store.settings['overlay_corner'] = 'Top center'
    store.save()
    reopened = Store(path)
    assert reopened.profile['slots'][3]['interval'] == 9.5
    assert reopened.profile['slots'][3]['item'] == 'Stingers'
    assert reopened.profile['alarms'][0]['keybind'] == 'P'
    assert reopened.settings['overlay_corner'] == 'Top center'


def test_load_original_presets_even_with_prepopulated_items(tmp_path):
    path = tmp_path / 'older.json'
    store = Store(path)
    store.profile['slots'][1] = dict(make_slot(2), item='Gumdrops', interval=2, enabled=True)
    store.profile['alarms'].append(dict(make_alarm('Glitter', 100), keybind='Ctrl+Alt+1'))
    store.save()
    again = Store(path)
    assert again.profile['slots'][1]['enabled'] is True
    assert again.profile['alarms'][0]['keybind'] == 'Ctrl+Alt+1'


def test_single_key_accepted_but_macro_keys_reserved():
    for hotkey in ('G','8','f4','space','ctrl+shift+h'):
        assert parse_hotkey(hotkey)
        assert normalize_hotkey(hotkey)
    for hotkey in ('F1','F2','F3','Ctrl+F2','', 'Ctrl', 'H+G'):
        assert parse_hotkey(hotkey) is None
