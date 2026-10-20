"""Reproducible SVG exports. Requires Inkscape; no network or image generation."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
source=root/'packaging/icons/scalable/apps/io.github.icfmp.Bible.svg'
for size in [32,48,64,128,256,512]:
    target=root/f'packaging/icons/{size}x{size}/io.github.icfmp.Bible.png'
    subprocess.run(['inkscape',str(source),f'--export-width={size}',f'--export-height={size}',f'--export-filename={target}'],check=True)
