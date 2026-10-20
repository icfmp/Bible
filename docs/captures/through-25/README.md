# Lecture réelle RTL — complément jusqu’à #25

Capture GTK 4.18/libadwaita 1.7 sous Xvfb, interface française, lecture de Jean 1
dans HebNTFD (Franz Delitzsch Hebrew New Testament), source AndBible Extra.
Licence déclarée dans le module : Public Domain. Le texte n’est ni généré ni
corrigé. Les 51 versets ont été comparés aux sorties natives SWORD ; seules les
empreintes sont conservées en JSON. Aucun module complet n’est ajouté au dépôt.

Reproduire avec une ressource déjà installée et ImageMagick disponible :

```sh
/usr/bin/python3 -m tools.check_rtl_resource PROFIL \
  'andbible-extra~HebNTFD' RESULTAT.json
```

Ce diagnostic n’ajoute pas de fonction d’import manuel dans l’application.
Il utilise un profil temporaire, sans modifier le profil source, et interdit
les connexions Python pendant les vérifications. Ce n’est pas un essai manuel
GNOME/Wayland, de lecteur d’écran, ni du Flatpak.
