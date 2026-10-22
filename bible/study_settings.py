"""Atomic drawer preferences, separate from reading appearance and annotations."""
import json
import os
from pathlib import Path
import tempfile


class StudySettings:
    def __init__(self, path):
        self.path = Path(path)
        self.width = 420
        self.tool = 'commentaries'
        self.error = ''
        try:
            if self.path.stat().st_size > 4096:
                raise ValueError('Study preferences file is too large')
            value = json.loads(self.path.read_text())
            if (not isinstance(value, dict) or value.get('version') != 1
                    or type(value.get('width')) is not int or not 280 <= value['width'] <= 2000
                    or value.get('tool') not in ('notes', 'commentaries', 'references')):
                raise ValueError('Unsupported study preferences')
            self.width, self.tool = value['width'], value['tool']
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as error:
            self.error = str(error)

    def save(self):
        if self.error:
            raise ValueError('Original study preferences preserved; repair the file before saving')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=self.path.parent, prefix='.study-', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(dict(version=1, width=self.width, tool=self.tool), stream)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary: temporary.unlink(missing_ok=True)
