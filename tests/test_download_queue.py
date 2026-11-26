"""Queue requests persist intent, never source content or completed installs."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.download_queue import DownloadQueue
from bible.providers import EXTRA
from bible.study_resources import StudyResource
from tests.test_library import RESOURCE


class DownloadQueueTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.root / "download-queue.json"
        self.queue = DownloadQueue(self.path)
        self.a = replace(RESOURCE, name="First", version="1.0")
        self.b = replace(RESOURCE, name="Second", version="2.0")

    def test_fifo_deduplication_uses_identity_and_preserves_a_different_provider(self):
        first = self.queue.enqueue(self.a)
        self.assertIs(self.queue.enqueue(self.a), first)
        foreign = replace(self.a, provider_id=EXTRA.id, source=EXTRA.name, source_url=EXTRA.url)
        other = self.queue.enqueue(foreign)
        self.assertIs(self.queue.start(), first)
        self.assertIsNone(self.queue.start())
        self.queue.finish(first)
        self.assertIs(self.queue.start(), other)
        self.assertNotEqual(first.key, other.key)

    def test_different_version_or_operation_cannot_silently_replace_the_same_target(self):
        self.queue.enqueue(self.a)
        for resource, operation in (
            (replace(self.a, version="2.0"), "install"),
            (self.a, "update"),
        ):
            with self.assertRaises(ValueError):
                self.queue.enqueue(resource, operation=operation)
        self.assertEqual(self.queue.requests[0].resource, self.a)

    def test_failed_item_does_not_block_the_next_request_and_retry_is_explicit(self):
        first = self.queue.enqueue(self.a)
        second = self.queue.enqueue(self.b)
        self.queue.start()
        self.queue.fail(first, "Rejected source")
        self.assertIs(self.queue.start(), second)
        self.queue.finish(second)
        self.assertIsNone(self.queue.start())
        restored = DownloadQueue(self.path)
        self.assertEqual(restored.requests[0].state, "failed")
        self.assertEqual(restored.requests[0].error, "Rejected source")
        retry = restored.enqueue(self.a)
        self.assertIs(restored.start(), retry)

    def test_pending_cancel_does_not_cancel_active_work(self):
        first = self.queue.enqueue(self.a)
        self.queue.enqueue(self.b)
        self.queue.start()
        self.assertFalse(self.queue.cancel(self.a.id))
        self.assertTrue(self.queue.cancel(self.b.id))
        self.assertEqual(self.queue.requests, [first])

    def test_restart_requires_explicit_resume_and_includes_study_requests(self):
        first = self.queue.enqueue(self.a)
        self.queue.enqueue(StudyResource())
        self.queue.start()
        restored = DownloadQueue(self.path)
        self.assertEqual([r.state for r in restored.requests], ["paused", "paused"])
        self.assertIsNone(restored.start())
        restored.resume()
        self.assertEqual(restored.start().key, first.key)
        self.assertEqual(restored.requests[1].resource.kind, "study")

    def test_write_failures_preserve_the_last_journal_and_memory_state(self):
        request = self.queue.enqueue(self.a)
        before = self.path.read_bytes()
        with patch("bible.download_queue.atomic_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.queue.enqueue(self.b)
            with self.assertRaises(OSError):
                self.queue.start()
            with self.assertRaises(OSError):
                self.queue.finish(request)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.queue.requests, [request])
        self.assertEqual(request.state, "queued")

    def test_invalid_journal_is_retained_and_blocks_mutations(self):
        for data in (
            b"{invalid original",
            b"[]",
            b'{"format":1,"requests":[{"resource":[]}]}',
            b"[" * 1200 + b"]" * 1200,
        ):
            with self.subTest(data=data[:40]):
                self.path.write_bytes(data)
                restored = DownloadQueue(self.path)
                self.assertTrue(restored.error)
                with self.assertRaises(ValueError):
                    restored.enqueue(self.a)
                self.assertEqual(self.path.read_bytes(), data)
