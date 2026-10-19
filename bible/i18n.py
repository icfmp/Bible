"""Small French/English message catalogue shared by native views."""
import locale
import os

FR = {
    'Translations': 'Traductions', 'Load catalogue': 'Charger le catalogue',
    'Download': 'Télécharger', 'Open': 'Ouvrir', 'Previous chapter': 'Chapitre précédent',
    'Next chapter': 'Chapitre suivant', 'No translation installed. Load the catalogue to choose one.':
        'Aucune traduction installée. Chargez le catalogue pour en choisir une.',
    'Loading catalogue…': 'Chargement du catalogue…', 'Downloading…': 'Téléchargement…',
    'Ready': 'Prêt', 'Retry using the same button.': 'Réessayez avec le même bouton.',
    'Reference (e.g. John 1:1)': 'Référence (par ex. John 1:1)',
    'Downloadable resources — source: CrossWire': 'Traductions téléchargeables — source : CrossWire',
    'No supported resource found.': 'Aucune ressource compatible trouvée.',
}
LANGUAGE = os.environ.get('LANGUAGE') or locale.getlocale()[0] or 'en'


def tr(message):
    return FR.get(message, message) if LANGUAGE.startswith('fr') else message


FR.update({
    'New tab': 'Nouvel onglet', 'Open passage in new tab': 'Ouvrir le passage dans un nouvel onglet',
    'Study': 'Étude', 'Study tools are not implemented yet.':
        'Les outils d’étude ne sont pas encore disponibles.',
    'Choose a translation': 'Choisir une traduction', 'Missing translation': 'Traduction absente',
    'This translation is no longer installed. Download it again or choose another translation.':
        'Cette traduction n’est plus installée. Téléchargez-la à nouveau ou choisissez une autre traduction.',
    'Unable to read this passage.': 'Impossible de lire ce passage.',
    'Unable to restore the session. The original file has been preserved.':
        'Impossible de restaurer la session. Le fichier original a été conservé.',
    'Unable to save the session.': 'Impossible d’enregistrer la session.',
    'Session saving is disabled to preserve the original file.':
        'L’enregistrement de la session est désactivé pour préserver le fichier original.',
})

FR.update({
    'Choose a passage': 'Choisir un passage', 'Version': 'Version', 'Book': 'Livre',
    'Chapter': 'Chapitre', 'Verse': 'Verset', 'Direct reference': 'Saisie directe',
    'Open in this tab': 'Ouvrir dans cet onglet', 'Download a translation': 'Télécharger une traduction',
    'No readable passage in this translation.': 'Aucun passage lisible dans cette traduction.',
    'This passage is not available in this translation.': 'Ce passage n’est pas disponible dans cette traduction.',
    'This passage is unavailable. Opened the first available passage.':
        'Ce passage n’est pas disponible. Le premier passage disponible a été ouvert.',
})

FR.update({
    'Installed translations': 'Traductions installées', 'Language': 'Langue',
    'All languages': 'Toutes les langues', 'Search translations': 'Rechercher une traduction',
    'No matching translation.': 'Aucune traduction correspondante.',
    'Source': 'Source', 'License': 'Licence', 'Conditions and attribution': 'Conditions et attribution',
    'Access key required. Encrypted translations are not supported.':
        'Clé d’accès nécessaire. Les traductions chiffrées ne sont pas prises en charge.',
    'Unsupported format.': 'Format non pris en charge.',
    'Distributed by the source. Download is checked before installation.':
        'Distribuée par la source. Le téléchargement est vérifié avant installation.',
    'No additional conditions supplied by the source.':
        'Aucune condition supplémentaire fournie par la source.',
    'Check the source conditions before downloading. Availability does not grant redistribution rights.':
        'Vérifiez les conditions de la source avant de télécharger. La disponibilité n’accorde pas de droit de redistribution.',
    'French': 'Français', 'English': 'Anglais', 'German': 'Allemand', 'Spanish': 'Espagnol',
    'Italian': 'Italien', 'Portuguese': 'Portugais', 'Greek': 'Grec', 'Hebrew': 'Hébreu',
    'Latin': 'Latin', 'Arabic': 'Arabe', 'Russian': 'Russe', 'Dutch': 'Néerlandais',
})
