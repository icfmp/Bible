"""Reader geometry shared by GTK and the independent Pango worker."""

EDITORIAL_GAP = 5  # Extra space after a source-typed editorial reference block.
# Internal leading for Bible and immersive headings, including wrapped lines.
# Keep this in the Pango page plan as well as GtkTextTag allocation. The study
# sidebar/source preface already use a more generous 1.5 line height.
HEADING_LINE_HEIGHT = 1.15
WIDTHS = {'narrow': 580, 'normal': 760, 'wide': 960}
SPACING = {'tight': 1, 'normal': 5, 'airy': 10, 'very-airy': 16}


def line_spacing(preferences):
    custom=getattr(preferences,'line_spacing_px',None)
    return custom if custom is not None else SPACING[preferences.line_spacing]


def paragraph_space_size(preferences):
    # A paragraph boundary is spacing, not an additional full-sized text line.
    return max(1,preferences.size*.25)


def text_width(preferences):
    custom=getattr(preferences,'text_width_px',None)
    return custom if custom is not None else WIDTHS[preferences.column_width]


def side_margin(preferences,default):
    custom=getattr(preferences,'side_margin_px',None)
    return custom if custom is not None else default
