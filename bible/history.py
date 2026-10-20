"""Bounded per-tab passage history. Scrolling/verse following never append."""
MAX_HISTORY = 100


def seed(state):
    if not state.history and state.resource:
        state.history = [dict(resource=state.resource, reference=state.reference, scroll=state.scroll)]
        state.history_index = 0


def capture(state):
    seed(state)
    if 0 <= state.history_index < len(state.history):
        state.history[state.history_index]['scroll'] = state.scroll


def visit(state, resource, reference):
    current = state.history[state.history_index] if state.history else None
    if current and (current['resource'],current['reference']) == (resource,reference):
        return
    if current:
        capture(state)
    state.history = state.history[:state.history_index + 1]
    state.history.append(dict(resource=resource,reference=reference,scroll=0.0))
    state.history = state.history[-MAX_HISTORY:]
    state.history_index = len(state.history)-1
