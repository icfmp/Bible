"""Render the alpha landing page without changing the signed channel."""
import html
from pathlib import Path
import shutil
from string import Template


def render(site, provenance):
    assets = Path(__file__).with_name('site_assets')
    site = Path(site)
    shutil.copytree(assets, site / 'assets', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('index.html'))
    values = {key: html.escape(str(value), quote=True) for key, value in provenance.items()}
    values['short_commit'] = values['source_commit'][:12]
    (site / 'index.html').write_text(
        Template((assets / 'index.html').read_text()).substitute(values), encoding='utf-8')
