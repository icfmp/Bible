"""Book-name UI metadata and French input aliases, never a list of module contents."""
import re
import unicodedata

FRENCH = dict(zip(
    'Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'.split(),
    ['Genèse', 'Exode', 'Lévitique', 'Nombres', 'Deutéronome', 'Josué', 'Juges', 'Ruth',
     '1 Samuel', '2 Samuel', '1 Rois', '2 Rois', '1 Chroniques', '2 Chroniques', 'Esdras',
     'Néhémie', 'Esther', 'Job', 'Psaumes', 'Proverbes', 'Ecclésiaste', 'Cantique des cantiques',
     'Ésaïe', 'Jérémie', 'Lamentations', 'Ézéchiel', 'Daniel', 'Osée', 'Joël', 'Amos', 'Abdias',
     'Jonas', 'Michée', 'Nahum', 'Habacuc', 'Sophonie', 'Aggée', 'Zacharie', 'Malachie',
     'Matthieu', 'Marc', 'Luc', 'Jean', 'Actes', 'Romains', '1 Corinthiens', '2 Corinthiens',
     'Galates', 'Éphésiens', 'Philippiens', 'Colossiens', '1 Thessaloniciens', '2 Thessaloniciens',
     '1 Timothée', '2 Timothée', 'Tite', 'Philémon', 'Hébreux', 'Jacques', '1 Pierre', '2 Pierre',
     '1 Jean', '2 Jean', '3 Jean', 'Jude', 'Apocalypse']))
FRENCH.update({'Tob': 'Tobie', 'Jdt': 'Judith', 'Wis': 'Sagesse', 'Sir': 'Siracide',
               'Bar': 'Baruch', '1Macc': '1 Maccabées', '2Macc': '2 Maccabées',
               '3Macc': '3 Maccabées', '4Macc': '4 Maccabées', '1Esd': '1 Esdras',
               '2Esd': '2 Esdras', 'PrMan': 'Prière de Manassé', 'Ps151': 'Psaume 151',
               'AddEsth': 'Additions à Esther', 'AddDan': 'Additions à Daniel',
               'EpJer': 'Lettre de Jérémie', 'PrAzar': 'Prière d’Azarias',
               'Sus': 'Suzanne', 'Bel': 'Bel et le Dragon'})


def normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(char) and char.isalnum())


# Input aliases are static metadata; do not normalize the entire table for each verse.
_INPUT_ALIASES = {normalized(label): code for code, label in FRENCH.items()}


def canonical_input(reference):
    """Resolve full French names; let SWORD resolve its own names and abbreviations."""
    match = re.fullmatch(r'(.+?)[ .]+([1-9][0-9]*(?:[.:][1-9][0-9]*)?)', reference.strip())
    if match:
        name, numbers = match.groups()
        code = _INPUT_ALIASES.get(normalized(name))
        if code:
            return f'{code}.{numbers}'
    return reference.strip()


def display_name(code, fallback, language='en'):
    return FRENCH.get(code, fallback) if language.startswith('fr') else fallback
