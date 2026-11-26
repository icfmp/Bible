"""Cooperative cancellation at boundaries of native SWORD/Pango operations."""

from concurrent.futures import CancelledError


def checkpoint(cancelled=None):
    """Raise CancelledError at a cooperative boundary when the supplied predicate requests it."""
    if cancelled is not None and cancelled():
        raise CancelledError()
