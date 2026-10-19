"""Versioned local reading session, independent from downloaded translations."""
from dataclasses import asdict, dataclass, field
import json
import math
import os
from pathlib import Path
import re
import tempfile


@dataclass
class TabState:
    resource: str | None = None
    reference: str = 'Gen.1.1'
    scroll: float = 0.0
    study_visible: bool = False


@dataclass
class Session:
    tabs: list[TabState] = field(default_factory=list)
    selected: int = 0


class SessionError(ValueError):
    pass


class SessionStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        try:
            with self.path.open('rb') as source:
                data = source.read(1024 * 1024 + 1)
        except FileNotFoundError:
            return Session()
        if len(data) > 1024 * 1024:
            raise SessionError('Session file too large')
        try:
            value = json.loads(data)
            if (not isinstance(value, dict) or type(value.get('version')) is not int
                    or value['version'] != 1 or not isinstance(value['tabs'], list)):
                raise ValueError('Unsupported session format')
            tabs = []
            for item in value['tabs']:
                resource = item['resource']
                reference = item['reference']
                scroll = item.get('scroll', 0.0)
                study = item.get('study_visible', False)
                if (resource is not None and (not isinstance(resource, str)
                        or not re.fullmatch(r'[A-Za-z0-9_-]+', resource))):
                    raise ValueError('Invalid translation name')
                if not isinstance(reference, str) or not reference or len(reference) > 256:
                    raise ValueError('Invalid reference')
                if (type(scroll) not in (int, float) or not 0 <= scroll <= 1
                        or not math.isfinite(scroll) or type(study) is not bool):
                    raise ValueError('Invalid reading position')
                tabs.append(TabState(resource, reference, float(scroll), study))
            selected = value.get('selected', 0)
            if type(selected) is not int or selected < 0 or (selected >= len(tabs) if tabs else selected != 0):
                raise ValueError('Invalid selected tab')
            return Session(tabs, selected)
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            raise SessionError(str(error)) from error

    def save(self, session):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                             dir=self.path.parent, prefix='.session-',
                                             delete=False) as output:
                temporary = Path(output.name)
                json.dump({'version': 1, 'tabs': [asdict(tab) for tab in session.tabs],
                           'selected': session.selected}, output, ensure_ascii=False,
                          allow_nan=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
