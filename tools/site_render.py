"""Render the alpha landing page without changing the signed channel."""

from __future__ import annotations

from collections.abc import Mapping
from os import PathLike

import html
from pathlib import Path
import shutil
from string import Template


def render(site: str | PathLike[str], provenance: Mapping[str, str]) -> None:
    """Write the landing page while preserving existing signed channel files."""
    assets = Path(__file__).with_name("site_assets")
    site = Path(site)
    shutil.copytree(
        assets, site / "assets", dirs_exist_ok=True, ignore=shutil.ignore_patterns("index.html")
    )
    values = {key: html.escape(str(value), quote=True) for key, value in provenance.items()}
    values["source_url"] = html.escape(
        provenance.get("source_url", "alpha/" + provenance["source_archive"]), quote=True
    )
    values["short_commit"] = values["source_commit"][:12]
    (site / "index.html").write_text(
        Template((assets / "index.html").read_text()).substitute(values), encoding="utf-8"
    )
