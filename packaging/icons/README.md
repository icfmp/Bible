# Icône Bible

Livre bleu vertical, pages ivoire à droite, signet ocre en haut à droite et
mot « Bible » sur la couverture : direction choisie par le client le
19 octobre 2026. Ni croix ni première proposition rouge.

`bible-source.png` conserve sans retouche la proposition PNG RGBA créée avec
l’outil d’images de ChatGPT puis corrigée à la demande du client. Cette référence
artistique reste distincte du dessin vectoriel repris pour l’intégration GNOME.

## Sources et exports

- `scalable/apps/io.github.icfmp.Bible.svg` : dessin sur canevas 128×128, surfaces
  planes, profil inférieur discret, ligne de base à 116 unités ; texte vectorisé.
- `scalable/apps/io.github.icfmp.Bible.Devel.svg` : variante de développement avec
  bande diagonale, préparée sans changer l’identifiant de l’application stable.
- `symbolic/apps/io.github.icfmp.Bible-symbolic.svg` : silhouette monochrome 16×16.
- `32x32` à `512x512` : exports PNG transparents depuis le SVG.

Le manifeste installe PNG, SVG et symbolique dans hicolor. Le fichier desktop
utilise `io.github.icfmp.Bible`. Les deux symboles de commandes Bibliothèque et
Mes notes sont distincts et vivent dans `bible/icons/hicolor/scalable/actions/`.

Installer Inkscape puis lancer depuis le dépôt :

```sh
python3 tools/export_vector_icons.py
```

`tools/export_app_icon.py` appelle désormais le même export vectoriel, pour
éviter qu’une ancienne commande remplace les nouveaux PNG par des rasterisations
de l’ancienne proposition. Ni Inkscape ni Pillow ne sont requis à l’exécution.

## Contrôles et limite restante

Les SVG sont analysés comme XML, les exports 32/64 et la variante Devel ont été
présentés dans une véritable fenêtre GTK en clair et sombre sous Xvfb ; captures
sous `docs/captures/remaining-issues/icons-*.png`. Les symboles de commandes sont
trouvés par le thème GTK. La revue spécifique dans **App Icon Preview** reste à
faire : cet outil n’est pas installé ici. Ne pas assimiler cette revue locale à
une validation de l’équipe design GNOME.

Références : [GNOME App Icons](https://developer.gnome.org/hig/guidelines/app-icons.html)
et [palette GNOME](https://developer.gnome.org/hig/reference/palette.html).
Le projet est sous GPL-2.0-only ; aucune licence existante n’est remplacée.
