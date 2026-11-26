"""Native theme lookup with application assets and GTK's own resource fallback."""

from pathlib import Path

ICON_ROOT = Path(__file__).with_name("icons")


def configure_theme(theme):
    # Keep the user's theme. hicolor provides the app's complete fallback set,
    # including on desktops which do not install Adwaita. Avoid accumulating
    # duplicate search paths when several Bible windows share one display.
    """Add application icon assets once while retaining native theme/resource fallback lookup."""
    path = str(ICON_ROOT)
    if path not in theme.get_search_path():
        theme.add_search_path(path)
    # Do not provide a partial hicolor/index.theme: it would shadow GTK's
    # complete built-in directory inventory, including its missing-image icon.
    return theme
