# Lecture immersive et commentaires continus — #24 et #25

## Livraison

L’action Mode immersif, son bouton près de Aa et F11 ouvrent la Bible en
plein écran natif. Deux pages successives de la même ressource sont réellement
paginées ; une seule page apparaît sur fenêtre étroite ou en gros caractères.
Les pages sont des portions distinctes du texte, pas deux colonnes défilantes.
Un chapitre commence sur une nouvelle page ; une double page peut présenter la
fin d’un chapitre puis le début du suivant. Les comparaisons et panneaux sont
retrouvés en quittant la lecture immersive.

La taille, la police et la géométrie recalculent les coupures à partir de la
référence et d’un décalage de caractères dans le verset, y compris au milieu
d’un long verset. Les blancs de sélection ont leur propre affinité d’ancrage.
Le contenu est mesuré par Pango ; une réserve de ligne tient compte des
séparateurs de paragraphes rendus par GtkTextView. Les pages conservent ces
séparateurs, sans tronquer le corpus pour les faire tenir.

Le bouton local du commentaire ouvre uniquement celui-ci. Les flèches de page
s’arrêtent à la limite de son entrée ; Précédente/Suivante entrée disponible
permettent explicitement de changer d’entrée. Le titre, la référence et les
conditions de source restent accessibles. La Bible ne navigue pas en arrière-plan.
Ouvrir ce passage dans la Bible est une action explicite. La position du
commentaire est conservée pour la reprise ; aucune immersion au redémarrage.
Les paragraphes du texte SWORD dépouillé sont conservés ; la mise en forme riche
interne des commentaires n’est pas encore restituée intégralement.

## Essayer

1. Lancer l’application selon le README avec une Bible et un commentaire installés.
2. Dans l’étude, faire défiler la Bible puis le commentaire au clavier ou à la
   molette. Le dernier panneau manipulé guide l’autre, sans bouton de liaison.
3. Essayer une longue entrée : lire plusieurs écrans ne ramène pas son début
   lorsque le passage biblique appartient encore à sa plage native.
4. Appuyer sur F11, puis Page suivante/précédente ou Espace/Maj+Espace. Les
   flèches gauche/droite suivent le sens d’écriture ; la molette est temporisée.
   Une sélection empêche les raccourcis de page de la déplacer.
5. F10 révèle les commandes et donne le focus à la sortie. Le bord supérieur
   les révèle à la souris. Échap ferme d’abord le menu ouvert, puis quitte.
   F11 et le bouton de sortie quittent aussi. Ouvrir Notes/Bibliothèque suspend
   l’immersion. Le plein écran antérieur est conservé si déjà actif.
6. Modifier Aa, réduire la fenêtre et vérifier le passage atteint à la sortie.
   Essayer également le bouton immersif du commentaire, sa reprise et l’action
   explicite vers la Bible.

Ctrl+C conserve exactement la sélection. Les actions nommées de menu contextuel
permettent séparément de copier les versets, avec citation, ou leur référence.

## Alignement et ressources

L’index relève les entrées réelles et les liens natifs SWORD, introductions
comprises. Deux textes identiques non liés restent deux entrées. Les citations
internes et l’espace entre deux clés ne deviennent jamais une plage inventée.
Une entrée absente efface le commentaire précédent. Une versification différente
suspend l’alignement. Les mises en page et le défilement programmatique ne sont
pas des intentions utilisateur ; pas d’ajout à l’historique ni de prise de focus.

Seuls les textes des sections proches sont chargés : fenêtre de vingt sections
et cache de vingt textes ; cinq documents de pagination en cache. L’index des
clés est construit séparément. Le prototype présente un commentaire à la fois ;
la comparaison simultanée de plusieurs commentaires reste un objectif distinct.

## Notifications : repli explicite, sans modification du système

Le portail [Notification](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Notification.html)
expose AddNotification et RemoveNotification, pas un Ne pas déranger global.
Le portail [Inhibit](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Inhibit.html)
concerne la session et la veille. Aucun des deux ne fournit ici une suspension
publique des notifications liée au processus avec restauration sûre après crash.
La clé interne GNOME Shell show-banners n’apporte pas cette garantie et les
notifications critiques peuvent suivre d’autres règles.

