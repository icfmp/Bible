"""Small French/English message catalogue shared by native views."""
import locale
import os

FR = {
    'Preparing saved resource metadata…':'Préparation des métadonnées des ressources enregistrées…',
    'Looking for available resources from the selected sources…':'Recherche des ressources disponibles auprès des sources sélectionnées…',
    'Preparing Library…':'Préparation de la Bibliothèque…',
    'Notes, labels and highlights only. Bibles and credentials are excluded. Exported annotations are not encrypted.': 'Notes, étiquettes et surlignages uniquement. Les Bibles et les identifiants sont exclus. Les annotations exportées ne sont pas chiffrées.',
    'Export a backup…': 'Exporter une sauvegarde…',
    'Restore a backup…': 'Restaurer une sauvegarde…',
    'Choose a local file.': 'Choisissez un fichier local.',
    'Backup restored. Existing annotations kept. Safety backup:': 'Sauvegarde restaurée. Annotations existantes conservées. Copie de sécurité :',
    'Unable to restore backup.': 'Impossible de restaurer la sauvegarde.',
    'Restore annotations?': 'Restaurer les annotations ?',
    'Merge notes and highlights. Existing highlights are kept on conflict; differing notes are copied. A verified safety backup is saved first.': 'Fusionner les notes et les surlignages. En cas de conflit, les surlignages existants sont conservés et les notes différentes sont copiées. Une copie de sécurité vérifiée est enregistrée avant la restauration.',
    'Backup exported.': 'Sauvegarde exportée.',
    'Unable to complete backup operation.': 'Impossible de terminer la sauvegarde.',
    'Some installed Bibles could not be read. They are preserved. Retry from Library.': 'Certaines Bibles installées sont illisibles. Elles sont conservées. Réessayez depuis la Bibliothèque.',
    'Clear filters': 'Effacer les filtres',
    'Refreshing sources…': 'Actualisation des sources…',
    'Loading catalogue…': 'Chargement du catalogue…',
    'Catalogue unavailable': 'Catalogue indisponible',
    'No Bible found': 'Aucune Bible trouvée',
    'Catalogue not loaded': 'Catalogue non chargé',
    'Retry or open installed resources. No files were removed.': 'Réessayez ou ouvrez les ressources installées. Aucun fichier n’a été supprimé.',
    'No resources match the current filters. Clear filters, choose another language or refresh.': 'Aucune ressource ne correspond aux filtres actuels. Effacez les filtres, choisissez une autre langue ou actualisez.',
    'Refresh the catalogue to discover resources.': 'Actualisez le catalogue pour découvrir les ressources.',

    'Passage studied':'Passage étudié', 'Back to first references':'Retour aux premiers renvois',
    'See all {count} references':'Voir les {count} références',
    'OpenBible target: {reference}':'Cible OpenBible : {reference}',
    'Community-ranked suggestions; explore the context.':'Suggestions classées par la communauté ; explorez le contexte.',
    'All my annotations':'Toutes mes annotations', 'No annotations for this passage.':'Aucune annotation pour ce passage.',
    'Bible excerpt unavailable.':'Extrait biblique indisponible.', 'Empty note':'Note vide',
    'Open note':'Ouvrir la note', 'Expand note':'Agrandir la note',
    'Highlight selection':'Surligner la sélection', 'Highlight and annotate…':'Surligner et annoter…',
    'Light':'Clair', 'Dark':'Sombre', 'Stop comparison':'Arrêter la comparaison',
    'Loading saved resources…':'Chargement des ressources enregistrées…',
    'Topics':'Thèmes', 'Text':'Texte', 'Passage':'Passage', 'Search':'Rechercher',
    'Search topics':'Rechercher un thème', 'Exact phrase in this translation':'Expression exacte dans cette traduction',
    'Download topic data':'Télécharger les thèmes',
    'Partial curated vocabulary: {count} topics in French and English. Suggestions are not doctrinal conclusions.':'Vocabulaire partiel relu : {count} thèmes en français et en anglais. Ces suggestions ne sont pas des conclusions doctrinales.',
    'Literal phrase, ignoring case, in the selected installed translation.':'Expression littérale, sans distinction de casse, dans la traduction installée sélectionnée.',
    'Enter a phrase and press Enter.':'Saisissez une expression et appuyez sur Entrée.',
    'Download topic data once to explore it offline.':'Téléchargez les thèmes une fois pour les explorer hors connexion.',
    'Choose a topic.':'Choisissez un thème.',
    'No topic in the supported vocabulary. Try a shorter word.':'Aucun thème dans le vocabulaire pris en charge. Essayez un mot plus court.',
    'Choose an installed translation.':'Choisissez une traduction installée.',
    'Searching…':'Recherche en cours…',
    'Showing {count} of {total} results.':'{count} résultats affichés sur {total}.',
    'No matching passages.':'Aucun passage correspondant.',
    'Search unavailable. Check the installed resource and try again.':'Recherche indisponible. Vérifiez la ressource installée et réessayez.',
    'Enter a phrase of 1–200 characters.':'Saisissez une expression de 1 à 200 caractères.',
    'Source quality score: {score}':'Score de qualité de la source : {score}',
    'Curated French/English topics':'Thèmes français/anglais relus',
    'Near this location':'À proximité de ce lieu', 'Along this geographical feature':'Le long de cet élément géographique',
    'On this geographical feature':'Sur cet élément géographique', 'Within this area':'À l’intérieur de cette zone',
    'Around this location':'Aux alentours de ce lieu',
    'Numbers identify candidates; × counts very close grouped alternatives.':'Les numéros identifient les propositions ; × compte les propositions très proches regroupées.',
    'Credits and licenses':'Crédits et licences',
    'Places in this passage':'Lieux de ce passage',
    'Biblical places and offline map':'Lieux bibliques et carte hors connexion',
    'Download place data':'Télécharger les lieux',
    'Open a Bible passage to see its places.':'Ouvrez un passage biblique pour voir ses lieux.',
    'Download place data once to use it offline.':'Téléchargez les lieux une fois pour les consulter hors connexion.',
    'Loading places…':'Chargement des lieux…',
    'Place data is unavailable. Download it again from Library.':'Les données de lieux sont indisponibles. Téléchargez-les à nouveau dans la bibliothèque.',
    '{count} recorded places.':'{count} lieux répertoriés.',
    'No places recorded for this passage.':'Aucun lieu répertorié pour ce passage.',
    'OpenBible.info · CC BY 4.0. OpenStreetMap contributors · ODbL 1.0. Natural Earth · public domain.':'OpenBible.info · CC BY 4.0. Contributeurs OpenStreetMap · ODbL 1.0. Natural Earth · domaine public.',
    'Known identification':'Identification bien établie', 'Probable identification':'Identification probable',
    'Disputed identification':'Identification discutée', 'Unknown location':'Localisation inconnue',
    'Names in the source':'Noms dans la source',
    'Loading offline map…':'Chargement de la carte hors connexion…',
    'Natural Earth · public domain. Simplified modern coastlines.':'Natural Earth · domaine public. Côtes actuelles simplifiées.',
    'Map unavailable; coordinates and references remain available.':'Carte indisponible ; les coordonnées et les références restent consultables.',
    'No identified location; no map pin is shown.':'Localisation inconnue ; aucune coordonnée dans la source.',
    'Source point':'Point indiqué dans la source',
    'Center of an approximate area':'Centre d’une zone approximative',
    'Representative point for a region or path':'Point représentatif d’une région ou d’un tracé',
    'Somewhere within the settlement':'À un endroit non précisé de cette localité',
    'Latitude, longitude: {latitude}, {longitude}':'Latitude, longitude : {latitude}, {longitude}',
    'Source uncertainty radius: {distance} km':'Rayon d’incertitude indiqué par la source : {distance} km',
    'Source path score: {score}; not a probability.':'Score d’identification de la source : {score} ; ce n’est pas une probabilité.',
    'Related Bible references':'Références bibliques associées',
    'Source evidence and bibliography':'Éléments de la source et bibliographie',
    'The dataset records this identification without a detailed bibliography.':'Les données répertorient cette identification sans bibliographie détaillée.',
    'Geographical overview. Candidate coordinates and uncertainty are listed below.':'Aperçu géographique. Les coordonnées proposées et leurs incertitudes sont indiquées plus bas.',
    'Simplified modern coastlines; not a historical or street map.':'Côtes actuelles simplifiées ; cette carte ne représente ni les rues ni le relief historique.',

    'Bible references: Tab to choose, Enter to preview.':'Références bibliques : Tab pour choisir, Entrée pour prévisualiser.',
    'No active Bible translation':'Aucune traduction biblique active',
    'Open an installed Bible translation to preview this reference.':'Ouvrez une traduction biblique installée pour prévisualiser cette référence.',
    'References':'Références', 'Study resources':'Ressources d’étude', 'Bible cross-references':'Renvois bibliques',
    'Update':'Mettre à jour', 'Cross-references':'Références croisées', 'View all':'Tout voir',
    'Passage preview':'Aperçu du passage', 'Local passage text':'Texte local du passage',
    'Open in current tab':'Ouvrir dans cet onglet', 'Open in new tab':'Ouvrir dans un nouvel onglet',
    'Beginning of passage; open it to read more.':'Début du passage ; ouvrez-le pour lire la suite.',
    'Text from your installed translation.':'Texte de votre traduction installée.',
    'This passage is unavailable in the selected translation.':'Ce passage est indisponible dans la traduction sélectionnée.',
    'Translation unavailable.':'Traduction indisponible.',
    'Download reference data':'Télécharger les renvois',
    'Open a Bible passage to see its references.':'Ouvrez un passage biblique pour voir ses renvois.',
    'Download OpenBible reference data once to use it offline.':'Téléchargez les renvois OpenBible une fois pour les utiliser hors connexion.',
    'Loading references…':'Chargement des renvois…',
    'Reference data is unavailable. Download it again from Library.':'Les données de renvois sont indisponibles. Téléchargez-les à nouveau dans la bibliothèque.',
    'No cross-references for this passage.':'Aucun renvoi pour ce passage.',
    'Community score: {score}':'Pertinence communautaire : {score}',
    'Related to {count} selected verses.':'Associé à {count} versets sélectionnés.',
    'OpenBible.info · CC BY 4.0. Community suggestions; explore the context.':'OpenBible.info · CC BY 4.0. Suggestions communautaires ; consultez le contexte.',
    'Passage study': 'Étude du passage', 'Notes': 'Notes', 'Commentaries': 'Commentaires',
    'Add note': 'Ajouter une note', 'Edit note': 'Modifier la note',
    'Notes on': 'Notes sur', 'No notes for this passage.': 'Aucune note pour ce passage.',
    'No highlights for this passage.': 'Aucun surlignage pour ce passage.',
    'Add highlight': 'Ajouter un surlignage', 'Show more notes': 'Afficher plus de notes',
    'Resize study panel': 'Redimensionner le panneau d’étude',
    'Resize study panel: drag or use Left/Right arrow keys': 'Redimensionner le panneau d’étude : faites glisser ou utilisez les flèches gauche/droite',
    'Unable to save study preferences.': 'Impossible d’enregistrer les préférences d’étude.',
    'Automatic following unavailable. Reading independently.': 'Suivi automatique indisponible. Lecture indépendante.',
    'Independent reading': 'Lecture indépendante',
    'Preparing reading pages…': 'Préparation des pages de lecture…',
    'Highlight actions': 'Actions de surlignage',
    'Highlights unavailable. The original file is preserved.': 'Surlignages indisponibles. Le fichier d’origine est conservé.',
    'Highlights': 'Surlignages', 'Highlight': 'Surligner', 'Remove highlight': 'Retirer le surlignage',
    'Show highlights': 'Afficher les surlignages', 'Yellow': 'Jaune', 'Green': 'Vert', 'Blue': 'Bleu',
    'Back up highlights': 'Sauvegarder les surlignages', 'Restore highlights': 'Restaurer les surlignages',
    'Search highlighted passages': 'Chercher les passages surlignés', 'No highlights yet.': 'Aucun surlignage pour le moment.',
    'Restore highlights?': 'Restaurer les surlignages ?',
    'Merge the backup with existing highlights. Notes and translations are unchanged.': 'Fusionner la sauvegarde avec les surlignages existants. Les notes et traductions sont conservées.',
    'No installed translation can open this highlight. The highlight is retained.': 'Aucune traduction installée ne permet d’ouvrir ce surlignage. Il est conservé.',
    'Passage actions': 'Actions du passage',
    'Copy selected text': 'Copier le texte sélectionné',
    'Copy options': 'Options de copie',
    'Dismiss passage actions': 'Fermer les actions du passage',
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
# Read only the real application's saved language before constructing any UI.
# An explicit Library resource-language choice remains independent.
def _application_language(system):
    import json
    from pathlib import Path
    path=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'bible/application-preferences.json'
    try:
        with path.open('rb') as stream:data=stream.read(8193)
        if len(data)>8192:return system
        value=json.loads(data)
        selected=value.get('ui_language') if value.get('version')==1 else None
        return selected if selected in ('fr','en') else system
    except (OSError,ValueError,TypeError,AttributeError):return system
LANGUAGE = _application_language(LANGUAGE)


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
    'Size unknown': 'Taille inconnue', 'Failed': 'Échec', 'Retry': 'Réessayer',
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
    'Reset reading settings':'Rétablir l’apparence de lecture',
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

FR.update({
    'Main menu':'Menu principal', 'Preferences':'Paramètres', 'Keyboard Shortcuts':'Raccourcis clavier',
    'About Bible':'À propos de Bible', 'Reading and application':'Lecture et application',
    'Preferred resource language':'Langue des ressources par défaut',
    'Choose which resources appear first. Reading appearance remains in Aa.':'Choisissez les ressources à afficher en premier. L’apparence de lecture reste dans Aa.',
    'Refresh catalogues automatically':'Actualiser les catalogues automatiquement',
    'Check metadata when Library opens. Resource texts download only on request.':'Vérifier les catalogues à l’ouverture de la bibliothèque. Les textes sont téléchargés uniquement sur demande.',
    'Unable to save application preferences.':'Impossible d’enregistrer les paramètres de l’application.',
    'Read and study the Bible. Downloaded resources keep their own licenses.':'Lire et étudier la Bible. Les ressources téléchargées conservent leurs propres licences.',
    'Third-party notices':'Mentions des composants tiers',
    'Welcome to Bible':'Bienvenue dans Bible',
    'Choose a Bible to start reading and studying.':'Choisissez une Bible pour commencer à lire et à étudier.',
    'Your downloaded texts stay available offline.':'Vos textes téléchargés restent disponibles hors connexion.',
    'Choose my Bible':'Choisir ma Bible', 'Later':'Plus tard', 'Download a Bible':'Télécharger une Bible',
    'Download more…':'Télécharger davantage…', 'Read':'Lire', 'Open':'Ouvrir',
    'Search Bibles':'Rechercher une Bible', 'Search commentaries':'Rechercher un commentaire',
    'Downloading…':'Téléchargement…', 'Cancel download':'Annuler le téléchargement',
    'Download cancelled.':'Téléchargement annulé.',
    'No resources in {language}. Choose another language or refresh the selected source.':'Aucune ressource en {language}. Choisissez une autre langue ou actualisez la source sélectionnée.',
    'This reading tab is no longer available. Open Library again from the intended tab.':'Cet onglet de lecture n’est plus disponible. Rouvrez la bibliothèque depuis l’onglet souhaité.',
})
FR.update({'Choose or download a Bible. Downloaded texts are available offline.':'Choisissez ou téléchargez une Bible. Les textes téléchargés restent disponibles hors connexion.'})
FR.update({'Unable to load application preferences. Original file preserved.':'Impossible de charger les paramètres de l’application. Le fichier original est conservé.'})
FR.update({'All highlights':'Tous les surlignages'})
FR.update({'Installing {name} and checking…':'Installation et vérification de {name}…'})

FR.update({
    'General':'Général', 'Application language':'Langue de l’application',
    'French':'Français', 'English':'Anglais', 'Interface appearance':'Apparence de l’interface',
    'Restore tabs at startup':'Restaurer les onglets au démarrage',
    'Restart Bible to apply the application language.':'Redémarrez Bible pour appliquer la langue de l’application.',
    'Aa keeps its explicit reading palette; System follows this appearance.':'Aa conserve sa palette de lecture explicite ; Système suit cette apparence.',
    'Applies at next launch. Your annotations and downloaded resources are kept.':'S’applique au prochain démarrage. Vos annotations et ressources téléchargées sont conservées.',
    'Reading appearance stays in Aa. Existing note backups remain available in My notes.':'L’apparence de lecture reste dans Aa. Les sauvegardes de notes existantes restent disponibles dans Mes notes.',
})
FR.update({
    'Notes and highlights':'Notes et surlignages', 'Application space':'Espace de l’application',
    'Notes':'Notes', 'All':'Tout', 'Filters':'Filtres', 'Annotation actions':'Actions sur les annotations',
    'Each note and each saved verse highlight counts once. Related records stay separate.':'Chaque note et chaque verset surligné compte une fois. Les éléments associés restent distincts.',
    'All books':'Tous les livres', 'Book':'Livre', 'All colors':'Toutes les couleurs',
    'Highlight color':'Couleur du surlignage', 'Search annotations':'Rechercher des annotations',
    'Sort annotations':'Trier les annotations', 'Back to annotations':'Retour aux annotations',
    'Open in Bible':'Ouvrir dans la Bible', 'Excerpt translation':'Traduction de l’extrait',
    'Choose an annotation':'Choisissez une annotation', 'Your annotations remain available offline.':'Vos annotations restent disponibles hors connexion.',
    'Original source':'Source d’origine', 'No matching annotations.':'Aucune annotation correspondante.',
    'No annotations yet.':'Aucune annotation pour le moment.', 'No installed Bible':'Aucune Bible installée',
    'Install a Bible to display this passage. Your annotation is kept.':'Installez une Bible pour afficher ce passage. Votre annotation est conservée.',
    'Displayed in':'Extrait affiché dans', 'Excerpt':'Extrait',
    'Passage unavailable or no verified alignment.':'Passage indisponible ou correspondance non vérifiée.',
    'Related annotations':'Annotations associées', 'More related records are available in the list.':'D’autres éléments associés sont disponibles dans la liste.',
    'Remove this highlight?':'Supprimer ce surlignage ?', 'The related notes are kept.':'Les notes associées sont conservées.',
    'This highlight changed elsewhere. Reopen it before editing.':'Ce surlignage a été modifié ailleurs. Rouvrez-le avant de le modifier.',
    'Saving…':'Enregistrement…', 'Press Enter to add the label before saving.':'Appuyez sur Entrée pour ajouter le label avant d’enregistrer.',
})
FR.update({'Highlight annotation':'Surlignage'})
FR.update({'Date sorting uses note modification dates. Highlights without dates follow in Bible order.':'Le tri par date utilise la modification des notes. Les surlignages sans date suivent dans l’ordre biblique.'})
FR.update({'Unable to save this note. Your draft is kept.':'Impossible d’enregistrer cette note. Votre brouillon est conservé.'})

FR.update({'Resume following':'Reprendre le suivi', 'No annotations in this chapter.':'Aucune annotation dans ce chapitre.'})

FR.update({'A note passage must be ordered within one book':'Le passage d’une note doit être ordonné dans un même livre.'})
