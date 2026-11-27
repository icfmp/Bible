"""Summarize high-water and end-of-process live native allocations without data."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict
import json
from pathlib import Path
import sys

if sys.platform == "win32":
    raise SystemExit("Memray native diagnostics require Linux or macOS")

import memray


class AllocationSummary(TypedDict):
    """Bounded allocation counts and frame locations, without allocated contents."""

    bytes: int
    allocations: int
    thread: str
    stack: list[tuple[str, str, int]]


def summarize(records: Iterable[memray.AllocationRecord]) -> list[AllocationSummary]:
    """Retain the largest groups and bounded Python/native frame locations."""
    result: list[AllocationSummary] = []
    for record in sorted(records, key=lambda r: r.size, reverse=True)[:30]:
        try:
            stack = list(record.hybrid_stack_trace())[-35:]
        except (NotImplementedError, RuntimeError):
            stack = list(record.stack_trace())[-35:]
        result.append(
            dict(
                bytes=record.size,
                allocations=record.n_allocations,
                thread=record.thread_name,
                stack=stack,
            )
        )
    return result


def main() -> None:
    """Write bounded peak/live allocation summaries from an existing trace."""
    reader = memray.FileReader(sys.argv[1])
    with reader:
        peak = summarize(reader.get_high_watermark_allocation_records())
        retained = summarize(reader.get_leaked_allocation_records())
    report = dict(
        peak=peak,
        retained_at_tracker_end=retained,
        limitation="Tracker/end-of-process retained allocations include intentional caches and tracer overhead; this is not by itself a leak verdict.",
    )
    Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(peak_groups=len(peak), retained_groups=len(retained))))


if __name__ == "__main__":
    main()
