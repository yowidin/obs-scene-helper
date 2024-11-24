import json
from pytest_mock import MockerFixture

from obs_scene_helper.model.settings.obs import OBS


def test_to_and_from_dict_conversion():
    original = OBS('h', 10, 'p', 20, 30, 40, None)
    assert original.as_args() == {'host': 'h', 'port': 10, 'password': 'p', 'timeout': 20}

    encoded_full = original.to_dict()
    assert encoded_full == {'host': 'h', 'port': 10, 'password': 'p', 'timeout': 20, 'reconnect_delay': 30,
                            'grace_period': 40}

    # Ensure we can convert to JSON and back
    encoded_json = json.dumps(encoded_full)
    decoded_json = json.loads(encoded_json)

    decoded = OBS.from_dict(decoded_json, None)
    assert original == decoded


def test_update(mocker: MockerFixture):
    on_change_callback = mocker.Mock()
    copy_callback = mocker.Mock()
    original = OBS('h', 10, 'p', 20, 30, 40, on_change_callback)

    unchanged = original.copy(copy_callback)
    changed_host = OBS('h1', 10, 'p', 20, 30, 40, on_change_callback)
    changed_port = OBS('h', 20, 'p', 20, 30, 40, on_change_callback)
    changed_password = OBS('h', 10, 'p1', 20, 30, 40, on_change_callback)
    changed_timeout = OBS('h', 10, 'p', 25, 30, 40, on_change_callback)
    changed_reconnect_delay = OBS('h', 10, 'p', 20, 31, 40, on_change_callback)
    changed_grace_period = OBS('h', 10, 'p', 20, 31, 42, on_change_callback)

    # Equality checks
    assert original == unchanged
    assert original != changed_host
    assert original != changed_port
    assert original != changed_password
    assert original != changed_timeout
    assert original != changed_reconnect_delay
    assert original != changed_grace_period

    assert not original.will_change_from(unchanged)
    assert original.will_change_from(changed_host)

    on_change_callback.assert_not_called()

    original.update(unchanged)
    on_change_callback.assert_not_called()

    def check_one_change(changed_one: OBS):
        # Ensure update is reported
        original.update(changed_one)
        on_change_callback.assert_called_once()

        # Reset the test object and the mock
        original.update(unchanged)
        on_change_callback.reset_mock()

    check_one_change(changed_host)
    check_one_change(changed_port)
    check_one_change(changed_password)
    check_one_change(changed_timeout)
    check_one_change(changed_reconnect_delay)
    check_one_change(changed_grace_period)

    copy_callback.assert_not_called()
