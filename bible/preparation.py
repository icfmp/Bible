"""Cooperative cancellation at boundaries of native SWORD/Pango operations."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import CancelledError


def checkpoint(cancelled: Callable[[], bool] | None = None) -> None:
    """Raise CancelledError at a cooperative boundary when the supplied predicate requests it."""
    if cancelled is not None and cancelled():
        raise CancelledError()
