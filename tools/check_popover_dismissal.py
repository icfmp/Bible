"""Native pointer/key regression for #43; Xvfb is not manual GNOME validation."""
from pathlib import Path
import tempfile
from tests.test_ui import installed_fixture, spin
from tools.check_alpha_ui import X11Input
from bible.ui import Application, Window, Library, Gtk


def main():
    app = Application(); app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations', False)
    native = X11Input()
    with tempfile.TemporaryDirectory() as directory:
        installed_fixture(directory)
        installed_fixture(directory, 'Other')
        window = Window(app, Library(Path(directory) / 'translations'))
        window.set_default_size(1200, 900); window.present(); spin(duration=.3)
        try:
            for button, popover in [(window.passage_button, window.navigation),
                                    (window.comparison_button, window.comparison_popover),
                                    (window.appearance_button, window.appearance)]:
                for _ in range(3):
                    reference = window.active_tab.state.reference
                    native.click(button); assert popover.get_visible()
                    native.click(button); assert not popover.get_visible()
                    native.click(button); native.click_at(window.active_tab.text, 8, 100)
                    assert not popover.get_visible()
                    assert window.active_tab.state.reference == reference
                    native.click(button); native.key('Escape'); assert not popover.get_visible()
            for selected in [1, 0, 1]:
                native.click(window.comparison_button)
                native.click(window.comparison_choices)
                native.key('End' if selected else 'Home'); native.key('Return')
                spin(duration=.2)
                assert window.active_tab.state.comparison == window._comparison_names[selected]
                assert not window.comparison_popover.get_visible()
            aa = window.appearance
            for index in [0, 1, 2, 3, 0, 3]:
                native.click(window.appearance_button)
                # Expand Layout, then operate the nested native spacing chooser.
                expander = aa.controls.get_first_child()
                while not isinstance(expander, Gtk.Expander):
                    expander = expander.get_next_sibling()
                expander.set_expanded(True); spin(duration=.2)
                native.click(aa.line_spacing); native.key('Home')
                for _ in range(index): native.key('Down')
                native.key('Return'); spin(duration=.2)
                assert window.preferences.value.line_spacing == ['tight','normal','airy','very-airy'][index]
                assert aa.get_visible()  # Further immediate adjustments are intentional.
                native.click(aa.larger); native.click(aa.smaller)
                native.click_at(window.active_tab.text, 8, 100); assert not aa.get_visible()
            print('PASS: repeated trigger/outside/Escape; parent-surface fallback; comparison '
                  'apply/close; nested four spacing choices and continued Aa adjustment', flush=True)
        finally:
            window.close(); native.close()


if __name__ == '__main__': main()
