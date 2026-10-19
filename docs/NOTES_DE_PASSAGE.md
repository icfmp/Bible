# Notes de passage — issue #7

## Créer, retrouver et modifier

Lancer l’application comme indiqué dans le README. Avec une Bible installée,
choisir un verset puis **Note de passage** dans le menu de la Header Bar, ou
Ctrl+N. Une sélection de texte couvrant plusieurs versets du chapitre crée une
note sur cet intervalle. Sans sélection, la note concerne le verset actif.
Les notes portent sur un chapitre à la fois dans cette tranche.

L’éditeur propose Gras, Italique, Liste et Lien, ainsi que les vues **Écrire** et
**Aperçu**. C’est un Markdown léger : gras, italique, listes simples et liens
présentés en texte. HTML et scripts restent du texte littéral ; images et liens
ne sont ni chargés ni ouverts. Les liens sont volontairement inertes, y compris
les URL de commande. Aucun navigateur embarqué ni service en ligne n’intervient.
L’aperçu est rendu par des Gtk.TextView et des styles natifs.

Ajouter un label dans le champ, avec autocomplétion des labels déjà utilisés,
puis Entrée ou +. Plusieurs labels sont possibles ; × retire une association.
**Enregistrer** conserve la note et ferme l’éditeur. Une note vide est refusée.
Fermer un brouillon modifié demande de confirmer son abandon ; la fermeture de
l’application protège aussi le brouillon ouvert. La suppression d’une note
existante demande une confirmation distincte.

Les numéros des versets annotés sont discrètement soulignés, sans ajouter de
caractères au texte biblique. Cliquer sur un numéro souligné ou sur **Notes du
passage** ouvre la note. S’il y en a plusieurs, une liste limitée au passage
permet de choisir. La commande de note ouvre une note existante si elle est seule ;
le bouton de nouvelle note de **Mes notes** permet d’en créer une supplémentaire.

Ouvrir **Mes notes** dans le menu ou avec Ctrl+Maj+N : la liste présente toutes
les notes, leur référence, versification, aperçu, labels et dates. Rechercher
un mot du contenu ou une référence (par exemple « Jean 3:16 »), choisir un tri
par modification récente/ancienne ou ordre biblique, et ajouter un ou plusieurs
labels de filtre. Les filtres de labels se combinent entre eux et avec la
recherche. Retirer un filtre n’altère pas le label des notes. Activer une ligne
ouvre le passage compatible et son éditeur. Le bouton Retour à la lecture ferme
cette vue sans fermer l’application.

Le panneau des commentaires garde son fonctionnement indépendant et F9. Les
fenêtres de notes et leurs labels s’adaptent à 360 pixels. Le français et
l’anglais sont disponibles selon la langue de l’application.

## Passage, traduction et versification

Une note stocke deux références OSIS (début/fin), la versification déclarée,
le corps Markdown, les labels et les dates. La traduction et la langue de
création sont un **contexte d’origine**, affiché dans l’éditeur et conservé lors
d’une modification. Elles ne constituent pas la clé d’association.

Une autre traduction utilisant exactement la même versification SWORD retrouve
la note sur les mêmes versets présents. Une versification différente n’est
jamais assimilée par numéro de verset. Aucun convertisseur de versification
n’est ajouté. Dans la liste, chaque référence montre son système de numérotation.

À l’ouverture depuis Mes notes, l’application privilégie la traduction courante
si elle est compatible, puis celle d’origine, puis une autre installée qui
utilise la même versification et possède les bornes du passage. Si aucune ne
convient, l’éditeur conserve l’accès au texte et aux labels avec une explication ;
aucun mauvais passage n’est ouvert, aucun téléchargement ne se déclenche.
La suppression de la traduction d’origine ne supprime donc aucune note.

L’ordre biblique utilise un ordre de présentation commun des livres, avec les
livres deutérocanoniques et autres livres connus intercalés avant le Nouveau
Testament ; ce tri n’établit aucune correspondance entre canons. Les codes
inconnus sont classés ensuite. Les dates sont conservées avec fuseau horaire.

