"""Reader geometry shared by GTK and the independent Pango worker."""

WIDTHS = {'narrow': 580, 'normal': 760, 'wide': 960}
SPACING = {'tight': 1, 'normal': 5, 'airy': 10, 'very-airy': 16}


def line_spacing(preferences):
    custom=getattr(preferences,'line_spacing_px',None)
    return custom if custom is not None else SPACING[preferences.line_spacing]


def text_width(preferences):
    custom=getattr(preferences,'text_width_px',None)
    return custom if custom is not None else WIDTHS[preferences.column_width]


def side_margin(preferences,default):
    custom=getattr(preferences,'side_margin_px',None)
    return custom if custom is not None else default
