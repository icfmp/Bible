"""A restrained native empty state; callers decide whether absence is genuine."""

from gi.repository import Adw
from ..i18n import tr


def empty_state(title: str, description: str, icon: str) -> Adw.StatusPage:
    """Create the shared translated empty state without deciding resource availability."""
    page = Adw.StatusPage(
        title=tr(title), description=tr(description), icon_name=icon, vexpand=True
    )
    page.add_css_class("compact")
    return page
