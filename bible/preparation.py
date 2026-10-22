"""Cooperative cancellation at boundaries of native SWORD/Pango operations."""
from concurrent.futures import CancelledError


def checkpoint(cancelled=None):
    if cancelled is not None and cancelled():
        raise CancelledError()
