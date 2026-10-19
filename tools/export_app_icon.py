"""Export the approved PNG artwork to hicolor application icon sizes.

Development-only dependency: Pillow (python3-pil on Debian/Ubuntu).
Run from any directory: python3 tools/export_app_icon.py
"""
from pathlib import Path
from PIL import Image


def main():
    root = Path(__file__).resolve().parents[1] / "packaging" / "icons"
    with Image.open(root / "bible-source.png") as source:
        image = source.convert("RGBA")
        if image.width != image.height:
            raise ValueError("Expected square source artwork")
        if image.getextrema()[3][0] != 0:
            raise ValueError("Expected transparent source margins")
        for size in (32, 48, 64, 128, 256, 512):
            target = root / f"{size}x{size}" / "io.github.icfmp.Bible.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            image.resize((size, size), Image.Resampling.LANCZOS).save(target, optimize=True)
            print(target.relative_to(root.parents[1]))


if __name__ == "__main__":
    main()
