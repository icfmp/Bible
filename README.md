# Bible

<img src="packaging/icons/bible-source.png" alt="Icône de Bible : livre bleu avec signet ocre" width="128" height="128">


Prototype natif GNOME de lecture biblique, sans traduction préembarquée.
Le jalon #2 comprend un catalogue CrossWire réel, un téléchargement sur demande,
la lecture locale via SWORD et la navigation entre chapitres. Le jalon #3 ajoute
les onglets indépendants, leur restauration et un panneau d’étude escamotable.
L’issue #5 centralise la navigation dans le titre cliquable de la Header Bar.

## Essai alpha en Flatpak (sans installer les dépendances de développement)

Depuis [la dernière exécution réussie de GitHub Actions](https://github.com/icfmp/Bible/actions),
télécharger l'artefact **Bible-alpha-linux-x86_64**, puis extraire
`Bible-alpha.flatpak` de l'archive ZIP. Sur un ordinateur Linux x86_64
avec Flatpak installé, ouvrir ce fichier avec le gestionnaire de logiciels,
ou exécuter dans son dossier :

```sh
flatpak install --user ./Bible-alpha.flatpak
flatpak run io.github.icfmp.Bible
```

Flatpak propose le runtime GNOME nécessaire si celui-ci n'est pas encore installé
et que Flathub est configuré. Ce fichier de test expire après 30 jours ; récupérer
le paquet du dernier run réussi pour la version la plus récente. La mise à jour
n'est pas automatique : installer de nouveau le paquet après chaque livraison.
Les traductions, commentaires et notes ne sont pas inclus dans le paquet et
restent dans le profil Flatpak de l'utilisateur. Le profil natif décrit ci-dessous
est distinct. Cette version n'est pas publiée sur Flathub et son fonctionnement
graphique doit encore être essayé sur un vrai bureau GNOME.

## Essayer sous Debian 13 ou Ubuntu 24.04

```sh
sudo apt update
sudo apt install python3 python3-gi python3-sword gir1.2-gtk-4.0 gir1.2-adw-1
cd Bible
/usr/bin/python3 -m bible
```

Utiliser le Python système, qui voit les bindings de la distribution. Depuis la
fenêtre, ouvrir **Bibliothèque** dans la Header Bar (`Ctrl+L`), choisir
**Charger le catalogue**, choisir **Bibles** et une **Langue**, rechercher un titre,
lire sa licence et ses conditions, puis cliquer sur **Télécharger**. Après installation, le premier chapitre apparaît. Les flèches
changent de chapitre. Cliquer sur le titre central (`Ctrl+G`) puis choisir
**Version → Livre → Chapitre → Verset**, par exemple **Jean → 3 → 16**.
**Ouvrir dans cet onglet** applique la sélection ; **Ouvrir dans un nouvel onglet**
conserve le passage de départ. Les listes reflètent le contenu réel de la
traduction installée. **Saisie directe** (`Ctrl+K`) accepte notamment `Jean 3:16`,
`John 3:16` ou `John.3.16`.
L'interface est disponible en français et en anglais selon la
langue du système (`LANGUAGE=fr /usr/bin/python3 -m bible` pour forcer le français).

Couper le réseau, fermer et relancer l'application : la traduction installée
s'ouvre sans accès réseau. Pour changer de traduction installée, utiliser le
sélecteur du titre central. Les ressources sont conservées dans
`${XDG_DATA_HOME:-~/.local/share}/bible/translations`.

**Onglets et session** : `Ctrl+T` ouvre un nouvel onglet au passage courant ;
le sélecteur central propose aussi d’ouvrir le passage dans un autre onglet.
Chaque onglet garde sa traduction et sa position. `Ctrl+W` ferme l’onglet actif.
Fermer puis relancer restaure les onglets, leur ordre et l’onglet sélectionné.
Une traduction supprimée laisse son onglet et sa référence visibles avec un
message permettant de comprendre l’absence de texte.

**Commentaires** : dans la bibliothèque (`Ctrl+L`), choisir **Commentaires**,
lire les conditions et télécharger par exemple **Clarke** ou **MHCC**.
`F9` affiche/masque le panneau droit. Cliquer sur le texte d’un verset le sélectionne ;
`Alt+Haut/Bas` choisit le verset précédent/suivant du chapitre. Le commentaire suit
le verset et l’onglet actifs ; une entrée absente efface le texte précédent.
Le sélecteur du panneau permet de changer de commentaire, avec un choix mémorisé
par onglet et restauré au redémarrage. **Source et conditions** reste disponible
hors connexion. Dans une petite fenêtre, le panneau se superpose à la Bible.
Les numérotations des versets doivent correspondre : une incompatibilité est
signalée, sans alignement automatique. Pour un premier essai, utiliser **KJV**
avec **Clarke** ou **MHCC**. Voir [les commentaires et leurs limites](docs/COMMENTAIRES_CROSSWIRE.md).

**Notes** : menu de la Header Bar → **Note de passage** (`Ctrl+N`). Sélectionner
le texte de plusieurs versets du chapitre pour annoter un passage. L’éditeur
propose Markdown léger, aperçu sûr et labels ; **Enregistrer** conserve la note.
Les versets annotés sont soulignés. **Mes notes** (`Ctrl+Maj+N`) permet de
rechercher, filtrer par labels, trier et ouvrir les notes avec leur passage.
Son menu propose la sauvegarde/restauration vers un fichier JSON choisi.
Les notes restent disponibles si la traduction est supprimée ; les versifications
différentes ne sont pas assimilées. Voir [le guide des notes](docs/NOTES_DE_PASSAGE.md).

La session est conservée dans `${XDG_DATA_HOME:-~/.local/share}/bible/session.json`
(profil distinct dans Flatpak). Un fichier invalide ou de version inconnue est
préservé et signalé ; la sauvegarde reste désactivée jusqu’à sa réparation ou son
déplacement manuel, application fermée.

Le catalogue présente les Bibles et commentaires distribués par le dépôt principal CrossWire,
sans filtrer leur licence. La langue, la provenance, la licence et les conditions
sont visibles avant téléchargement. Les ressources chiffrées restent signalées,
avec téléchargement désactivé. **Ressources installées** permet de consulter
les attributions et conditions sans charger le catalogue, même hors connexion.
La Bible David Martin 1707 (`FreBDM1707`) est une version française à essayer.
Le Semeur n’est pas annoncé disponible : voir [l’étude des sources](docs/CATALOGUE_CROSSWIRE.md).

Le lecteur présente le texte brut produit par SWORD,
avec numéros de versets ; les notes de traduction et les enrichissements du
texte source ne sont pas encore présentés. Les conditions du fournisseur et les
règles du pays d'utilisation restent applicables.

## Vérifier

```sh
/usr/bin/python3 tools/check_environment.py --network
/usr/bin/python3 -m unittest tests.test_library -v
# Avec un affichage graphique ou avec Xvfb :
dbus-run-session -- xvfb-run -a /usr/bin/python3 -m unittest discover -v
# Télécharge réellement une traduction temporaire (aucune incluse dans Git) :
/usr/bin/python3 -m tools.check_crosswire
# Télécharge deux commentaires temporaires et vérifie leur fidélité :
/usr/bin/python3 -m tools.check_commentary
```

Les tests locaux utilisent des sentinelles textuelles identifiées comme fixtures,
sans se substituer au test d'intégration CrossWire. Le test hors connexion
interdit les appels réseau de Python après installation et recharge le contenu
sur disque ; un essai avec réseau désactivé sur poste GNOME reste à effectuer.

## Construction Flatpak de développement

Construction et import de SWORD dans le sandbox vérifiés en CI. Le lancement
graphique sur un poste GNOME reste à essayer ; aucun paquet publié ni acceptation
Flathub annoncé.

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//49 org.gnome.Sdk//49
flatpak-builder --user --install --force-clean build-dir packaging/io.github.icfmp.Bible.json
flatpak run io.github.icfmp.Bible
```

Voir [le catalogue et les conditions d’accès](docs/CATALOGUE_CROSSWIRE.md),
[la navigation dans la Header Bar](docs/NAVIGATION_HEADER_BAR.md),
[le jalon des onglets](docs/JALON_1_ONGLETS.md),
[la note technique et les résultats réels](docs/PROTOTYPE_GNOME.md),
[le cahier des charges](docs/CAHIER_DES_CHARGES.md) et
[la feuille de route](docs/FEUILLE_DE_ROUTE.md).

## Icône de l’application

Le livre bleu avec le titre « Bible » et le signet ocre est intégré au lanceur
Flatpak. Voir [la source, les exports et les finitions GNOME restantes](packaging/icons/README.md).
