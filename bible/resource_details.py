"""Plain, noninteractive presentation of untrusted provider metadata."""
from html.parser import HTMLParser
import re
from .i18n import tr


class PlainMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('br', 'p', 'div'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value):
    parser = PlainMetadata()
    parser.feed(value)
    # About fields often contain SWORD's legacy RTF paragraph markers.
    value = ''.join(parser.parts)
    # Some catalogues double the backslash and omit the space before an
    # immediately following capital (e.g. \\par\\parSource:). Keep all words.
    value = re.sub(r'\\+par(?:d)?(?=$|[^a-z])\s*', '\n', value)
    return re.sub(r'\\+(?:qc|b0?|i0?)\b\s*', '', value).strip()


from .languages import language_name


def details(resource):
    import json
    try:pending=resource.provider_id=='youversion' and json.loads(resource.acquisition).get('_catalogue_summary')
    except (ValueError,AttributeError):pending=False
    availability = (tr('Access key required. Encrypted resources are not supported.') if resource.locked
                    else tr('Unsupported format.') if not resource.installable
                    else tr('Distributed by the source. Download is checked before installation.'))
    if resource.provider_id=='youversion' and not resource.installable:
        availability=tr('No offline package supplied by the source.')
    numbering=resource.versification
    if resource.provider_id=='youversion' and numbering.startswith('YouVersion'):
        numbering=tr('Numbering supplied by this edition')
        availability+='\n'+tr('Automatic verse alignment with other editions is unavailable. Independent parallel reading remains available.')
    provenance=''
    if resource.provider_id=='bible-resources':
        from .curated_catalogue import package_record
        try:entry=package_record(resource)
        except (ValueError,TypeError,KeyError):entry=None
        provenance=(tr('Source edition')+': '+entry['canonical_edition_id']+' / '+entry['edition']
                    if entry else tr('Source edition metadata could not be verified.'))
        # Report publisher-supplied approval metadata, never turn a draft's
        # prose into application-authored claims or silently translate it.
        profiles=entry.get('profiles',{}) if entry else {}
        if isinstance(profiles,dict):
            for language,profile in profiles.items():
                if not isinstance(profile,dict):continue
                if all(isinstance(profile.get(key),str) and profile[key] for key in ('approved_at','approved_by','approval_url')):
                    provenance+='\n'+tr('Profile approval reported by the source')+' ('+str(language)+'): '+profile['approved_at']+'\n'+profile['approval_url']
    return '\n\n'.join([
        f'{plain(resource.description)} ({resource.name})',
        f'{tr("Resource type")}: '+tr({'commentary':'Commentaries','study':'Study resources','dictionary':'Dictionary or lexicon','general':'General book'}.get(resource.kind,'Bibles')),
        f'{tr("Author")}: {plain(resource.author)}' if resource.author else '',
        f'{tr("Language")}: {language_name(resource.language)}',
        f'{tr("Source")}: {resource.source}\n{resource.source_url}',
        f'{tr("Version")}: {resource.version}' if getattr(resource,'version','') else '',
        tr('Version notes (source)')+':\n'+plain(resource.release_notes) if getattr(resource,'release_notes','') else '',
        provenance,
        f'{tr("License")}: {plain(resource.license)}',
        f'{tr("Verse numbering")}: {numbering}' if resource.kind in ('bible','commentary','study') else '',
        availability,
        f'{tr("Conditions and attribution")}:\n' + (
            tr('Loading edition details…') if pending else
            plain(resource.conditions) or tr('No additional conditions supplied by the source.')),
        plain(resource.about),
        tr('Check the source conditions before downloading. Availability does not grant redistribution rights.'),
    ])
