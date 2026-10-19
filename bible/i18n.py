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
