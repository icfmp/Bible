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
            for _ in range(3):
                native.click(window.comparison_button)
                assert window.comparison_choices.list.get_mapped()
                window.comparison_choices.list.get_row_at_index(0).grab_focus()
                native.key('End');native.key('Return');spin(duration=.2)
                assert window.active_tab.state.comparison==window._comparison_names[-1]
                assert not window.comparison_popover.get_visible()
                native.click(window.compared_version);native.key('Escape')
                assert not window.compared_version.popover.get_visible()
                native.click(window.comparison_button);native.click(window.comparison_choices.list.get_row_at_index(0))
                assert window.active_tab.state.comparison is None
                assert not window.comparison_popover.get_visible()
            aa = window.appearance
            for index in [0, 1, 2, 3, 0, 3]:
                native.click(window.appearance_button)
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
