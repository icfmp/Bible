"""Native keys whose public reference retains an explicit source section ID."""
import re
from .source_sections import SECTION


def key_type(sword,index,system):
    """Build once per verified index; do not replace SWORD's global key class.

    C++ receives the ordinary native storage fields. Python callers receive the
    original section reference. Both conversions use the same explicit table.
    """
    class SourceKey(sword.VerseKey):
        def __init__(self,value=None):
            if value is None or isinstance(value,str):
                super().__init__();self.setVersificationSystem(system);self.setAutoNormalize(False)
                if self.getVersificationSystem()!=system:raise ValueError('Source numbering unavailable')
                if isinstance(value,str):self.setText(value)
            else:
                super().__init__(value)
                if self.getVersificationSystem()!=system:raise ValueError('Source key context differs')
                self._public_alias=value.getOSISRef() if isinstance(value,SourceKey) else None

        def setText(self,value):
            match=re.fullmatch(rf'(.+?)[ .]+({SECTION})(?:[.:](0|[1-9][0-9]{{0,3}}))?',value.strip()) if isinstance(value,str) else None
            if not match:raise ValueError('Invalid source reference')
            book,chapter,verse=match.groups()
            # Resolve only the book spelling here. Parsing the source's chapter
            # through native storage first could clamp or reinterpret its ID.
            probe=sword.VerseKey();probe.setVersificationSystem(system);probe.setAutoNormalize(False)
            probe.setText(book+'.1.1')
            if probe.popError()!='\x00':raise ValueError('Invalid source book')
            source=probe.getOSISBookName()+'.'+chapter+('.'+verse if verse is not None else '')
            if verse is None:
                description=getattr(index,'chapters',{}).get(source)
                if description:source=description.units[0].members[0]
            super().setText(index.to_native(source,allow_zero=True))
            self._public_alias=source if source.count('.')==2 else source+'.1'

        def getOSISRef(self):
            native=super().getOSISRef();alias=getattr(self,'_public_alias',None)
            if native.split('.')[1]=='0':return native
            if alias and index.to_native(alias,allow_zero=True)==native:return alias
            return index.to_source(native,allow_zero=True)

        def getChapter(self):
            chapter=self.getOSISRef().split('.')[1]
            return chapter if '_' in chapter else int(chapter)

        def getVerse(self):return int(self.getOSISRef().split('.')[2])

        def getVerseMax(self):
            chapter=self.getOSISRef().rsplit('.',1)[0]
            units=getattr(index,'chapters',{}).get(chapter)
            return max(int(ref.rsplit('.',1)[1]) for ref in units.inventory) if units else super().getVerseMax()

        def setVerse(self,number):
            self.setText(self.getOSISRef().rsplit('.',1)[0]+'.'+str(number))

        def setChapter(self,number):
            if number==0:
                self._public_alias=None;return super().setChapter(0)
            self.setText(self.getOSISBookName()+'.'+str(number)+'.1')

        def getUpperBound(self):return type(self)(super().getUpperBound())
        def getLowerBound(self):return type(self)(super().getLowerBound())

    return SourceKey
