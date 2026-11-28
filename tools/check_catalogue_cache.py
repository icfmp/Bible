"""Measure real per-provider cold/warm catalogue startup without timing fixtures."""

from __future__ import annotations

from collections.abc import Sequence

from bible.providers import Provider
from bible.library import Resource, CatalogueTimings

import argparse
import json
from pathlib import Path
import time
from bible.catalogue.catalogue_cache import CatalogueCache
from bible.library import catalogues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile")
    args = parser.parse_args()
    cache = CatalogueCache(Path(args.profile) / "catalogue-cache")
    for name, force in [("cold", True), ("warm", False)]:
        start = time.monotonic()
        events: list[dict[str, object]] = []

        def delivered(
            provider: Provider,
            items: Sequence[Resource],
            error: str | None,
            timings: CatalogueTimings,
        ) -> None:
            events.append(
                dict(
                    provider=provider.id,
                    at_seconds=time.monotonic() - start,
                    resources=len(items),
                    error=error,
                    **timings,
                )
            )

        result = catalogues(cache=cache, on_provider=delivered, force=force)
        print(
            json.dumps(
                dict(
                    mode=name,
                    first_seconds=events[0]["at_seconds"],
                    total_seconds=time.monotonic() - start,
                    resources=len(result.resources),
                    providers=events,
                )
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
