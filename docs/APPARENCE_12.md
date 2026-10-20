# Aa — décision actualisée de l’issue #12

La description publique de #12 a été relue le 20 octobre 2026, y compris son
complément final sur le contraste élevé. Cette livraison conserve les changements
des autres issues et complète le premier panneau de réglages.

## Commandes disponibles

Ouvrir Aa dans la Header Bar, ou Apparence de lecture dans le menu sur petite
largeur. Aucun bouton Appliquer : le texte se remet en page immédiatement.

1. **Livre** (DejaVu Serif, défaut) et **Simple** (DejaVu Sans), avec aperçu dans
   leur propre police. Le manifeste installe les huit fichiers nécessaires aux
   vrais gras et italiques, avec leurs licences. Pango assure le repli des écritures.
2. **A− / valeur / A+**, de 12 à 64 pt ; boutons désactivés aux limites.
3. **Système** (défaut), **Jour**, **Nuit**, via `Adw.StyleManager`.
4. **Couleurs de jour** : Blanc (défaut), Papier (sépia). **Couleurs de nuit** :
   Gris sombre (défaut), Noir. Chaque groupe garde son choix ; une pastille ne
   change pas le mode. Système retrouve le bon groupe lorsque le bureau change.

La section **Mise en page** propose interligne Serré/Normal/Aéré et colonne
Étroite/Normale/Large (580/760/960 pixels maximum avant adaptation à la fenêtre).
Elle ne modifie pas la largeur de l’étude. Les numéros de chapitres et de versets
restent indépendants. **Rétablir les réglages** conserve les textes installés,
notes et sauvegardes. Les préférences sont locales, atomiques, communes aux onglets
et compatibles avec le premier fichier de préférences ; un fichier invalide est
préservé. La sélection et l’ancrage dans le corps du passage sont conservés pendant
la remise en page, y compris lors de commandes rapides successives.

## Contraste élevé

Aucun interrupteur supplémentaire : notifications `notify::high-contrast` et
`notify::dark` de libadwaita. Le lecteur biblique, la comparaison et le texte des
commentaires prennent une palette noir/blanc cohérente avec le mode actif.
La typographie choisie reste en place. Les pastilles sont indisponibles avec une
explication ; les choix de jour/nuit sont conservés puis restaurés. Les boutons,
menus, focus et fenêtres restent natifs. La CSS de couleur est limitée aux zones
de texte et aux pastilles, sans recolorer globalement l’application.

Les icônes Bibliothèque/Mes notes sont désormais dans un véritable thème hicolor :
GTK les identifie comme symboliques et les recolore en sombre/contraste élevé.
Les chevrons gardent les styles natifs circulaires/OSD, adaptés par Adwaita.

## Vérifications réelles

- Tests GTK : commandes de police/taille/mode/mise en page et numéros ; partage
  entre onglets, redémarrage, conservation des notes lors de la réinitialisation.
- Changement clair/sombre et contraste élevé à chaud avec les notifications
  libadwaita ; contrôle de la couleur réellement calculée par GTK dans les deux
  lecteurs, de la sélection et des palettes restaurées. L’API privée d’override
  de libadwaita est utilisée **seulement dans les tests** pour émuler le système.
- Calcul WCAG des six palettes : texte et numéros au moins 7:1, liens au moins
  4,5:1, sélection au moins 4,5:1 (7:1 pour les palettes de contraste élevé).
- Ancrage après changement rapide taille/largeur ; texte 64 pt à 360 pixels ;
  accents, grec, hébreu et arabe rendus sans glyphe manquant dans l’environnement.
- Module de polices : les commandes d’extraction/installation du manifeste ont
  été exécutées dans un préfixe temporaire ; huit fontes et deux notices vérifiées.

Captures réelles GTK/Xvfb dans `captures/appearance-12/` : quatre palettes,
contraste élevé clair et sombre, Aa, indication système et très gros caractères.
Le texte biblique est celui du module danois public DanDetteBiblen. Le commentaire
visible est un **jeu synthétique de test du rendu**, explicitement marqué, sans
contenu théologique inventé présenté comme une vraie ressource. Aucun module
complet n’est inclus dans Git.

Résultats : suite complète **102 tests réussis**, interface française **44 tests
réussis**, dont cinq vérifications spécifiques d’apparence. Les ensembles se
recouvrent. Le test natif X11 active Aa à la souris et au clavier (Espace/Entrée,
choix de police, taille, palette, mode, numéros et Échap). Les noms accessibles
incluent la valeur de taille ; l’essai avec un véritable lecteur d’écran reste
à faire. Une exécution simultanée des deux grosses suites a rencontré des délais
d’attente GTK ; les résultats retenus sont ceux des exécutions séquentielles,
comme dans la CI. Les tests attendent explicitement la fin de la remise en page.

## Essai GNOME/Flatpak restant

Les notifications émulées et captures Xvfb ne prouvent pas le fonctionnement du
portail sur le poste du client. Un nouveau Flatpak n’a pas pu être construit :
le SDK Flathub est bloqué par le proxy (`403 Forbidden`) et l’envoi GitHub reste
bloqué faute d’identifiant. La CI GitHub des nouveaux commits n’a pas été exécutée.

Après construction du paquet du même commit, ouvrir Bible et un commentaire,
choisir Papier, activer le contraste élevé dans les réglages GNOME sans relancer,
puis le désactiver. Répéter en sombre, puis changer clair/sombre en mode Système :
les palettes mémorisées doivent revenir. Contrôler sélection, liens si présents,
numéros, notes, chevrons, focus clavier, lecture avec lecteur d’écran et gros texte.
La couverture des écritures autres que celles testées dépend des polices de repli
fournies par le runtime et le système. Aucun téléchargement de police n’est lancé
par Bible.

L’audio, les surlignages et les modes continu/paginé restent futurs ; aucune commande
factice n’est ajoutée. Un ticket lié pour les surlignages reste à créer lorsque
l’accès GitHub sera disponible ; leur visibilité n’est pas annoncée implémentée.
La revue App Icon Preview de #13 reste également à faire.

Référence officielle : [Styles & Appearance](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/styles-and-appearance.html).
Les signatures et règles ont aussi été vérifiées dans la source publique de
libadwaita 1.7.0 correspondant à l’environnement de test.
