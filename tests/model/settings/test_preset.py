import json
import pytest
from pytest_mock import MockerFixture

from obs_scene_helper.model.settings.preset import *


def test_preset_to_and_from_dict_conversion():
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    encoded = original.to_dict()

    assert encoded == {'uuid': '1', 'name': 'n', 'displays': ['d1', 'd2'], 'profile': 'p', 'scene_collection': 'sc'}

    # Ensure we can convert to JSON and back
    encoded_json = json.dumps(encoded)
    decoded_json = json.loads(encoded_json)

    decoded = Preset.from_dict(decoded_json)
    assert original == decoded


def test_preset_update_unchanged():
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    unchanged = original.copy()
    assert not original.will_change_from(unchanged)

    # If everything except the UUID is the same, then update should report that nothing has changed
    assert not original.update(unchanged)
    assert not unchanged.update(original)


def test_preset_update_changed():
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    changed = Preset('2', 'n', ['d2', 'd1'], 'p', 'sc1')
    assert original.will_change_from(changed)

    # After updating once, another update should report that nothing has changed
    assert original.update(changed)
    assert not original.update(changed)


def test_preset_make_empty():
    dummy = Preset.make()
    assert len(dummy.uuid) > 1


def test_preset_make_non_empty():
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    dummy = Preset.make(original)

    assert len(dummy.uuid) > 1

    # The freshly made preset should be indistinguishable from the original one
    assert not dummy.update(original)
    assert not original.update(dummy)


def test_preset_displays_unique_enough():
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    non_unique = Preset('2', 'n', ['d2', 'd1'], 'p', 'sc')
    unique_different_count = Preset('1', 'n', ['d2', 'd1', 'd3'], 'p', 'sc')
    unique_different_set = Preset('2', 'n', ['d3', 'd1'], 'p', 'sc')

    with pytest.raises(InvalidDisplayListArgument):
        # noinspection PyTypeChecker
        original.displays_unique_enough(10)

    assert not original.displays_unique_enough(non_unique)
    assert original.displays_unique_enough(unique_different_count.displays)
    assert original.displays_unique_enough(unique_different_set)


def test_preset_list_add(mocker: MockerFixture):
    p1 = Preset('1', 'n1', ['d1', 'd2'], 'p', 'sc')
    p2 = Preset('2', 'n2', ['d2', 'd1', 'd3'], 'p', 'sc')
    non_unique_config = Preset('3', 'n3', ['d2', 'd1'], 'p', 'sc')
    non_unique_name = Preset('4', 'n2', ['d7', 'd1'], 'p', 'sc')
    unique_different_set = Preset('5', 'n4', ['d3', 'd1'], 'p', 'sc')

    on_change_callback = mocker.Mock()
    preset_list = PresetList([p1, p2], on_change_callback)
    assert preset_list.presets == [p1, p2]

    with pytest.raises(NonUniqueUUID):
        preset_list.add(p1)

    with pytest.raises(NonUniquePreset):
        preset_list.add(non_unique_config)

    with pytest.raises(NonUniqueName):
        preset_list.add(non_unique_name)

    preset_list.add(unique_different_set)
    on_change_callback.assert_called_once()


def test_preset_list_remove(mocker: MockerFixture):
    p1 = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    p2 = Preset('2', 'n', ['d2', 'd1', 'd3'], 'p', 'sc')
    non_existent = Preset('3', 'n', ['d2', 'd1'], 'p', 'sc')

    on_change_callback = mocker.Mock()
    preset_list = PresetList([p1, p2], on_change_callback)
    assert preset_list.presets == [p1, p2]

    with pytest.raises(InvalidPresetArgument):
        # noinspection PyTypeChecker
        preset_list.remove(10)

    with pytest.raises(PresetNotFoundException):
        preset_list.remove(non_existent)

    with pytest.raises(PresetNotFoundException):
        preset_list.remove(non_existent.uuid)

    preset_list.remove(p1)
    assert preset_list.presets == [p2]
    on_change_callback.assert_called_once()
    on_change_callback.reset_mock()

    preset_list.remove(p2.uuid)
    assert preset_list.presets == []
    on_change_callback.assert_called_once()


def test_preset_list_update_unchanged(mocker: MockerFixture):
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    unchanged = Preset('2', 'n', ['d2', 'd1'], 'p', 'sc')

    on_change_callback = mocker.Mock()
    preset_list = PresetList([original], on_change_callback)
    assert preset_list.presets == [original]

    # If everything except the UUID is the same, then update should not trigger a callback
    preset_list.update(original, unchanged)
    on_change_callback.assert_not_called()


def test_preset_list_update_changed(mocker: MockerFixture):
    original = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    changed = Preset('2', 'n', ['d2', 'd1'], 'p', 'sc1')

    on_change_callback = mocker.Mock()
    preset_list = PresetList([original], on_change_callback)
    assert preset_list.presets == [original]

    # After updating once, another update should not trigger a callback
    preset_list.update(original, changed)
    on_change_callback.assert_called_once()

    on_change_callback.reset_mock()
    preset_list.update(original, changed)
    on_change_callback.assert_not_called()


def test_preset_list_update_non_unique_name(mocker: MockerFixture):
    p1 = Preset('1', 'n1', ['d1', 'd2'], 'p', 'sc')
    p2 = Preset('2', 'n2', ['d2', 'd1', 'd3'], 'p', 'sc')
    non_unique = Preset('3', 'n2', ['d4'], 'p', 'sc')

    on_change_callback = mocker.Mock()
    preset_list = PresetList([p1, p2], on_change_callback)
    assert preset_list.presets == [p1, p2]

    with pytest.raises(NonUniqueName):
        preset_list.update(p1, non_unique)

    on_change_callback.assert_not_called()


def test_preset_list_update_non_unique_config(mocker: MockerFixture):
    p1 = Preset('1', 'n1', ['d1', 'd2'], 'p', 'sc')
    p2 = Preset('2', 'n2', ['d2', 'd1', 'd3'], 'p', 'sc')
    non_unique = Preset('3', 'n3', ['d2', 'd1', 'd3'], 'p', 'sc')

    on_change_callback = mocker.Mock()
    preset_list = PresetList([p1, p2], on_change_callback)
    assert preset_list.presets == [p1, p2]

    with pytest.raises(NonUniquePreset):
        preset_list.update(p1, non_unique)

    on_change_callback.assert_not_called()


def test_preset_list_to_and_from_dict_conversion():
    p1 = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    p1_dict = p1.to_dict()

    original = PresetList([p1], None)
    assert original.presets == [p1]

    encoded = original.to_dict()
    assert encoded == {'presets': [p1_dict]}

    # Ensure we can convert to JSON and back
    encoded_json = json.dumps(encoded)
    decoded_json = json.loads(encoded_json)

    decoded = PresetList.from_dict(decoded_json, None)
    assert original.presets == decoded.presets


def test_str_convertible():
    p = Preset('1', 'n', ['d1', 'd2'], 'p', 'sc')
    assert p.name == str(p)
