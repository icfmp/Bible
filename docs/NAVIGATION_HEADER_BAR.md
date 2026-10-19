# Navigation dans la Header Bar — issue #5

Le titre central affiche le livre, le chapitre, le verset et la version de
l’onglet actif. Il suit le changement d’onglet et la restauration de session.
Son sélecteur propose Version, Livre, Chapitre, Verset, puis deux actions :
ouvrir dans l’onglet actif ou dans un nouvel onglet. La sélection reste provisoire
jusqu’à cette action. La saisie directe est repliée, accessible avec Ctrl+K ;
Ctrl+G ouvre le sélecteur, Alt+Gauche/Droite change de chapitre disponible.
Les noms de livres français sont acceptés, avec les références anglaises/OSIS.

Les contrôles redondants au-dessus du texte ont été supprimés. La Bible reste
à gauche et l’étude à droite, escamotable avec F9. Sous 760 pixels, l’étude
se superpose au texte. Les flèches disparaissent sous 560 pixels ; sous 420,
l’accès au catalogue reste dans le sélecteur et par Ctrl+L. Les listes ont des
libellés accessibles et sont utilisables au clavier. Les outils d’étude futurs
restent explicitement indisponibles.

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

## Vérifications

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
