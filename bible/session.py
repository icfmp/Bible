"""Versioned local reading session, independent from downloaded translations."""
from dataclasses import asdict, dataclass, field
import json
import math
import os
from pathlib import Path
import re
import tempfile
from .providers import RESOURCE_ID


@dataclass
class TabState:
    resource: str | None = None
    reference: str = 'Gen.1.1'
    scroll: float = 0.0
    study_visible: bool = False
    commentary: str | None = None
    history: list = field(default_factory=list)
    history_index: int = -1
    comparison: str | None = None


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
                commentary = item.get('commentary')
                if commentary is not None and (not isinstance(commentary, str)
                        or not re.fullmatch(RESOURCE_ID, commentary)):
                    raise ValueError('Invalid commentary name')
                scroll = item.get('scroll', 0.0)
                study = item.get('study_visible', False)
                if (resource is not None and (not isinstance(resource, str)
                        or not re.fullmatch(RESOURCE_ID, resource))):
                    raise ValueError('Invalid translation name')
                if not isinstance(reference, str) or not reference or len(reference) > 256:
                    raise ValueError('Invalid reference')
                if (type(scroll) not in (int, float) or not 0 <= scroll <= 1
                        or not math.isfinite(scroll) or type(study) is not bool):
                    raise ValueError('Invalid reading position')
                history = item.get('history', [])
                cursor = item.get('history_index', len(history)-1)
                if not isinstance(history,list) or len(history)>100:raise ValueError('Invalid history')
                for entry in history:
                    if (not isinstance(entry,dict) or not isinstance(entry.get('resource'),str)
                            or not re.fullmatch(RESOURCE_ID,entry['resource'])
                            or not isinstance(entry.get('reference'),str) or not 1<=len(entry['reference'])<=256
                            or type(entry.get('scroll',0)) not in (int,float)
                            or not 0<=entry.get('scroll',0)<=1):raise ValueError('Invalid history entry')
                if type(cursor) is not int or (not 0<=cursor<len(history) if history else cursor != -1):
                    raise ValueError('Invalid history cursor')
                comparison = item.get('comparison')
                if comparison is not None and (not isinstance(comparison,str) or not re.fullmatch(RESOURCE_ID,comparison)):
                    raise ValueError('Invalid comparison')
                tabs.append(TabState(resource, reference, float(scroll), study, commentary, history, cursor, comparison))
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
