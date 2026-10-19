# Commentaires CrossWire — issue #6

## Essayer

Mettre à jour le dépôt puis lancer `LANGUAGE=fr /usr/bin/python3 -m bible` avec
le Python système et les dépendances du README. Dans **Bibliothèque** (Ctrl+L),
charger le catalogue et choisir le type **Commentaires**. Langue, recherche,
titre, auteur lorsqu’il est fourni, source, licence, conditions et numérotation
des versets sont visibles avant téléchargement.

Pour un premier essai, installer **KJV** dans Bibles, puis **Clarke** et **MHCC**
(Matthew Henry Concise) dans Commentaires. Ces deux commentaires sont annoncés
par CrossWire en anglais, dans le domaine public, avec la numérotation KJV.
Ouvrir Jean 3:16 depuis le titre central, afficher l’étude avec F9 et choisir le
commentaire dans son sélecteur. Cliquer sur le texte d’un autre verset ou utiliser
Alt+Haut/Bas pour choisir le verset précédent/suivant du chapitre. Son numéro
devient gras et le titre central suit la sélection. Le défilement seul ne change
pas le verset choisi. La sélection de texte pour copie reste possible.

Le panneau montre le vrai texte SWORD local, son titre/source et **Source et
conditions**, consultable hors connexion. Une entrée manquante ou vide affiche
« Aucun commentaire pour ce passage » et efface l’ancien contenu. Un changement
d’onglet, une erreur ou une ressource manquante ne conserve jamais une ancienne
entrée sous une nouvelle référence. Les entrées liées par SWORD sont respectées :
un même commentaire peut réellement couvrir plusieurs versets.

Chaque onglet garde son choix de commentaire et l’état du panneau. Le redémarrage
les restaure. Le nom d’un commentaire désinstallé est conservé dans la session,
avec un message explicite ; aucun fichier utilisateur n’est supprimé. Les anciens
fichiers de session version 1 restent lisibles : le nouveau champ optionnel
`commentary` vaut alors null. La lecture seule ne réécrit pas le fichier ; les
sauvegardes gardent le remplacement atomique existant. Aucun changement de base
de notes ni migration destructive n’est introduit.

F9 cache le panneau et rend la largeur au lecteur. Sur fenêtre large, la Bible
reste à gauche et l’étude à droite. À 360 pixels, l’étude se superpose au lecteur ;
un seul commentaire est affiché à la fois, avec un sélecteur pour les autres.

## Prise en charge et limites

Le catalogue distingue les pilotes de Bibles et de commentaires. Les commentaires
pris en charge utilisent les pilotes SWORD `RawCom`, `RawCom4`, `zCom` et `zCom4`.
Les types non pris en charge classés comme commentaires par la source restent
signalés avec téléchargement désactivé. Une configuration comportant `CipherKey`,
même vide, est également bloquée ; aucun système de clés ou déchiffrement n’est
ajouté. Le téléchargement reste sur demande, avec progression et nouvelle
tentative, et reprend les bornes de taille, contrôles de chemins, CRC ZIP,
identité et installation atomique du catalogue existant. Les changements de type,
numérotation, auteur ou conditions entre catalogue et paquet sont refusés.
La première entrée réellement indexée et lisible est validée avant installation.

Un commentaire n’est jamais proposé comme traduction dans la navigation de la
Bible. Installer uniquement un commentaire ne crée pas une fausse Bible.
L’installation d’un commentaire sélectionne ce dernier dans l’onglet actif et
ouvre le panneau d’étude, sans remplacer le texte biblique.

La correspondance exige la **même versification déclarée** dans les deux
ressources. Si elles diffèrent, le panneau affiche les deux systèmes et une
limite explicite. Il n’effectue pas de correspondance automatique, même si
certains versets portent le même numéro. Par exemple, choisir un commentaire
KJV avec une Bible Calvin ne constitue pas un alignement validé. Les systèmes
inconnus de la version SWORD installée restent refusés.

Le catalogue officiel comporte aussi des commentaires français, notamment
FreAug, FreChry, FreJer (Catholic) et FreCJE (DarbyFr). Leur présence dans le
catalogue a été vérifiée, mais ne constitue pas un test de leur lecture ni de
leur correspondance avec n’importe quelle Bible française. Consulter la
numérotation indiquée sur les fiches avant de choisir la Bible et le commentaire.

Les vérifications utilisent `hasEntry` sur la clé exacte avant `stripText`.
L’absence d’entrée ne doit pas déclencher le comportement SWORD de recherche
d’une entrée voisine. Les introductions indexées uniquement au livre/chapitre,
sans verset, n’ont pas de vue dédiée dans cette tranche.

Le texte passe dans un Gtk.TextView sans rendu HTML ni actions provenant du
contenu téléchargé. Les références sont du texte ; elles ne déclenchent aucune
commande. Les métadonnées HTML/RTF sont présentées en texte simple. L’UTF-8,
le grec et l’hébreu sont conservés ; la validation linguistique et typographique
complète sur un bureau réel reste à faire. Pas de comparaison dédiée de deux
commentaires, dictionnaires, Strong, morphologie, notes ou IA dans ce jalon.

## Vérifications

Les tests créent de petits modules RawCom réels avec des sentinelles clairement
identifiées comme données de test, sans faux commentaire livré à l’utilisateur.
Ils couvrent les entrées absentes/vides/liées, la versification, les attributions
hors connexion, le type de ressource, l’installation sûre, les anciennes sessions,
la sélection par clic/clavier, les onglets, la restauration, la disparition d’une
ressource et l’interface à 360 pixels. Un clic X11 injecté sous Xvfb a également
vérifié le trajet des événements natifs ; cela reste un affichage virtuel.

La suite compte 48 tests. Les tests GTK sont exécutés en anglais et français.
`python3 -m tools.check_commentary` télécharge réellement Clarke et MHCC dans un
dossier temporaire, compare le texte au retour direct SWORD et vérifie la lecture
et l’attribution dans un processus séparé. En CI, ce processus utilise un espace
réseau isolé. Le test cherche aussi une entrée réellement absente dans chaque
source, lorsqu’il en existe une. Les résultats effectifs sont visibles dans
GitHub Actions ; le proxy local interdit ces téléchargements. La CI conserve les
tests de traductions et construit le Flatpak GNOME 49. Aucun ouvrage complet
n’est ajouté à Git ou au paquet de l’application.

Sources consultées : [configurations SWORD](https://wiki.crosswire.org/DevTools:conf_Files),
[catalogue CrossWire](https://www.crosswire.org/ftpmirror/pub/sword/raw/mods.d.tar.gz),
[exécution d’examen des commentaires](https://github.com/icfmp/Bible/actions/runs/39223437480).
Les méthodes utilisées ont été éprouvées avec les bindings réels SWORD 1.9.

Sur un poste GNOME, il reste à essayer le téléchargement, la lecture et le choix
de verset à la souris/clavier, les différents thèmes, le panneau étroit et la
réouverture après coupure du réseau. Les tests sous Xvfb ne valident pas le bureau
du client ; aucun essai Windows/macOS ni publication Flathub n’est annoncé.
