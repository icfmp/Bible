"""Keep round navigation targets in the viewport's safe text margins."""
from gi.repository import Gtk


def position(button,left,right,top,height,width):
    button_width=max(40,button.get_width());button_height=max(40,button.get_height())
    button.set_valign(Gtk.Align.START)
    if button.get_halign()==Gtk.Align.START:
        button.set_margin_start(max(6,int(left-button_width-20)))
    else:button.set_margin_end(max(6,int(width-right-button_width-20)))
    # Reserve the bottom for the selection toolbar/footer, and leave verse text
    # untouched: only overlay allocations change as the viewport changes.
    button.set_margin_top(max(0,int(top+max(0,height-button_height)*.82)))
