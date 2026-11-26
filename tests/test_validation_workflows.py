"""Check declarative CI boundaries; GitHub evaluates expressions and glob rules."""

from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


class WorkflowPolicyTests(unittest.TestCase):
    def test_all_workflows_parse_and_job_dependencies_exist(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            with self.subTest(workflow=path.name):
                doc = workflow(path.name)
                self.assertIn("on", doc)
                self.assertTrue(doc["jobs"])
                for name, job in doc["jobs"].items():
                    needs = job.get("needs", [])
                    if isinstance(needs, str):
                        needs = [needs]
                    self.assertTrue(set(needs) <= doc["jobs"].keys(), name)

    def test_build_filters_only_exempt_reviewed_metadata_or_test_inputs(self):
        allowed = {
            "tools/*channel*.py",
            "tools/alpha_storage.py",
            "tools/site_render.py",
            "tools/site_assets/index.html",
            "tests/test_channel_*.py",
            "tests/test_alpha_storage.py",
            "tests/test_site_render.py",
            "tests/test_validation_workflows.py",
            "tests/test_ci_campaigns.py",
            "tools/ci_campaigns.py",
            "AGENTS.md",
            "README.md",
            "docs/**",
            "wiki/**",
            ".github/ISSUE_TEMPLATE/**",
            ".github/workflows/**",
        }
        doc = workflow("prerequisites.yml")["on"]
        for event in ("push", "pull_request"):
            filters = set(doc[event]["paths-ignore"])
            accepted = allowed | (
                {"tests/**", "tools/check_*.py", "tools/research/check_*.py"}
                if event == "push"
                else set()
            )
            self.assertLessEqual(filters, accepted)
            self.assertTrue({"AGENTS.md", "docs/**", ".github/workflows/**"} <= filters)
            self.assertEqual(doc[event]["branches"], ["main"])
        self.assertIn("workflow_dispatch", doc)

    def test_test_maintenance_keeps_pr_regressions_without_repackaging_main(self):
        events = workflow("prerequisites.yml")["on"]
        self.assertIn("tests/**", events["push"]["paths-ignore"])
        self.assertNotIn("tests/**", events["pull_request"]["paths-ignore"])
        self.assertNotIn("tools/check_*.py", events["pull_request"]["paths-ignore"])

    def test_host_suite_and_merged_package_boundaries_remain_present(self):
        jobs = workflow("prerequisites.yml")["jobs"]
        self.assertNotIn("if", jobs["prerequisites"])
        self.assertIn("if", jobs["flatpak"])
        self.assertEqual(jobs["flatpak"]["needs"], "prerequisites")
        commands = "\n".join(s.get("run", "") for s in jobs["flatpak"]["steps"])
        self.assertIn("tools.project_sources", commands)
        self.assertIn("$GITHUB_SHA", commands)
        self.assertIn("--require-packaged", commands)
        self.assertIn("--unshare=network", commands)
        self.assertIn("tests.test_personal_backup", commands)
        host = jobs["prerequisites"]["steps"]
        self.assertTrue(any("unittest discover" in s.get("run", "") for s in host))
        self.assertTrue(any("FRENCH_TESTS" in s.get("env", {}) for s in host))

    def test_extended_campaigns_depend_on_selection_without_gating_core_checks(self):
        jobs = workflow("prerequisites.yml")["jobs"]
        guarded = [
            s for s in jobs["flatpak"]["steps"] if "needs.prerequisites.outputs." in s.get("if", "")
        ]
        self.assertEqual(len(guarded), 4)
        for group in ("visual", "words", "contextual", "library"):
            self.assertIn(group, jobs["prerequisites"]["outputs"])
            self.assertTrue(any("outputs." + group in s["if"] for s in guarded))
        core = next(s for s in jobs["flatpak"]["steps"] if s.get("id") == "real_study")
        self.assertNotIn("needs.prerequisites.outputs.", core["if"])
        self.assertIn("tools.check_sustained_scroll", core["run"])

    def test_channel_main_retains_guarded_signed_lifecycle(self):
        doc = workflow("channel-restore-checks.yml")
        self.assertIn("pull_request", doc["on"])
        self.assertEqual(doc["on"]["push"]["branches"], ["main"])
        steps = doc["jobs"]["restore"]["steps"]
        units = next(s for s in steps if "tests.test_channel_gates" in s.get("run", ""))
        self.assertNotIn("if", units)
        signed = next(s for s in steps if "tools.check_flatpak_channel" in s.get("run", ""))
        self.assertIn("if", signed)

    def test_workflow_edits_have_lightweight_checks(self):
        doc = workflow("workflow-checks.yml")
        for event in ("push", "pull_request"):
            self.assertIn(".github/workflows/**", doc["on"][event]["paths"])
            self.assertIn("tools/ci_campaigns.py", doc["on"][event]["paths"])
        commands = "\n".join(s.get("run", "") for s in doc["jobs"]["policy"]["steps"])
        self.assertNotIn("flatpak", commands)
        self.assertIn("tests.test_ci_campaigns", commands)

    def test_expensive_diagnostic_campaigns_are_manual(self):
        for name in (
            "alpha-input-profile.yml",
            "alpha-native-profile.yml",
            "alpha-candidate-profile.yml",
            "alpha-channel-checks.yml",
            "alpha-performance.yml",
            "yves-proof.yml",
            "alpha-signed-update-feedback.yml",
            "audit-affiliated-sources.yml",
        ):
            events = workflow(name)["on"]
            if isinstance(events, str):
                events = {events: {}}
            self.assertIn("workflow_dispatch", events)
            self.assertNotIn("push", events)

    def test_only_main_triggers_automatic_publication_and_manual_input_is_explicit(self):
        doc = workflow("alpha-channel.yml")
        self.assertEqual(doc["on"]["workflow_run"]["branches"], ["main"])
        self.assertIn("if", doc["jobs"]["publish"])
        inputs = doc["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["verified_run"]["required"], "true")
        self.assertFalse(inputs["verified_run"].get("default"))
