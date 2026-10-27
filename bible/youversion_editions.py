"""Explicitly reviewed pilot editions; metadata labels never infer numbering."""

# edition ID: (expected source vrs label, verified native storage system).
# Two sources use their own exact index because their published inventories
# differ from registered schemes. Their cross-edition alignment is unavailable.
EDITIONS={21:('org','Original','fra'),93:('org','YouVersion93','fra'),64:('org','Original','fra'),
          131:('org','YouVersion131','fra'),1:('eng','KJV','eng'),12:('eng','KJV','eng'),3034:('eng','KJV','eng')}
METADATA_URL='https://nodejs.bible.com/api/bible/version/3.3?id={edition}'


def module_id(edition):
    if type(edition) is not int or edition not in EDITIONS:raise ValueError('Unreviewed edition')
    return 'YV'+str(edition)


def edition_id(name):
    if not isinstance(name,str) or not name.startswith('YV') or not name[2:].isdigit():raise ValueError('Invalid edition identity')
    number=int(name[2:])
    if module_id(number)!=name:raise ValueError('Invalid edition identity')
    return number
