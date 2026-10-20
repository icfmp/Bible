"""Compatibility entry point: export the authoritative SVG with Inkscape.

The original approved PNG remains as an artistic reference. Raster deliveries
now come from the 128-unit vector, not another resampling of that reference.
"""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('export_vector_icons.py')),run_name='__main__')
