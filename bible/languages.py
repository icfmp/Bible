"""CLDR names (Babel) with maintained ISO 639-3 coverage, never merge source codes."""
from functools import lru_cache
import gettext
import json
from pathlib import Path
import re
from babel import Locale, UnknownLocaleError
from babel.core import get_global
from babel.localedata import locale_identifiers
from .i18n import LANGUAGE, tr


@lru_cache(maxsize=1)
def iso_languages():
    for root in [Path('/app/share'),Path('/usr/share')]:
        path=root/'iso-codes/json/iso_639-3.json'
        if path.is_file():
            values=json.loads(path.read_text())['639-3']
            return {code:entry for entry in values for code in [entry['alpha_3'],entry.get('alpha_2')] if code}
    return {}


@lru_cache(maxsize=8)
def iso_translation(interface):
    for root in ['/app/share/locale','/usr/share/locale']:
        try:return gettext.translation('iso_639-3',localedir=root,languages=[interface])
        except OSError:pass
    return gettext.NullTranslations()


@lru_cache(maxsize=4096)
def language_info(code, interface=None):
    interface=(interface or LANGUAGE).split('_')[0].split('-')[0].split(':')[0]
    interface='fr' if interface=='fr' else 'en'
    if not isinstance(code,str) or not re.fullmatch(r'[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*',code):
        return (('Langue non identifiée' if interface=='fr' else 'Unidentified language')+f' ({code})','')
    parts=code.replace('_','-').split('-');base=parts[0].lower()
    alias=get_global('language_aliases').get(base,base).split('_')[0]
    locale=Locale(interface)
    name=locale.languages.get(alias)
    if not name:
        entry=iso_languages().get(base)
        if entry:name=iso_translation(interface).gettext(entry['name'])
    if not name or base=='und':
        return (('Langue non identifiée' if interface=='fr' else 'Unidentified language')+f' ({code})','')
    qualifiers=[]
    for part in parts[1:]:
        if len(part)==4 and part.isalpha():qualifiers.append(locale.scripts.get(part.title(),part))
        elif len(part) in (2,3):qualifiers.append(locale.territories.get(part.upper(),part))
        else:qualifiers.append(part)
    if qualifiers:name+=' — '+', '.join(qualifiers)
    native=''
    # Babel's missing-locale fallback linearly normalizes its entire locale
    # inventory several times. Most ISO 639-3 catalogue languages have no CLDR
    # native locale at all: do not perform that expensive failed lookup.
    if alias in native_language_codes():
        try:
            own=Locale.parse(code.replace('-','_'))
            native=own.get_display_name(own) or ''
        except (UnknownLocaleError,ValueError):pass
    return name,native


def language_name(code):return language_info(code)[0]


@lru_cache(maxsize=1)
def native_language_codes():
    return frozenset(identifier.split('_')[0] for identifier in locale_identifiers())


def search_terms(code):
    names=language_info(code)
    return ' '.join((code,*names,language_info(code,'fr')[0],language_info(code,'en')[0]))
