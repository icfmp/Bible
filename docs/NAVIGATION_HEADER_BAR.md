# Navigation dans la Header Bar — issue #5

Les outils d’étude décrits comme futurs ci-dessous ont depuis été complétés par
[les commentaires de l’issue #6](COMMENTAIRES_CROSSWIRE.md).

Le titre central affiche le livre, le chapitre, le verset et la version de
l’onglet actif. Il suit le changement d’onglet et la restauration de session.
Les issues #9 et #10 remplacent la présentation de l’issue #5 : le sélecteur
présente à gauche la recherche et la liste des livres en ordre biblique, groupés
selon le testament réellement fourni par SWORD. À droite : nom du livre et grille
de chapitres, chapitre actif marqué. Le livre actif est ramené dans la zone
visible à la réouverture. Sur petite largeur, les deux zones sont empilées et
défilantes. Les noms et groupes sont traduits en français et en anglais.

Le clic sur un livre puis sur un chapitre modifie directement l’onglet actif ;
le sélecteur reste ouvert pour préciser le passage. Le verset et la saisie directe
sont repliables, la traduction discrètement placée en haut. Aucune introduction
factice et aucun bouton « ouvrir dans cet onglet » / « nouvel onglet ».
Ctrl+T et l’action dédiée restent les seuls moyens de créer un onglet depuis
cette interface. Si le passage manque dans la traduction choisie ou que sa
versification diffère, un message demande de choisir explicitement son propre
chapitre ; l’ancien texte reste affiché jusqu’à ce choix, sans faux alignement.

Ctrl+G ouvre le sélecteur, Ctrl+K la saisie directe. Entrée applique une référence
française ou anglaise/OSIS valide. Les flèches du clavier dans la liste des livres,
Entrée/Espace et les boutons natifs sont utilisables sans souris. Les changements
automatiques de focus GTK ne doivent pas naviguer à la place de l’utilisateur.

Les commandes précédent/suivant sont désormais des boutons circulaires en
surimpression au milieu des bords de la zone de lecture. Des marges réservent leur
espace ; elles restent dans le panneau biblique, même avec l’étude à droite.
Elles restent visibles à 360 pixels, utilisent les couleurs système en clair et
sombre, et s’arrêtent aux limites réelles du contenu. Alt+Gauche/Droite garde
les mêmes actions. La Bible reste à gauche et l’étude à droite, escamotable
avec F9 ; sous 760 pixels, l’étude se superpose au texte.

Voir [les corrections alpha #8–#10](CORRECTIONS_ALPHA_8_10.md) pour les tests et
le paquet corrigé. La barre d’outils de lecture inspirée de Bible.com reste une
proposition distincte ; aucune fonction audio factice n’est ajoutée.

## Contenu réel du module

Le lecteur vérifie la versification déclarée avec les bindings SWORD, sans
accepter silencieusement le remplacement d’une versification inconnue par KJV.
Il parcourt les clés de cette versification et les index `hasEntry` du module :
seuls les livres, chapitres et versets présents sont proposés. Une traduction
NT seule ne propose donc pas la Genèse. Les noms traduits sont des métadonnées
d’affichage, pas une liste imposant le canon. Les versets absents ne produisent
pas de lignes vides inventées. Le texte reste celui de `stripText` de SWORD.

L’installation vérifie le premier passage réellement présent. Si une session
vise un passage absent dans une traduction disponible, un message explicite
accompagne l’ouverture du premier passage présent. Une saisie directe invalide
conserve le passage courant. Une traduction supprimée conserve son onglet.
La structure de session existante est inchangée.

## Vérifications historiques du jalon #5

32 tests automatisés passent localement en français et en anglais avec GTK
4.18, libadwaita 1.7 et SWORD 1.9 sous Xvfb. Ils couvrent la sélection de
Jean 3:16, le changement de version, les onglets et leur restauration, le
positionnement gauche/droite, l’affichage à 360 pixels et la visibilité du
verset après calcul des lignes repliées. Les tests de contenu créent de vrais
modules RawText avec des sentinelles explicitement fictives : NT seul, versets
absents et Tobie dans la versification Catholic. Aucun texte biblique généré
ni traduction complète n’est livré.

La CI exécute les tests GTK, répète les tests d’interface en français, puis
vérifie séparément un vrai téléchargement CrossWire, la présence de Jean 3:16,
la fidélité au texte SWORD et la réouverture avec réseau isolé. Elle construit
aussi le Flatpak GNOME 49 et importe le lecteur et l’interface dans le sandbox.
Les résultats de chaque exécution sont à consulter dans GitHub Actions ; les
tests locaux ne prouvent pas ces étapes réseau ou Flatpak.

Le proxy local bloque CrossWire et developer.gnome.org. Les recommandations
officielles ont été consultées depuis la CI, avec succès dans
[l’exécution de préparation](https://github.com/icfmp/Bible/actions/runs/39216559748) :
[Header Bars](https://developer.gnome.org/hig/patterns/containers/header-bars.html)
et [Scaling and Adaptiveness](https://developer.gnome.org/hig/guidelines/adaptive.html).
Le titre contextuel, les trois points d’alignement, les boutons sans bordure,
les infobulles et les adaptations à une fenêtre étroite suivent ces recommandations.

La validation manuelle sur un bureau GNOME réel reste à faire : télécharger
une traduction, sélectionner Jean 3:16 sans saisir de code, changer de version,
ouvrir un second onglet, fermer/relancer, puis réduire la fenêtre et ouvrir
l’étude. Aucun test Windows/macOS ni publication Flathub n’est revendiqué.
