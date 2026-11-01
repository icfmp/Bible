"""Stable identities and previously verified numbering; never infer from labels."""

# edition ID: (expected source vrs label, verified native storage system).
# Two sources use their own exact index because their published inventories
# differ from registered schemes. Their cross-edition alignment is unavailable.
EDITIONS={21:('org','Original','fra'),93:('org','YouVersion93','fra'),64:('org','Original','fra'),
          131:('org','YouVersion131','fra'),1:('eng','KJV','eng'),12:('eng','KJV','eng'),3034:('eng','KJV','eng')}
METADATA_URL='https://nodejs.bible.com/api/bible/version/3.3?id={edition}'
CONFIGURATION_URL='https://bible.youversionapi.com/3.1/configuration.json'
VERSIONS_URL='https://bible.youversionapi.com/3.1/versions.json?language_tag={language}&type=all'


def module_id(edition):
    if type(edition) is not int or not 1<=edition<=999999999:raise ValueError('Invalid edition identity')
    return 'YV'+str(edition)


def edition_id(name):
    if not isinstance(name,str) or not name.startswith('YV') or not name[2:].isdigit():raise ValueError('Invalid edition identity')
    number=int(name[2:])
    if module_id(number)!=name:raise ValueError('Invalid edition identity')
    return number


def storage_system(identifier):
    module_id(identifier)
    # Keep every existing module and annotation reference stable. New editions
    # receive an exact source-specific index, not an assumed cross-edition map.
    return EDITIONS[identifier][1] if identifier in EDITIONS else 'YouVersion'+str(identifier)
