import hashlib
import inspect
import json
from pathlib import Path
from bible.library import Library
from bible.sword_provider import Reader
from bible.reference_resolution import resolve, VersificationMismatch

assert inspect.getfile(Reader).startswith('/app/lib/bible-python/bible/')
profile = Path('/validation/issue57-profile')
library = Library(profile / 'translations')
names = ('FreSegond1910','KJV','ebible~frajnd2024eb','ebible~fraLSG1910eb','ebible~frasbl2022eb')
readers = {name:Reader(library.root/name,name) for name in names}
report = {'code':'signed-public-alpha', 'source_commit':'87b9803eebf56fbd3acaa1e3c6b9cfd8f5d60d0b',
          'flatpak_commit':'f876b328b4777182cdb499dd7cb617d328cdb30a6ada042f7a3f15560aea3294',
          'reader_import':inspect.getfile(Reader),'network':'flatpak --unshare=network',
          'resources':{},'pairs':[],'status':'reproducer; no correction implemented'}
for name,reader in readers.items():
    chapter = reader.chapter('John.3.16')
    text = dict(chapter.verses)['John.3.16']
    reader.module.setKey(reader.key('John.3.16'))
    plain = reader.module.stripText()
    if not isinstance(plain,str):plain=plain.c_str()
    assert text == plain
    report['resources'][name] = dict(versification=reader.versification,
        driver=reader.module.getConfigEntry('ModDrv'),version=reader.module.getConfigEntry('Version'),
        john_3_16_characters=len(text),direct_sword_match=True,
        sha256=hashlib.sha256(text.encode()).hexdigest())
for primary,secondary in (('FreSegond1910','ebible~frajnd2024eb'),
                          ('ebible~frajnd2024eb','FreSegond1910'),
                          ('ebible~frajnd2024eb','ebible~frajnd2024eb'),
                          ('KJV','FreSegond1910'),
                          ('ebible~fraLSG1910eb','FreSegond1910'),
                          ('ebible~frasbl2022eb','FreSegond1910')):
    result = dict(primary=primary,comparison=secondary)
    try:
        mapped = resolve('John.3.16',readers[primary].versification,readers[secondary])
        result.update(aligned=True,start=mapped.start,end=mapped.end)
    except VersificationMismatch as error:
        result.update(aligned=False,error=str(error))
    report['pairs'].append(result)
print(json.dumps(report,ensure_ascii=False,indent=2))
