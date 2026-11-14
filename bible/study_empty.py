"""A restrained native empty state; callers decide whether absence is genuine."""
from gi.repository import Adw
from .i18n import tr


def empty_state(title,description,icon):
    page=Adw.StatusPage(title=tr(title),description=tr(description),icon_name=icon,vexpand=True)
    page.add_css_class('compact')
    return page
