"""Run affected tests against installed application imports, from outside checkout."""
import inspect
import json
from pathlib import Path
import sys
import unittest

names = ['book_preparation', 'pagination', 'book_stream', 'immersion', 'ui',
         'provider_ui', 'library', 'reference_resolution', 'notes', 'session',
         'highlights', 'highlight_ui', 'reading_direction', 'reading_sync',
         'appearance', 'passage_actions', 'comparison_sync', 'commentary']
suite = unittest.defaultTestLoader.loadTestsFromNames(['tests.test_' + n for n in names])

def flatten(suite):
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            yield from flatten(entry)
        else:
            yield entry

# This native-event test normally creates a nested Xvfb. Run it separately on
# its own host-provided display; Xvfb is a test tool, not an app dependency.
separate = 'tests.test_immersion.ImmersionTests.test_native_click_targets_notes_and_context_copy_on_each_page'
filtered = unittest.TestSuite(t for t in flatten(suite) if t.id() != separate)
result = unittest.TextTestRunner(verbosity=2).run(filtered)
imports = {name: inspect.getfile(module) for name, module in list(sys.modules.items())
           if (name == 'bible' or name.startswith('bible.')) and hasattr(module, '__file__')}
assert imports and all(Path(p).is_relative_to('/app/lib/bible-python/bible') for p in imports.values()), imports
Path('/evidence/flatpak/affected-suite.json').write_text(json.dumps({
    'code': 'installed-package', 'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': result.skipped, 'imports': imports,
    'separate_native_test': separate,
    'manual_gnome_validation': False,
}, indent=2) + '\n')
raise SystemExit(not result.wasSuccessful())
