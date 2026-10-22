"""Apply only the published refresh method to exercise new behavioral regressions."""
import ast
from pathlib import Path
import unittest
from bible import reading_tab

tree=ast.parse(Path('/evidence/issue57/reading-tab-baseline.py').read_text())
kind=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ReadingTab')
function=next(n for n in kind.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_comparison')
function.name='baseline_refresh'
namespace=vars(reading_tab).copy()
exec(compile(ast.Module(body=[function],type_ignores=[]),'published-refresh','exec'),namespace)
reading_tab.ReadingTab.refresh_comparison=namespace['baseline_refresh']
suite=unittest.defaultTestLoader.loadTestsFromNames([
    'tests.test_comparison_sync.ComparisonTests.test_switching_primary_clears_an_obsolete_alignment_error',
    'tests.test_comparison_sync.ComparisonTests.test_switching_primary_recomputes_the_same_printed_psalm_reference',
])
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert len(result.failures)==2 and not result.errors, 'Both regressions must fail on the published method'
print('CONFIRMED: both new behavioral regressions fail on the published comparison cache')
