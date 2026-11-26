"""Bounded per-tab passage history. Scrolling/verse following never append."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .session import TabState

MAX_HISTORY = 100


def seed(state: TabState) -> None:
    """Initialize history only for a tab with an identified resource."""
    if not state.history and state.resource:
        state.history = [
            dict(resource=state.resource, reference=state.reference, scroll=state.scroll)
        ]
        state.history_index = 0


def capture(state: TabState) -> None:
    """Update the current entry’s position without recording a new visit."""
    seed(state)
    if 0 <= state.history_index < len(state.history):
        state.history[state.history_index]["scroll"] = state.scroll


def visit(state: TabState, resource: str, reference: str) -> None:
    """Record an explicit new passage after capturing the current position and truncating forward history."""
    current = state.history[state.history_index] if state.history else None
    if current and (current["resource"], current["reference"]) == (resource, reference):
        return
    if current:
        capture(state)
    state.history = state.history[: state.history_index + 1]
    state.history.append(dict(resource=resource, reference=reference, scroll=0.0))
    state.history = state.history[-MAX_HISTORY:]
    state.history_index = len(state.history) - 1
