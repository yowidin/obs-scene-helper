import json
import pytest
from pytest_mock import MockerFixture

from obs_scene_helper.model.settings.all_displays import AllDisplays


def test_to_and_from_dict_conversion():
    original = AllDisplays(['1', '2'], None)
    encoded = original.to_dict()
    assert encoded == {'all_displays': ['1', '2']}

    # Ensure we can convert to JSON and back
    encoded_json = json.dumps(encoded)
    decoded_json = json.loads(encoded_json)

    decoded = AllDisplays.from_dict(decoded_json, None)
    assert original == decoded


def test_update(mocker: MockerFixture):
    on_change_callback = mocker.Mock()
    original_list = ['1', '2']

    original = AllDisplays(original_list, on_change_callback)
    different_order = AllDisplays(['2', '1'], None)
    different_values = AllDisplays(['1', '3'], None)
    different_count = AllDisplays(['1', '2', '3'], None)

    assert not original.will_change_from(different_order)
    assert original.will_change_from(different_values)
    assert original.will_change_from(different_count)

    assert not original.will_change_from(different_order.all_displays)
    assert original.will_change_from(different_values.all_displays)
    assert original.will_change_from(different_count.all_displays)

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        original.will_change_from(10)

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        original.update(10)

    original.update(different_order)
    on_change_callback.assert_not_called()

    def check_one_change(changed_one: AllDisplays):
        # Ensure update is reported
        original.update(changed_one)
        on_change_callback.assert_called_once()

        # Reset the test object and the mock
        original.update(original_list)
        on_change_callback.reset_mock()

    check_one_change(different_values)
    check_one_change(different_count)
