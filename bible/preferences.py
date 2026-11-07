"""Small, atomic local reading preferences independent of note/session data."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile


@dataclass
class ReadingPreferences:
    font: str = 'Roboto Serif'
    size: int = 14
    chapter_numbers: bool = True
    verse_numbers: bool = True
    mode: str = 'system'
    day_palette: str = 'white'
    night_palette: str = 'dark'
    line_spacing: str = 'very-airy'
    column_width: str = 'narrow'
    show_highlights: bool = True
    note_indicators: bool = True
    place_markers: bool = True
    version: int = 1
    study_font: str = 'sans-serif'
    line_spacing_px: int | None = None
    text_width_px: int | None = None
    side_margin_px: int | None = None
    alignment: str = 'left'
    immersion_columns: str = 'automatic'
    serif_font: str = 'Roboto Serif'
    sans_font: str = 'Roboto'
    font_style: str = 'book'
    study_size: int | None = None
    visible_elements_expanded: bool = False


class Preferences:
    def __init__(self,path):
        self.path = Path(path)
        self.value = ReadingPreferences()
        self.error = ''
        self.writable = True
        try:
            value = json.loads(self.path.read_text())
            if not isinstance(value,dict):raise ValueError('Invalid reading preferences')
            if type(value.get('version',1)) is not int or value.get('version',1)!=1:
                raise ValueError('Unsupported reading preferences version')
            font,size = value.get('font','DejaVu Serif'), value.get('size',14)
            if not isinstance(font,str) or not font or len(font)>100:raise ValueError('Invalid font')
            if type(size) is not int or not 12<=size<=64:raise ValueError('Invalid text size')
            for key in ['chapter_numbers','verse_numbers','show_highlights','note_indicators','place_markers']:
                if type(value.get(key,True)) is not bool:raise ValueError('Invalid visibility preference')
            choices = {'mode': ('system','day','night'), 'day_palette': ('white','paper'),
                       'night_palette': ('dark','black'), 'line_spacing': ('tight','normal','airy','very-airy'),
                       'column_width': ('narrow','normal','wide')}
            defaults = ReadingPreferences()
            selected = {key:value.get(key,getattr(defaults,key)) for key in choices}
            if any(selected[key] not in options for key,options in choices.items()):
                raise ValueError('Invalid reading appearance')
            study_font=value.get('study_font','sans-serif')
            if not isinstance(study_font,str) or not study_font or len(study_font)>100 or any(ord(c)<32 for c in study_font):
                raise ValueError('Invalid study font')
            style=value.get('font_style','simple' if font=='DejaVu Sans' else 'book')
            if style not in ('book','simple'):raise ValueError('Invalid font style')
            typography={'font_style':style}
            for key,active,fallback in [('serif_font','book','DejaVu Serif'),('sans_font','simple','DejaVu Sans')]:
                family=value.get(key,font if style==active else fallback)
                if not isinstance(family,str) or not family or len(family)>100 or any(ord(c)<32 for c in family):
                    raise ValueError('Invalid reading font')
                typography[key]=family
            typography['study_size']=value.get('study_size')
            if typography['study_size'] is not None and (type(typography['study_size']) is not int or not 8<=typography['study_size']<=64):
                raise ValueError('Invalid study text size')
            typography['visible_elements_expanded']=value.get('visible_elements_expanded',True)
            if type(typography['visible_elements_expanded']) is not bool:raise ValueError('Invalid visibility preference')
            advanced={}
            for key,low,high in [('line_spacing_px',0,48),('text_width_px',280,1440),('side_margin_px',48,160)]:
                number=value.get(key)
                if number is not None and (type(number) is not int or not low<=number<=high):
                    raise ValueError('Invalid reading layout')
                advanced[key]=number
            for key,options in [('alignment',('left','justified')),('immersion_columns',('automatic','one'))]:
                option=value.get(key,getattr(defaults,key))
                if option not in options:raise ValueError('Invalid reading layout')
                advanced[key]=option
            self.value = ReadingPreferences(font,size,value.get('chapter_numbers',True),value.get('verse_numbers',True),
                                            show_highlights=value.get('show_highlights',True),
                                            note_indicators=value.get('note_indicators',True),
                                            place_markers=value.get('place_markers',True),study_font=study_font,**selected,**advanced,**typography)
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