## Stockage et sauvegarde

Les notes sont dans `${XDG_DATA_HOME:-~/.local/share}/bible/notes.sqlite3`, à côté
de la session et **en dehors** des traductions téléchargées. Flatpak utilise le
répertoire de données de l’application, distinct du profil natif. La réinstallation
de l’application conserve les notes si ces données utilisateur sont conservées.
Supprimer ces données les supprime ; sauvegarder avant une suppression du profil.

Le schéma SQLite est identifié par `application_id` et `user_version=1`. La seule
migration initiale est 0 → 1 sur une base réellement vide, dans une transaction
explicite. Une base inconnue, future ou illisible n’est pas remplacée : les
commandes de notes sont désactivées avec un message et la lecture continue.
Les écritures et suppressions sont transactionnelles. Une révision par note
refuse les écritures fondées sur une ancienne version, en gardant le brouillon,
plutôt que d’écraser les changements d’un autre éditeur.

Dans **Mes notes**, ouvrir le menu → **Sauvegarder les notes** et choisir un
fichier JSON. Le sélecteur de fichiers natif est utilisé, sans autorisation
permanente d’accès au disque ajoutée au Flatpak. L’écriture utilise un fichier
temporaire puis un remplacement atomique. La base de notes elle-même ne peut
pas être choisie comme destination de sauvegarde. Les nouveaux fichiers de
base et de sauvegarde ont des permissions privées sous Linux. Le JSON contient
les notes en clair ; il n’est pas chiffré.

**Restaurer les notes** vérifie d’abord le format `bible-notes`, sa version, les
références, identifiants, dates, corps et labels de **tout** le fichier. Le
fichier est limité à 32 Mio, une note à 200 000 caractères, les labels à 32 par
note et 80 caractères chacun. Une erreur ne restaure pas un sous-ensemble.

La restauration fusionne dans une transaction, sans remplacer les notes
existantes. Les copies déjà présentes sont ignorées. Si un même identifiant a
un contenu différent, la version sauvegardée devient une nouvelle note et la
version locale reste intacte. Le résultat indique les ajouts, les éléments déjà
présents et les copies conservées. Restaurer le même fichier une seconde fois
ne multiplie pas ces copies. Les attributions et contextes de création restent
conservés. Cette sauvegarde contient uniquement notes et labels, pas les Bibles,
commentaires, sessions ou clés de fournisseurs.

## Vérifications

La suite compte 66 tests, dont les contrôles de notes sur SQLite réel et des
tests GTK sous Xvfb. Ils vérifient : persistance après réouverture, labels et
recherche combinée, plages de versets, ordre/date, compatibilité de versification,
changement de traduction/langue, disparition de la traduction d’origine,
base future préservée, conflit de révision, rollback d’une écriture échouée,
fusion/restauration invalide sans perte, export échoué, Markdown inerte,
commandes de mise en forme, confirmations de suppression/abandon, accès depuis
un résultat et fenêtres à 360 pixels. Les tests utilisent des modules SWORD avec
sentinelles identifiées comme fixtures, sans corpus biblique ajouté au dépôt.

Les tests d’interface sont répétés en français dans la CI. Celle-ci garde les
vrais téléchargements CrossWire et la construction Flatpak GNOME 49. Les captures
inspectées proviennent de GTK sous Xvfb ; elles ne valident pas le poste du client.
Le parcours du sélecteur de fichiers et ses autorisations de portail Flatpak,
le clavier/lecteur d’écran complet et l’essai sur le bureau GNOME restent à
vérifier manuellement. Aucun essai Windows/macOS n’est revendiqué.

Pas d’IA, synchronisation ou surlignage dans cette livraison. Les sauvegardes
et restaurations de notes sont réalisées ici ; ce volet n’est pas reporté à une
issue ultérieure. Les plages traversant plusieurs chapitres et le Markdown
complet restent hors de cette première tranche.
