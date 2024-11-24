from dataclasses import dataclass
from typing import List, Dict, Union, Optional, Any, Callable


class InvalidDisplayListArgument(TypeError):
    def __init__(self, argument: Any):
        super().__init__(f'Invalid display list type: {type(argument)}')
        self.argument = argument


@dataclass
class Preset:
    uuid: str
    name: str
    displays: List[str]
    profile: str
    scene_collection: str

    def to_dict(self) -> Dict:
        return {
            'uuid': self.uuid,
            'name': self.name,
            'displays': self.displays,
            'profile': self.profile,
            'scene_collection': self.scene_collection,
        }

    @staticmethod
    def from_dict(val: Dict) -> 'Preset':
        uuid = val['uuid']
        name = val['name']
        displays = [x for x in sorted(val['displays'])]
        profile = val['profile']
        scene_collection = val['scene_collection']
        return Preset(uuid, name, displays, profile, scene_collection)

    @staticmethod
    def _comparable_display_list(displays: List[str]) -> List[str]:
        return [x.lower() for x in sorted(displays)]

    def _values_as_tuple(self):
        return self.name, Preset._comparable_display_list(self.displays), self.profile, self.scene_collection

    def will_change_from(self, other: 'Preset'):
        return self._values_as_tuple() != other._values_as_tuple()

    def update(self, other: 'Preset') -> bool:
        if self._values_as_tuple() == other._values_as_tuple():
            # Nothing changed
            return False

        self.name = other.name
        self.displays = other.displays
        self.profile = other.profile
        self.scene_collection = other.scene_collection

        return True

    @staticmethod
    def make(template: Optional['Preset'] = None) -> 'Preset':
        from uuid import uuid4

        result = Preset(str(uuid4()), '', [], '', '')
        if template is not None:
            result.update(template)

        return result

    def copy(self) -> 'Preset':
        """ Make a deep copy of a preset """
        return Preset(self.uuid, self.name, [x for x in self.displays], self.profile, self.scene_collection)

    def displays_unique_enough(self, other: Union['Preset', List[str]]):
        """
        Compare the display lists.

        We need the presets to be distinct enough so that we can decide which settings to apply if we observe a display
        configuration change.

        :return True if the display lists are unique enough, False otherwise
        """
        if isinstance(other, Preset):
            displays = other.displays
        elif isinstance(other, list):
            displays = other
        else:
            raise InvalidDisplayListArgument(other)

        return Preset._comparable_display_list(self.displays) != Preset._comparable_display_list(displays)

    def __str__(self):
        return self.name


class PresetNotFoundException(RuntimeError):
    def __init__(self, uuid: str):
        super().__init__(f'Unknown preset: {uuid}')
        self.uuid = uuid


class InvalidPresetArgument(TypeError):
    def __init__(self, argument: Any):
        super().__init__(f'Invalid preset argument type: {type(argument)}')
        self.argument = argument


class NonUniqueUUID(RuntimeError):
    def __init__(self, existing: Preset):
        super().__init__(f'Preset UUID is not unique: {existing.uuid}')
        self.existing = existing


class NonUniquePreset(RuntimeError):
    def __init__(self, existing: Preset, new: Preset):
        super().__init__(f'New preset "{new.name}" is not unique enough, conflicts with "{existing.name}"')
        self.existing = existing
        self.new = new


class PresetList:
    def __init__(self, presets: List[Preset], on_changed: Optional[Callable[[], None]]):
        super().__init__()
        self._presets = presets
        self._by_uuid = self._arrange_by_uuid(self._presets)
        self._on_changed = on_changed

    def _notify_changed(self):
        if self._on_changed is not None:
            self._on_changed()

    @property
    def presets(self):
        return self._presets

    def add(self, preset: Preset):
        if preset.uuid in self._by_uuid:
            raise NonUniqueUUID(self._by_uuid[preset.uuid])

        for existing in self._presets:
            if not existing.displays_unique_enough(preset):
                raise NonUniquePreset(existing, preset)

        self._presets.append(preset)
        self._by_uuid[preset.uuid] = preset

        self._notify_changed()

    def _find_preset(self, preset: Union[Preset, str]) -> Preset:
        if isinstance(preset, str):
            uuid = preset
        elif isinstance(preset, Preset):
            uuid = preset.uuid
        else:
            raise InvalidPresetArgument(preset)

        if uuid not in self._by_uuid:
            raise PresetNotFoundException(uuid)

        return self._by_uuid[uuid]

    def remove(self, preset: Union[Preset, str]):
        existing = self._find_preset(preset)
        self._presets.remove(existing)
        del self._by_uuid[existing.uuid]
        self._notify_changed()

    def update(self, existing: Union[Preset, str], updated: Preset):
        """ Update the existing preset with the new values (all values except UUID will be copied over) """
        existing = self._find_preset(existing)
        if existing.update(updated):
            self._notify_changed()

    @staticmethod
    def _arrange_by_uuid(presets: List[Preset]) -> Dict:
        res = {}

        for preset in presets:
            res[preset.uuid] = preset

        return res

    def to_dict(self) -> Dict:
        return {'presets': [x.to_dict() for x in self._presets]}

    @staticmethod
    def from_dict(val: Dict, on_changed: Optional[Callable[[], None]]) -> 'PresetList':
        raw_presets = val['presets']

        presets = []
        for raw_preset in raw_presets:
            presets.append(Preset.from_dict(raw_preset))

        return PresetList(presets, on_changed)
