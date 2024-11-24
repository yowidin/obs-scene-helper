from typing import Dict, Optional, Callable


class OBS:
    def __init__(self, host: str, port: int, password: str, timeout: int, reconnect_delay: int, grace_period: int,
                 on_changed: Optional[Callable[[], None]]):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.grace_period = grace_period
        self._on_changed = on_changed

    def _notify_changed(self):
        if self._on_changed is not None:
            self._on_changed()

    def as_args(self):
        """ Return a dictionary that could be directly passed to the OBS-WS library as initialization arguments """
        return {
            'host': self.host,
            'port': self.port,
            'password': self.password,
            'timeout': self.timeout
        }

    def to_dict(self) -> Dict:
        return {
            'host': self.host,
            'port': self.port,
            'password': self.password,
            'timeout': self.timeout,
            'reconnect_delay': self.reconnect_delay,
            'grace_period': self.grace_period,
        }

    @staticmethod
    def from_dict(val: Dict, on_changed: Optional[Callable[[], None]]) -> 'OBS':
        host = val['host']
        port = val['port']
        password = val['password']
        timeout = val['timeout']
        reconnect_delay = val['reconnect_delay']
        grace_period = val['grace_period']
        return OBS(host, port, password, timeout, reconnect_delay, grace_period, on_changed)

    def _values_as_tuple(self):
        return self.host, self.port, self.password, self.timeout, self.reconnect_delay, self.grace_period

    def __eq__(self, other: 'OBS'):
        return self._values_as_tuple() == other._values_as_tuple()

    def __ne__(self, other: 'OBS'):
        return self._values_as_tuple() != other._values_as_tuple()

    def will_change_from(self, other: 'OBS'):
        return self != other

    @staticmethod
    def make_default(on_changed: Optional[Callable[[], None]]) -> 'OBS':
        return OBS('localhost', 4455, '', 5, 5, 15, on_changed)

    def copy(self, on_changed: Optional[Callable[[], None]]) -> 'OBS':
        """ Make a copy of the settings instance """
        return OBS(self.host, self.port, self.password, self.timeout, self.reconnect_delay, self.grace_period,
                   on_changed)

    def update(self, other: 'OBS'):
        if self == other:
            # Nothing changed
            return

        self.host = other.host
        self.port = other.port
        self.password = other.password
        self.timeout = other.timeout
        self.reconnect_delay = other.reconnect_delay
        self.grace_period = other.grace_period
        self._notify_changed()
