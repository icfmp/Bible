"""Exercise workflow event/job gates without building or publishing an app."""
from fnmatch import fnmatchcase
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    # BaseLoader preserves GitHub's `on` key and expression strings (YAML 1.2).
    return yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)


def triggered(document, event, paths, branch='main'):
    events = document['on']
    if isinstance(events, str):
        return event == events
    if event not in events:
        return False
    config = events[event] or {}
    if 'branches' in config and not any(fnmatchcase(branch, p) for p in config['branches']):
        return False
    if 'paths' in config and not any(fnmatchcase(path, p) for path in paths for p in config['paths']):
        return False
    if 'paths-ignore' in config and all(any(fnmatchcase(path, p) for p in config['paths-ignore']) for path in paths):
        return False
    return True


class WorkflowPolicyTests(unittest.TestCase):
    def test_all_workflows_parse_and_job_dependencies_exist(self):
        for path in sorted((ROOT / '.github/workflows').glob('*.yml')):
            with self.subTest(workflow=path.name):
                doc = workflow(path.name)
                self.assertIn('on', doc)
                self.assertTrue(doc['jobs'])
                for name, job in doc['jobs'].items():
                    needs = job.get('needs', [])
                    if isinstance(needs, str):
                        needs = [needs]
                    self.assertTrue(set(needs) <= doc['jobs'].keys(), name)

    def test_documentation_and_maintenance_do_not_build_but_mixed_app_changes_do(self):
        doc = workflow('prerequisites.yml')
        for event in ('push', 'pull_request'):
            for path in ('AGENTS.md', 'README.md', 'docs/VALIDATION.md', 'docs/captures/image.png',
                         'wiki/Home.md', '.github/workflows/prerequisites.yml',
                         '.github/workflows/channel-restore-checks.yml',
                         'tools/check_flatpak_channel.py', 'tests/test_validation_workflows.py'):
                with self.subTest(event=event, path=path):
                    self.assertFalse(triggered(doc, event, [path]))
                    self.assertTrue(triggered(doc, event, [path, 'bible/reading_tab.py']))

    def test_application_and_build_inputs_still_run_regressions(self):
        doc = workflow('prerequisites.yml')
        for event in ('push', 'pull_request'):
            for path in ('bible/ui.py', 'bible/data/topics.json',
                         'packaging/io.github.icfmp.Bible.json', 'packaging/icons/example.svg',
                         'tests/test_notes.py', 'tools/project_sources.py', 'LICENSE'):
                with self.subTest(event=event, path=path):
                    self.assertTrue(triggered(doc, event, [path]))
        self.assertFalse(triggered(doc, 'push', ['bible/ui.py'], branch='feat/example'))
        self.assertTrue(triggered(doc, 'workflow_dispatch', []))

    def test_pr_checks_host_and_main_builds_exact_merged_package(self):
        jobs = workflow('prerequisites.yml')['jobs']
        self.assertNotIn('if', jobs['prerequisites'])
        self.assertEqual(jobs['flatpak']['if'], "github.event_name != 'pull_request'")
        self.assertEqual(jobs['flatpak']['needs'], 'prerequisites')
        commands = '\n'.join(s.get('run', '') for s in jobs['flatpak']['steps'])
        self.assertIn('tools.project_sources "$GITHUB_SHA"', commands)
        self.assertIn('--require-packaged', commands)
        self.assertIn('--unshare=network', commands)
        self.assertIn('tests.test_personal_backup', commands)

    def test_channel_main_retains_real_signed_lifecycle(self):
        doc = workflow('channel-restore-checks.yml')
        self.assertTrue(triggered(doc, 'pull_request', ['tools/check_flatpak_channel.py']))
        self.assertTrue(triggered(doc, 'push', ['tools/check_flatpak_channel.py']))
        steps = doc['jobs']['restore']['steps']
        units = next(s for s in steps if 'tests.test_channel_gates' in s.get('run', ''))
        self.assertNotIn('if', units)
        signed = next(s for s in steps if s.get('run') == 'python3 -m tools.check_flatpak_channel')
        self.assertEqual(signed['if'], "github.event_name != 'pull_request'")

    def test_workflow_edits_have_lightweight_checks(self):
        doc = workflow('workflow-checks.yml')
        for event in ('push', 'pull_request'):
            for path in (ROOT / '.github/workflows').glob('*.yml'):
                self.assertTrue(triggered(doc, event, [str(path.relative_to(ROOT))]))
        commands = '\n'.join(s.get('run', '') for s in doc['jobs']['policy']['steps'])
        self.assertNotIn('flatpak', commands)
        self.assertIn('tests.test_validation_workflows', commands)

    def test_source_audit_is_explicit_and_application_still_checks_real_resources(self):
        audit = workflow('audit-affiliated-sources.yml')
        self.assertTrue(triggered(audit, 'workflow_dispatch', []))
        self.assertFalse(triggered(audit, 'push', ['bible/ui.py']))
        steps = workflow('prerequisites.yml')['jobs']['prerequisites']['steps']
        commands = '\n'.join(s.get('run', '') for s in steps)
        self.assertNotIn('tools/inspect_gnome_hig.py', commands)
        self.assertNotIn('tools/check_environment.py --network', commands)
        self.assertIn('tools/check_environment.py', commands)
        self.assertIn('unittest discover', commands)
        self.assertIn('LANGUAGE=fr', commands)
        self.assertIn('BIBLE_OFFLINE_PREFIX', str(steps))

    def test_expensive_diagnostic_campaigns_require_explicit_dispatch(self):
        for name in ('alpha-input-profile.yml', 'alpha-native-profile.yml',
                     'alpha-candidate-profile.yml', 'alpha-channel-checks.yml',
                     'alpha-performance.yml', 'yves-proof.yml',
                     'alpha-signed-update-feedback.yml'):
            with self.subTest(workflow=name):
                doc = workflow(name)
                self.assertTrue(triggered(doc, 'workflow_dispatch', []))
                self.assertFalse(triggered(doc, 'push', ['bible/ui.py'], branch='feat/26-youversion-language-catalogue'))
                self.assertNotIn('push', doc['on'] if isinstance(doc['on'], dict) else {})
        inputs = workflow('alpha-channel.yml')['on']['workflow_dispatch']['inputs']
        self.assertEqual(inputs['verified_run']['required'], 'true')
        self.assertFalse(inputs['verified_run'].get('default'))

    def test_only_main_can_trigger_automatic_publication(self):
        doc = workflow('alpha-channel.yml')
        self.assertEqual(doc['on']['workflow_run']['branches'], ['main'])
        condition = doc['jobs']['publish']['if']
        self.assertIn("github.ref == 'refs/heads/main'", condition)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", condition)


if __name__ == '__main__':
    unittest.main()
