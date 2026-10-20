"""A local opt-out for honest GNOME notification help; never changes host state."""
import json
import os
from pathlib import Path
import tempfile


class ImmersionHints:
    def __init__(self,path):
        self.path=Path(path);self.disabled=False;self.writable=True
        try:
            value=json.loads(self.path.read_text())
            if not isinstance(value,dict) or type(value.get('disabled')) is not bool:raise ValueError('Invalid help preference')
            self.disabled=value['disabled']
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError):self.writable=False

    def disable(self):
        if not self.writable:return False
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile('w',dir=self.path.parent,delete=False,prefix='.immersion-help-') as stream:
                temporary=Path(stream.name);json.dump({'disabled':True},stream);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path);self.disabled=True;return True
        except OSError:return False
        finally:
            if temporary:temporary.unlink(missing_ok=True)
