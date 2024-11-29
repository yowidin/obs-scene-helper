from typing import List, Optional, Callable, Dict, Union


class AllDisplays:
    """ Stores all displays we've ever seen, making the preset construction easier """

    def __init__(self, all_displays: List[str], on_changed: Optional[Callable[[], None]]):
        self.all_displays = all_displays
        self._on_changed = on_changed

    def _notify_changed(self):
        if self._on_changed is not None:
            self._on_changed()

    def to_dict(self) -> Dict:
        return {'all_displays': self.all_displays}

    @staticmethod
    def from_dict(val: Dict, on_changed: Optional[Callable[[], None]]) -> 'AllDisplays':
        all_displays = val['all_displays']
        return AllDisplays(all_displays, on_changed)

    @staticmethod
    def _comparable_display_list(displays: List[str]) -> List[str]:
        return [x.lower() for x in sorted(displays)]

    @staticmethod
    def _display_list_from_other(other: Union['AllDisplays', List[str]]):
        if isinstance(other, AllDisplays):
            return other.all_displays
        elif isinstance(other, list):
            return other
        else:
            raise TypeError('Display list expected')

    def __eq__(self, other: Union['AllDisplays', List[str]]):
        other_displays = AllDisplays._display_list_from_other(other)
        return self._comparable_display_list(self.all_displays) == AllDisplays._comparable_display_list(other_displays)

    def __ne__(self, other: Union['AllDisplays', List[str]]):
        return not (self == other)

    def will_change_from(self, other: Union['AllDisplays', List[str]]):
        return self != other

    def update(self, other: Union['AllDisplays', List[str]]):
        # The new display list might be smaller than the old one, but can still contain some new entries.
        # So we make use an intersection of both lists as the new list.

        other_displays = set(AllDisplays._display_list_from_other(other))
        our_displays = set(self.all_displays)
        new_display_list = list(our_displays | other_displays)

        if not self.will_change_from(new_display_list):
            return

        self.all_displays = new_display_list
        self._notify_changed()
