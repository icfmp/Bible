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

FR.update({
    'Library': 'Bibliothèque', 'Resources': 'Ressources', 'Resource type': 'Type de ressource',
    'Bibles': 'Bibles', 'Commentaries': 'Commentaires', 'Author': 'Auteur',
    'Installed resources': 'Ressources installées', 'Search resources': 'Rechercher une ressource',
    'No matching resource.': 'Aucune ressource correspondante.', 'Source: CrossWire': 'Source : CrossWire',
    'Choose a commentary': 'Choisir un commentaire', 'Missing commentary': 'Commentaire absent',
    'Source and conditions': 'Source et conditions', 'Commentary text': 'Texte du commentaire',
    'Click a verse in the Bible to follow it here.': 'Cliquez sur un verset dans la Bible pour le suivre ici.',
    'Download a commentary': 'Télécharger un commentaire',
    'Choose or download a commentary.': 'Choisissez ou téléchargez un commentaire.',
    'This commentary is no longer installed. Choose another or download it again.':
        'Ce commentaire n’est plus installé. Choisissez-en un autre ou téléchargez-le à nouveau.',
    'Open a Bible passage to read its commentary.': 'Ouvrez un passage biblique pour lire son commentaire.',
    'No commentary for this passage.': 'Aucun commentaire pour ce passage.',
    'Different versifications. Automatic alignment is unavailable.':
        'Versifications différentes. L’alignement automatique n’est pas disponible.',
    'Unable to read this commentary.': 'Impossible de lire ce commentaire.',
    'Click a verse to select it. Alt+Up/Down selects the previous/next verse.':
        'Cliquez sur un verset pour le sélectionner. Alt+Haut/Bas sélectionne le verset précédent/suivant.',
    'Access key required. Encrypted resources are not supported.':
        'Clé d’accès nécessaire. Les ressources chiffrées ne sont pas prises en charge.',
})

FR['Verse numbering'] = 'Numérotation des versets'

FR.update({
    'My notes': 'Mes notes', 'Passage note': 'Note de passage', 'Notes and commands': 'Notes et commandes',
    'New passage note': 'Nouvelle note de passage', 'Save': 'Enregistrer', 'Cancel': 'Annuler', 'Confirm': 'Confirmer',
    'Original context': 'Contexte d’origine', 'Bold': 'Gras', 'Italic': 'Italique', 'List': 'Liste', 'Link': 'Lien',
    'Note in Markdown': 'Note en Markdown', 'Safe preview': 'Aperçu sûr', 'Write': 'Écrire', 'Preview': 'Aperçu',
    'Labels': 'Labels', 'Add a label': 'Ajouter un label', 'Remove label': 'Retirer le label',
    'Links are displayed as text and never opened automatically.':
        'Les liens sont affichés en texte, sans ouverture automatique.',
    'Delete note': 'Supprimer la note', 'Note saved.': 'Note enregistrée.',
    'Delete this note permanently?': 'Supprimer définitivement cette note ?',
    'This removes the note and its labels from this passage.': 'La note et ses associations de labels seront supprimées de ce passage.',
    'Discard unsaved changes?': 'Abandonner les modifications non enregistrées ?',
    'Your note has not been saved.': 'Votre note n’a pas été enregistrée.',
    'Search notes or references': 'Rechercher dans les notes ou les références',
    'Most recent': 'Les plus récentes', 'Oldest first': 'Les plus anciennes', 'Bible order': 'Ordre biblique',
    'Sort notes': 'Trier les notes', 'All passages': 'Tous les passages', 'No matching note.': 'Aucune note correspondante.',
    'Created': 'Création', 'Modified': 'Modification', 'notes': 'notes',
    'Backup and restore': 'Sauvegarde et restauration', 'Back up notes': 'Sauvegarder les notes',
    'Restore notes': 'Restaurer les notes', 'Notes backup (JSON)': 'Sauvegarde des notes (JSON)',
    'Choose a local file.': 'Choisissez un fichier local.', 'Notes backup saved.': 'Sauvegarde des notes enregistrée.',
    'Restore complete. Added / already present / copies kept':
        'Restauration terminée. Ajoutées / déjà présentes / copies conservées',
    'Passage notes': 'Notes du passage', 'Underlined verse numbers have notes.':
        'Les numéros de versets soulignés ont des notes.',
    'Notes unavailable. The original file has been preserved.':
        'Notes indisponibles. Le fichier d’origine a été conservé.',
    'Open a Bible passage before creating a note.': 'Ouvrez un passage biblique avant de créer une note.',
    'No compatible translation installed. The note remains available.':
        'Aucune traduction compatible installée. La note reste consultable.',
    'Invalid label': 'Label invalide (80 caractères au maximum).',
    'Invalid labels': 'Labels invalides (32 au maximum).',
    'A note must contain text (maximum 200000 characters)':
        'Une note doit contenir du texte (200 000 caractères au maximum).',
    'This note changed elsewhere. Your draft has been preserved.':
        'Cette note a changé ailleurs. Votre brouillon a été conservé.',
    'Choose a backup file different from the notes database':
        'Choisissez un fichier de sauvegarde distinct de la base des notes.',
    'Notes backup exceeds the 32 MiB limit': 'La sauvegarde dépasse la limite de 32 Mio.',
})

FR.update({'Back to reading': 'Retour à la lecture', 'note': 'note',
           'Save or close the current note before opening another.':
               'Enregistrez ou fermez la note actuelle avant d’en ouvrir une autre.'})

FR.update({
    'Downloading {name}…': 'Téléchargement de {name}…',
    'Installing and checking…': 'Installation et vérification…',
    'Installed: {name}': 'Installé : {name}',
    'Size unknown': 'Taille inconnue', 'Failed': 'Échec',
})

FR.update({
    'Search books': 'Rechercher un livre', 'No matching book.': 'Aucun livre correspondant.',
    'Old Testament': 'Ancien Testament', 'New Testament': 'Nouveau Testament',
    'Chapters': 'Chapitres', 'Close': 'Fermer',
})

FR['Choose a chapter in this translation to start reading.'] = (
    'Choisissez un chapitre dans cette traduction pour commencer la lecture.')

FR.update({
    'All sources': 'Toutes les sources',
    'Partial catalogue. Retry to reload unavailable sources.':
        'Catalogue partiel. Rechargez pour réessayer les sources indisponibles.',
})
