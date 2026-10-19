# Bible

Prototype natif GNOME de lecture biblique, sans traduction préembarquée.
Le jalon #2 comprend un catalogue CrossWire réel, un téléchargement sur demande,
la lecture locale via SWORD et la navigation entre chapitres.

## Essayer sous Debian 13 ou Ubuntu 24.04

```sh
sudo apt update
sudo apt install python3 python3-gi python3-sword gir1.2-gtk-4.0 gir1.2-adw-1
cd Bible
/usr/bin/python3 -m bible
```

Utiliser le Python système, qui voit les bindings de la distribution. Depuis la
fenêtre, choisir **Charger le catalogue**, sélectionner une traduction puis
**Télécharger**. Après installation, le premier chapitre apparaît. Les flèches
changent de chapitre ; l'entrée accepte les références SWORD/OSIS, par exemple
`John 1:1` ou `Gen.2.1`. La saisie des noms de livres français n'est pas encore
prise en charge. L'interface est disponible en français et en anglais selon la
langue du système (`LANGUAGE=fr /usr/bin/python3 -m bible` pour forcer le français).

Couper le réseau, fermer et relancer l'application : la traduction installée
s'ouvre sans accès réseau. Pour changer de traduction installée, utiliser le
second sélecteur puis **Ouvrir**. Les ressources sont conservées dans
`${XDG_DATA_HOME:-~/.local/share}/bible/translations`.

Le catalogue de ce prototype se limite aux Bibles dont CrossWire déclare une licence réutilisable
(domaine public ou GPL), affichée dans le sélecteur. Le lecteur présente le texte brut produit par SWORD,
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
```

Les tests locaux utilisent des sentinelles textuelles identifiées comme fixtures,
sans se substituer au test d'intégration CrossWire. Le test hors connexion
interdit les appels réseau de Python après installation et recharge le contenu
sur disque ; un essai avec réseau désactivé sur poste GNOME reste à effectuer.

## Construction Flatpak de développement

Recette à vérifier avec le job Flatpak de la pipeline ; aucun paquet publié ni
acceptation Flathub annoncé.

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//49 org.gnome.Sdk//49
flatpak-builder --user --install --force-clean build-dir packaging/io.github.icfmp.Bible.json
flatpak run io.github.icfmp.Bible
```

Voir [la note technique et les résultats réels](docs/PROTOTYPE_GNOME.md),
[le cahier des charges](docs/CAHIER_DES_CHARGES.md) et
[la feuille de route](docs/FEUILLE_DE_ROUTE.md).
