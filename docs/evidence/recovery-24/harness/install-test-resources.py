"""Download actual CrossWire resources into a new disposable validation profile."""
import hashlib
import json
from pathlib import Path

from bible.library import Library, catalogue
from bible.sword_provider import Reader, CommentaryReader

profile = Path('/validation/resources')
assert not (profile / 'translations').exists(), 'Use a new disposable profile'
library = Library(profile / 'translations')
resources = {r.name: r for r in catalogue() if r.installable}
report = []
for name in ('FreSegond1910', 'KJV', 'MHC'):
    resource = resources[name]
    library.install(resource)
    cls = CommentaryReader if resource.kind == 'commentary' else Reader
    reader = cls(library.root / resource.id, resource.id)
    report.append({'id': resource.id, 'provider': resource.provider_id,
                   'kind': resource.kind, 'driver': resource.driver,
                   'versification': reader.versification,
                   'source': resource.source, 'license': resource.license,
                   'conditions': resource.conditions})
    print('INSTALLED', name, reader.versification, flush=True)
files = {str(p.relative_to(profile)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in profile.rglob('*') if p.is_file()}
Path('/evidence/resources.json').write_text(json.dumps({'resources': report, 'files': files}, indent=2) + '\n')
