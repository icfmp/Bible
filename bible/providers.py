"""Reviewed SWORD providers. Catalogue and package paths are independent."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    url: str
    catalogue_url: str
    packages_url: str


CROSSWIRE = Provider('crosswire', 'CrossWire', 'https://www.crosswire.org/ftpmirror/pub/sword/',
                     'https://www.crosswire.org/ftpmirror/pub/sword/raw/mods.d.tar.gz',
                     'https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/')
# Source: AndBible app/src/main/res/raw/repositories.txt; see docs/SOURCES_AFFILIEES_11.md.
EXTRA = Provider('andbible-extra', 'AndBible Extra (Xiphos)', 'https://andbible.github.io/andbible-extra/',
                 'https://andbible.github.io/andbible-extra/mods.d.tar.gz',
                 'https://andbible.github.io/andbible-extra/zip/')
ANDBIBLE = Provider('andbible', 'AndBible', 'https://andbible.github.io/data/andbible/',
                    'https://andbible.github.io/data/andbible/mods.d.tar.gz',
                    'https://andbible.github.io/data/andbible/zip/')
STEP = Provider('step', 'STEP Bible (Tyndale)', 'https://public.modules.stepbible.org/',
                'https://public.modules.stepbible.org/catalog/mods.d.tar.gz',
                'https://public.modules.stepbible.org/packages/')
PROVIDERS = (CROSSWIRE, EXTRA, ANDBIBLE, STEP)
BY_ID = {p.id: p for p in PROVIDERS}
MODULE_NAME = r'[A-Za-z0-9_-]+'
RESOURCE_ID = rf'(?:[a-z0-9-]+~)?{MODULE_NAME}'


def identity(provider_id, module_name):
    if provider_id not in BY_ID or not re.fullmatch(MODULE_NAME, module_name):
        raise ValueError('Invalid resource identity')
    # '~' is not allowed in historical module names. Existing CrossWire IDs stay
    # byte-for-byte unchanged; other providers cannot collide with them.
    return module_name if provider_id == 'crosswire' else f'{provider_id}~{module_name}'


def module_name(resource_id):
    parts = resource_id.split('~')
    provider_id, name = parts if len(parts) == 2 else ('crosswire', resource_id)
    if identity(provider_id, name) != resource_id:
        raise ValueError('Invalid resource identity')
    return name
