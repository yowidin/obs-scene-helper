from typing import Dict, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class OSH:
    @dataclass
    class MacOS:
        fix_inputs_after_recording_resume_delay: int = 15

        def copy(self) -> 'OSH.MacOS':
            macos = OSH.MacOS(self.fix_inputs_after_recording_resume_delay)
            return macos

    output_file_change_script: str = field(default="")
    macos: MacOS = field(default_factory=lambda: OSH.MacOS())

    _on_changed: Optional[Callable[[], None]] = field(default=None, init=False, repr=False, compare=False, hash=False)

    def _notify_changed(self):
        if self._on_changed is not None:
            self._on_changed()

    def to_json_dict(self) -> Dict:
        return {
            'macos': self.macos.__dict__,
            'output_file_change_script': self.output_file_change_script,
        }

    @staticmethod
    def from_json_dict(val: Dict, on_changed: Optional[Callable[[], None]]) -> 'OSH':
        macos = OSH.MacOS(**val['macos'])
        output_file_change_script = val.get('output_file_change_script', "")
        osh = OSH(output_file_change_script, macos)
        osh._on_changed = on_changed
        return osh

    def will_change_from(self, other: 'OSH'):
        return self != other

    @staticmethod
    def make_default(on_changed: Optional[Callable[[], None]]) -> 'OSH':
        osh = OSH()
        osh._on_changed = on_changed
        return osh

    def copy(self, on_changed: Optional[Callable[[], None]]) -> 'OSH':
        """ Make a copy of the settings instance """
        osh = OSH(self.output_file_change_script, self.macos.copy())
        osh._on_changed = on_changed
        return osh

    def update(self, other: 'OSH'):
        if self == other:
            # Nothing changed
            return

        self.output_file_change_script = other.output_file_change_script
        self.macos = other.macos
        self._notify_changed()
