"""Small French/English message catalogue shared by native views."""
import locale
import os

FR = {
    'Hide study': 'Masquer l’étude',
    'Commentary actions': 'Actions du commentaire',
    'Very airy': 'Très aéré',
    'Saved catalogue — available offline.': 'Catalogue enregistré — disponible hors connexion.',
    'Saved results retained.': 'Les résultats enregistrés sont conservés.',
    'Installed — available offline': 'Installé — disponible hors connexion',
    'Refreshing sources… Cached resources remain available.': 'Actualisation des sources… Les ressources en cache restent disponibles.',
    'Scroll either pane to follow the passage.': 'Faites défiler un panneau pour suivre le passage.',
    'No verified alignment for this passage.': 'Aucun alignement vérifié pour ce passage.',
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

FR.update({
    'Reading appearance':'Apparence de lecture','Reading font':'Police de lecture',
    'Text size':'Taille du texte','Chapter numbers':'Numéros de chapitres','Verse numbers':'Numéros de versets',
    'Compare translations':'Comparer les traductions','No comparison':'Aucune comparaison',
    'Comparison translation unavailable.':'La traduction de comparaison est indisponible.',
    'History':'Historique','History back':'Historique : retour','History forward':'Historique : avancer',
    'Books':'Livres','No passage history yet.':'Aucun passage dans l’historique.',
    'History resource unavailable. The passage has been kept.':'Cette traduction est indisponible. Le passage reste dans l’historique.',
    'Add a passage note':'Ajouter une note de passage',
    'Explore':'Explorer','Installed':'Installée','Refresh catalogue':'Actualiser le catalogue',
    'Search languages':'Rechercher une langue','Back':'Retour',
    'Note created with':'Note créée avec','Note actions':'Actions de la note','Delete note…':'Supprimer la note…',
    'Write / Preview':'Écrire / Aperçu','Unsaved changes':'Modifications non enregistrées',
    'Save this note before leaving?':'Enregistrer cette note avant de quitter l’édition ?',
    'Keep editing':'Continuer l’édition','Discard':'Abandonner',
    'Filter by label':'Filtrer par label','Search labels':'Rechercher un label','Remove filter':'Retirer le filtre',
    'Today':'Aujourd’hui','Yesterday':'Hier','Reading':'Lecture','Back to notes':'Retour aux notes',
    'Choose a note':'Choisissez une note','Your notes remain available offline.':'Vos notes restent disponibles hors connexion.',
    'No notes yet.':'Aucune note pour le moment.','Open passage':'Ouvrir le passage',
})

FR.update({
    'Book':'Livre','Simple':'Simple','Decrease text size':'Réduire la taille du texte',
    'Increase text size':'Augmenter la taille du texte','Reading mode':'Mode',
    'System':'Système','Day':'Jour','Night':'Nuit','Day palettes':'Couleurs de jour',
    'Night palettes':'Couleurs de nuit','White':'Blanc','Paper (sepia)':'Papier (sépia)',
    'Dark grey':'Gris sombre','Black':'Noir','Layout':'Mise en page',
    'Line spacing':'Interligne','Tight':'Serré','Normal':'Normal','Airy':'Aéré',
    'Text width':'Largeur du texte','Narrow':'Étroite','Wide':'Large',
    'Reset reading settings':'Rétablir les réglages',
    'Colors follow the system high contrast setting.':'Les couleurs suivent le contraste élevé du système.',
})

FR.update({
    'Introduction':'Introduction','Introduction has no verified verse alignment.':'Cette introduction n’a pas de correspondance vérifiée avec un verset.',
    'Previous available entry':'Entrée disponible précédente','Next available entry':'Entrée disponible suivante',
    'Immersive mode':'Mode immersif','Leave immersive mode':'Quitter le mode immersif',
    'Read in immersive mode':'Lire en mode immersif','Reading page':'Page de lecture',
    'Previous pages':'Pages précédentes','Next pages':'Pages suivantes',
    'Open this passage in the Bible':'Ouvrir ce passage dans la Bible',
    'Commentary resumed. The Bible passage is unchanged.':'Lecture du commentaire reprise. Le passage biblique est inchangé.',
    'In GNOME, turn on Do Not Disturb in the clock menu. Bible does not change notifications.':
        'Dans GNOME, activez Ne pas déranger dans le menu de l’horloge. Bible ne modifie pas les notifications.',
    'Do not show again':'Ne plus afficher',
})

FR.update({
    'Copy verses without numbers':'Copier les versets sans numéros',
    'Copy verses with reference':'Copier les versets avec la référence',
    'Copy reference':'Copier la référence',
})
