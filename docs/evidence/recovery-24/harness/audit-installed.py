import hashlib
import json
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango
import bible
import Sword

application = Path(bible.__file__).parent
assert application == Path('/app/lib/bible-python/bible'), application
hashes = {}
for source in sorted(Path('/validation/checkout/bible').rglob('*.py')):
    relative = source.relative_to('/validation/checkout/bible')
    installed = application / relative
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(source) == digest(installed), relative
    hashes[str(relative)] = digest(installed)
before = json.loads(Path('/evidence/resources.json').read_text())['files']
after = {str(p.relative_to('/validation/resources')): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in Path('/validation/resources').rglob('*') if p.is_file()}
assert before == after
Path('/evidence/flatpak/installed-audit.json').write_text(json.dumps({
    'application': str(application), 'sword_binding': Sword.__file__,
    'gtk': '.'.join(str(getattr(Gtk, 'get_' + part + '_version')()) for part in ('major', 'minor', 'micro')),
    'libadwaita': '.'.join(str(getattr(Adw, 'get_' + part + '_version')()) for part in ('major', 'minor', 'micro')),
    'pango': Pango.version_string(),
    'all_application_python_files_match_source': True,
    'application_sha256': hashes,
    'original_test_resource_files_unchanged': True,
    'network': 'flatpak run --unshare=network',
    'manual_gnome_validation': False,
}, indent=2) + '\n')
print('PASS: all installed application Python files match source; original test resources unchanged')
