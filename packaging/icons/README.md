# Icône Bible

## Direction approuvée

Livre bleu vertical, pages ivoire à droite, signet ocre en haut à droite et
mot « Bible » sur la couverture. Le client a choisi cette proposition le
19 octobre 2026. La première proposition rouge et la variante avec croix
ne sont pas retenues.

`bible-source.png` est l’image PNG RGBA originale générée avec l’outil de
création d’images de ChatGPT, puis corrigée à la demande du client pour
remplacer la croix par « Bible ». Ce fichier n’est pas une copie du logo
Bible.com. La proposition utilise des couleurs et une silhouette distinctes.

Les sous-dossiers 32x32 à 512x512 contiennent les exports pour le thème
hicolor. Le manifest Flatpak les installe sous le nom `io.github.icfmp.Bible`,
utilisé par le fichier desktop. Pillow sert uniquement à préparer ces
exports et n’est pas une dépendance de l’application.

## Reproduire les exports

Installer Pillow pour le Python de développement (par exemple
`sudo apt install python3-pil`), puis exécuter :

```sh
/usr/bin/python3 tools/export_app_icon.py
```

L’image originale est conservée sans retouche. Les exports changent
uniquement sa résolution et conservent le canal alpha.

## Finitions restantes — issue #13

L’image intégrée est une proposition raster approuvée ; elle n’est pas
présentée comme un SVG final validé par l’équipe design GNOME.

- Redessiner l’icône sur le gabarit GNOME 128×128 : grille de 2 px,
  marges, poids visuel et ligne de base.
- Privilégier les aplats sur les surfaces planes et un profil inférieur
  discret ; vérifier le mot « Bible » aux petites tailles.
- Préparer la version symbolique et la variante alpha/nightly.
- Vérifier dans App Icon Preview à 32 et 64 px et sur fonds clairs/sombres.

Références : [GNOME App Icons](https://developer.gnome.org/hig/guidelines/app-icons.html)
et [palette GNOME](https://developer.gnome.org/hig/reference/palette.html).

Aucune licence de projet ou d’asset existante n’est remplacée par cette
intégration. Le choix formel de licence du projet reste suivi dans sa
feuille de route.
