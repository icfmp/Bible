# Captures et résultats #24/#25

`real-modules.png` : capture réelle GTK sous Xvfb, commentaire Kretzmann,
source AndBible Extra, sans gestionnaire de fenêtres GNOME. Elle ne prouve pas
le fonctionnement du plein écran natif sous GNOME. Le texte provient de SWORD,
sans génération. Conditions de la ressource dans `real-modules.json`.

Commande de reproduction sur un profil de test avec ressources préinstallées :

```sh
/usr/bin/python3 -m tools.check_paginated_resources PROFIL \
  'andbible-extra~PorRecebida' 'andbible-extra~Kretzmann' RESULTAT.json
```

La commande remplace la session du profil indiqué ; utiliser un profil de test.
Elle interdit les requêtes réseau Python pendant les contrôles ; aucun corpus
complet ne doit être ajouté au dépôt. Les tests unitaires utilisent séparément
des fixtures synthétiques clairement identifiées.
