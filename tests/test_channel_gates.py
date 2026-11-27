"""Publication gates must reject an unverified source, changed artifact or key."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import channel_ci
from tools.flatpak_channel import prepare, digest


class ChannelGateTests(unittest.TestCase):
    def test_pages_artifact_waits_for_two_stable_observations(self) -> None:
        asset = dict(id=321, name="github-pages-first-2", expired=False, size_in_bytes=100)
        with (
            patch.dict(os.environ, dict(GITHUB_RUN_ID="123", GITHUB_RUN_ATTEMPT="2")),
            patch.object(
                channel_ci,
                "api",
                side_effect=[{"artifacts": []}, {"artifacts": [asset]}, {"artifacts": [asset]}],
            ) as fetch,
            patch.object(channel_ci.time, "sleep") as sleep,
        ):
            self.assertEqual(channel_ci.wait_pages_artifact(), asset)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(sleep.call_args_list, [((5,),), ((5,),)])

    def test_pages_wait_is_bounded_and_never_retries_access_or_identity_failures(self) -> None:
        from subprocess import CalledProcessError

        asset = dict(id=321, name="github-pages-first-2", expired=False, size_in_bytes=100)
        with patch.dict(os.environ, dict(GITHUB_RUN_ID="123", GITHUB_RUN_ATTEMPT="2")):
            with (
                patch.object(channel_ci, "api", return_value={"artifacts": []}),
                patch.object(channel_ci.time, "sleep") as sleep,
            ):
                with self.assertRaisesRegex(RuntimeError, "55 seconds"):
                    channel_ci.wait_pages_artifact()
                self.assertEqual(sleep.call_count, 11)
            with (
                patch.object(channel_ci, "api", side_effect=CalledProcessError(1, ["gh", "api"])),
                patch.object(channel_ci.time, "sleep") as sleep,
            ):
                with self.assertRaises(CalledProcessError):
                    channel_ci.wait_pages_artifact()
                sleep.assert_not_called()
            for records in ([dict(asset, expired=True)], [asset, asset]):
                with (
                    patch.object(channel_ci, "api", return_value={"artifacts": records}),
                    patch.object(channel_ci.time, "sleep") as sleep,
                ):
                    with self.assertRaises(AssertionError):
                        channel_ci.wait_pages_artifact()
                    sleep.assert_not_called()
            for records in (
                [{"artifacts": [asset]}, {"artifacts": [dict(asset, id=322)]}],
                [{"artifacts": [asset]}, {"artifacts": []}, {"artifacts": [dict(asset, id=322)]}],
            ):
                with (
                    patch.object(channel_ci, "api", side_effect=records),
                    patch.object(channel_ci.time, "sleep"),
                ):
                    with self.assertRaisesRegex(AssertionError, "identity changed"):
                        channel_ci.wait_pages_artifact()

    def verification(
        self, *, conclusion="success", repository="icfmp/Bible", corrupt: bool = False
    ):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                Path("event.json").write_text(json.dumps({"workflow_run": {"id": 123}}))
                execution = {
                    "status": "completed",
                    "conclusion": conclusion,
                    "head_branch": "main",
                    "head_repository": {"full_name": repository},
                    "path": ".github/workflows/prerequisites.yml",
                    "head_sha": channel_ci.BASELINE,
                }

                def command(args, **kwargs: object) -> None:
                    if args[:3] == ["gh", "run", "download"]:
                        incoming = Path("incoming")
                        incoming.mkdir()
                        bundle = incoming / "Bible-alpha.flatpak"
                        bundle.write_bytes(b"test artifact")
                        (incoming / "build-info.json").write_text(
                            json.dumps(
                                {
                                    "commit": channel_ci.BASELINE,
                                    "architecture": "x86_64",
                                    "prerequisites": "success",
                                    "ci": "https://github.com/icfmp/Bible/actions/runs/123",
                                    "flatpak_ref": "app/io.github.icfmp.Bible/x86_64/master",
                                    "sha256": "0" * 64 if corrupt else digest(bundle),
                                }
                            )
                        )

                env = {"GITHUB_EVENT_PATH": str(Path("event.json").resolve())}
                with (
                    patch.dict(os.environ, env),
                    patch.object(channel_ci, "api", return_value=execution),
                    patch.object(channel_ci.subprocess, "run", side_effect=command),
                ):
                    return channel_ci.verify()
            finally:
                os.chdir(previous)

    def test_green_main_artifact_is_identified(self) -> None:
        self.assertEqual(self.verification(), {"source": channel_ci.BASELINE, "ci_run": "123"})

    def test_failed_ci_cannot_publish(self) -> None:
        with self.assertRaisesRegex(AssertionError, "CI must be green"):
            self.verification(conclusion="failure")

    def test_fork_run_cannot_publish(self) -> None:
        with self.assertRaises(AssertionError):
            self.verification(repository="untrusted/Bible")

    def test_changed_artifact_cannot_publish(self) -> None:
        with self.assertRaises(AssertionError):
            self.verification(corrupt=True)

    def test_signing_key_change_preserves_previous_site(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / "site"
            alpha = site / "alpha"
            alpha.mkdir(parents=True)
            old = {"source_commit": "a" * 40, "signing_fingerprint": "A" * 40}
            metadata = alpha / "provenance.json"
            metadata.write_text(json.dumps(old))
            with self.assertRaisesRegex(AssertionError, "signing key change"):
                prepare(
                    "unused",
                    site,
                    "https://example.invalid/Bible",
                    "unused",
                    "B" * 40,
                    "a" * 40,
                    "1",
                    "1",
                )
            self.assertEqual(json.loads(metadata.read_text()), old)

    def test_rollback_preserves_previous_site(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / "site"
            alpha = site / "alpha"
            alpha.mkdir(parents=True)
            old = {"source_commit": "a" * 40, "signing_fingerprint": "A" * 40}
            metadata = alpha / "provenance.json"
            metadata.write_text(json.dumps(old))
            import subprocess

            with patch(
                "tools.flatpak_channel.subprocess.run",
                return_value=subprocess.CompletedProcess([], 1),
            ):
                with self.assertRaisesRegex(AssertionError, "alpha rollback"):
                    prepare(
                        "unused",
                        site,
                        "https://example.invalid/Bible",
                        "unused",
                        "A" * 40,
                        "b" * 40,
                        "1",
                        "1",
                    )
            self.assertEqual(json.loads(metadata.read_text()), old)

    def test_non_https_repository_is_not_public(self) -> None:
        with self.assertRaises(AssertionError):
            prepare(
                "unused",
                "unused",
                "http://example.invalid/Bible",
                "unused",
                "A" * 40,
                "a" * 40,
                "1",
                "1",
            )
