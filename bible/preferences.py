"""Small, atomic local reading preferences independent of note/session data."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile


@dataclass
class ReadingPreferences:
    font: str = 'DejaVu Serif'
    size: int = 14
    chapter_numbers: bool = True
    verse_numbers: bool = True
    mode: str = 'system'
    day_palette: str = 'white'
    night_palette: str = 'dark'
    line_spacing: str = 'airy'
    column_width: str = 'narrow'
    show_highlights: bool = True


class Preferences:
    def __init__(self,path):
        self.path = Path(path)
        self.value = ReadingPreferences()
        self.error = ''
        self.writable = True
        try:
            value = json.loads(self.path.read_text())
            if not isinstance(value,dict):raise ValueError('Invalid reading preferences')
            font,size = value.get('font','DejaVu Serif'), value.get('size',14)
            if not isinstance(font,str) or not font or len(font)>100:raise ValueError('Invalid font')
            if type(size) is not int or not 12<=size<=64:raise ValueError('Invalid text size')
            for key in ['chapter_numbers','verse_numbers','show_highlights']:
                if type(value.get(key,True)) is not bool:raise ValueError('Invalid visibility preference')
            choices = {'mode': ('system','day','night'), 'day_palette': ('white','paper'),
                       'night_palette': ('dark','black'), 'line_spacing': ('tight','normal','airy','very-airy'),
                       'column_width': ('narrow','normal','wide')}
            defaults = ReadingPreferences()
            selected = {key:value.get(key,getattr(defaults,key)) for key in choices}
            if any(selected[key] not in options for key,options in choices.items()):
                raise ValueError('Invalid reading appearance')
            self.value = ReadingPreferences(font,size,value.get('chapter_numbers',True),value.get('verse_numbers',True),
                                            show_highlights=value.get('show_highlights',True),**selected)
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError) as error:
            self.error = str(error);self.writable = False

    def save(self):
        if not self.writable:raise ValueError('Original preferences preserved; repair the file before saving')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w',dir=self.path.parent,prefix='.appearance-',delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(asdict(self.value),stream,ensure_ascii=False)
                stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary:temporary.unlink(missing_ok=True)