Bible affiche donc l’aide prévue dans #24 pour activer manuellement Ne pas
déranger dans le menu de l’horloge. « Ne plus afficher » est mémorisé localement.
Aucun réglage de notifications de l’hôte n’est modifié, aucune permission
Flatpak de bus général ni exécution sur l’hôte n’est ajoutée.

Suivi restant lié à #24 : démontrer une API publique à durée de vie bornée dans
le Flatpak sous GNOME avant d’implémenter une suspension automatique. La création
d’une tâche GitHub de suivi est bloquée par l’absence d’authentification ; aucun
numéro fictif n’est annoncé. L’aide ne prétend jamais que les notifications sont
coupées. L’essai manuel sur le poste GNOME reste à effectuer.

## Vérifications réellement exécutées

- Suite complète finale : **112 tests réussis** (GTK 4.18, libadwaita 1.7,
  SWORD 1.9, Xvfb).
- Suite graphique française : **54 tests réussis** ; après les derniers
  ajustements de copie/notes, les **7 tests** d’immersion et de synchronisation
  concernés ont aussi été rejoués en français avec succès. Ensembles recouvrants.
- Pagination Unicode, longs versets, ancre après remise en page, sélection/copie,
  sens droite-à-gauche, passage une/deux pages, jointures entre chapitres,
  aller-retour et absence de texte omis/dupliqué testés automatiquement.
- Deux entrées Kretzmann réelles (Jean 1:1 : 20 760 caractères ; Jean 1:19 :
  13 611) et PorRecebida (Jean 1 et 2) mesurés en tailles 19/64. La concaténation
  des pages restitue exactement le document source. La lecture graphique de
  toute la longue entrée vérifie également les derniers glyphes de chaque page.
- Les événements clavier X11 sur ces ressources réelles vérifient le suivi
  commentaire → Bible puis Bible → commentaire. La pagination du commentaire
  laisse la Bible inchangée ; Jean 1:2, absent de l’index Kretzmann, efface bien
  l’ancienne entrée. Les connexions Python et URL sont interdites pendant ces
  contrôles ; ce n’est pas une isolation réseau du système d’exploitation.
- Le scénario X11 sur fixtures vérifie clics, changement de panneau pilote,
  F11, Page suivante, F10 et Échap (menu d’abord, sortie ensuite).
- Compilation Python, `actionlint` et `git diff --check` réussis.

[Résultats et empreintes des modules réels](captures/reading-24-25/real-modules.json)
et [capture de l’entrée Kretzmann](captures/reading-24-25/real-modules.png).
Kretzmann : œuvre d’origine dans le domaine public, édition électronique assortie
notamment de conditions de reproduction sans altération ; conditions conservées
dans le résultat et la fiche de ressource. Aucun ouvrage complet n’est joint.

Ces contrôles n’attestent pas le plein écran d’un compositeur GNOME : Xvfb est
utilisé sans gestionnaire de fenêtres. L’appel natif et la restauration de l’état
sont implémentés ; le plein écran effectif, Wayland, les gestes d’un pavé tactile
réel, le lecteur d’écran et les portails dans le Flatpak restent à essayer sur le
poste cible. Des avertissements GTK de mesure/allocation et des dépréciations
subsistent lors de certains scénarios, sans échec d’assertion. La mise en forme
riche des commentaires et la comparaison de plusieurs commentaires restent limitées.

## Reprise par le product manager

La PR #23 publiée a pour tête `87db216839d7d5a95dd5e80c71f3c7ce08e8e924`.
Ses 107 fichiers correspondent exactement au commit local `d389954` : comparaison
binaire de l’archive GitHub avec tous les fichiers suivis, aucun écart ni ajout.
Le patch complémentaire part de cet état et comprend le complément Aa `ef88419`
puis les changements #24/#25 ; il ne réintroduit pas la livraison déjà publiée.
Les commits locaux d’origine sont conservés. Appliquer le patch sur la branche
réelle de la PR ou une branche qui la contient, jamais en poussant l’ascendance
du snapshot local `d8fc09e`.

La CI verte de #23 et sa construction Flatpak sont signalées par le client.
Elles ne couvrent pas les nouveaux commits de ce patch : après publication par
le product manager, laisser GitHub Actions vérifier et construire ces derniers.
Aucun nouveau paquet Flatpak ni nouvelle release n’est annoncé ici. Le SDK reste
inaccessible localement (`curl: (56) CONNECT tunnel failed, response 403`).
L’essai manuel sur le poste GNOME reste à effectuer.
