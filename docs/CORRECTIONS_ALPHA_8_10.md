# Corrections alpha — issues #8, #9 et #10

## Téléchargements (#8)

Le défaut a été reproduit avec un serveur HTTPS local, un certificat explicitement
approuvé par le test et un transfert réel arrêté à plusieurs points intermédiaires.
Pour un petit ZIP inférieur à 64 Kio, `HTTPResponse.read(64 * 1024)` attendait de
remplir le bloc ou d’atteindre la fin : aucun octet reçu n’était signalé pendant
l’attente. La barre était ensuite remise à zéro à la fin de la tâche. Cela prouve
un cas du défaut, sans attribuer un symptôme visuel précis au premier essai client.

Le téléchargement utilise désormais `read1` pour signaler les octets disponibles.
Le nom apparaît immédiatement. Avec Content-Length fiable, la barre reflète les
octets reçus ; taille absente/invalide ou transfert chunked : quantité reçue et
activité indéterminée, sans faux pourcentage. Un timer GTK regroupe les événements
et anime l’activité même entre deux réceptions. Le thread de travail ne touche
pas aux widgets. L’installation/validation est une phase distincte ; le succès
n’est affiché qu’après validation SWORD et renommage atomique du dossier terminé.
L’erreur arrête l’animation et réactive la nouvelle tentative. Un nouveau transfert
repart à zéro, sans laisser l’état du précédent. Bibles et commentaires partagent
ce comportement.

## Sélecteur de passage (#9, précision visuelle incluse)

Depuis le titre de la Header Bar : surface arrondie, recherche des livres et
liste à gauche, groupes Ancien/Nouveau Testament issus de SWORD, noms traduits,
livre actif sélectionné. À droite : grand nom du livre et grille de chapitres,
chapitre courant marqué. Le bouton de fermeture est en haut à droite.

Livre, chapitre et verset modifient directement l’onglet actif. Le sélecteur reste
ouvert ; aucun bouton de validation ni choix de destination. Le verset et la
saisie directe sont repliables et facultatifs. La version est accessible en haut.
Si une autre traduction ne contient pas le passage, ou utilise une autre
versification, son sélecteur affiche un message explicite : choisir un chapitre
dans cette traduction. L’ancien texte reste affiché jusque-là ; aucune équivalence
n’est inventée. Le chapitre du candidat n’est pas présenté comme déjà lu.

La recherche ne change pas le passage. À la réouverture, le livre et le chapitre
actifs sont ramenés dans les zones visibles. Sur petite largeur, liste et grille
s’empilent et défilent ; les contrôles restent accessibles. Aucune introduction
factice. Les anciens boutons de l’issue #5 ne doivent pas revenir. Ctrl+T et
l’action dédiée conservent la création volontaire d’un onglet indépendant.

Les activations souris/Entrée et les flèches du clavier sont traitées comme des
choix. Une sélection interne provoquée par le focus ou le redessin GTK ne navigue
pas à la place de l’utilisateur. Le modèle de traduction n’est pas remplacé
récursivement dans sa notification : cela évite un plantage constaté sous GTK 4.18.

## Navigation pendant la lecture (#10)

Les boutons précédent/suivant quittent la Header Bar et deviennent deux chevrons
circulaires en surimpression au milieu des bords du panneau biblique. Des marges
dédiées évitent de masquer le texte. Ils restent centrés dans la partie visible
pendant le défilement et dans le panneau de la Bible lorsque l’étude est ouverte.
Ils restent disponibles sans survol, y compris à 360 pixels. Leur style, focus,
infobulles et noms accessibles suivent GTK/Adwaita et la langue de l’interface.

La navigation utilise les chapitres réellement indexés dans le module et sa
versification, saute les livres/chapitres absents et désactive les limites sans
boucler. Chaque changement ouvre le début du chapitre, met à jour le titre,
les commentaires et les notes, sans modifier les autres onglets. Alt+Gauche/Droite
reste disponible.

## Vérifications locales

- Suite générale : **72 tests réussis** sous GTK 4.18, libadwaita 1.7 et SWORD 1.9,
  avec Xvfb et le rendu Cairo.
- Interface française, dont les nouvelles régressions : **34 tests réussis**.
- Transfert HTTPS contrôlé : largeur réellement allouée au remplissage de la barre
  avant la fin du fichier, plusieurs états d’octets reçus, validation maintenue
  en attente, animation indéterminée, commentaire, erreur et second téléchargement.
- Sélecteur : recherche, 1 Corinthiens avec 16 chapitres et chapitre 15 sélectionné,
  traduction, cas incompatibles, deux onglets, réouverture et largeur de 360 pixels.
- Flèches : position mesurée par GTK pendant le défilement, avec/sans étude,
  clair/sombre, largeur de 360 pixels, début/fin et livres partiellement présents.
- Entrées X11 réelles automatisées : clic livre/chapitre, Espace sur un chapitre,
  Entrée et flèche Bas dans les livres, recherche saisie au clavier, fermeture,
  clic sur la flèche de lecture et indépendance des onglets.
- Captures réelles sous Xvfb examinées pour le sélecteur, les petites largeurs et
  la lecture en clair/sombre. Les textes de ces fixtures sont des sentinelles
  explicitement fictives, jamais des traductions livrées avec l’application.

```sh
dbus-run-session -- xvfb-run -a /usr/bin/python3 -m unittest discover -v
LANGUAGE=fr dbus-run-session -- xvfb-run -a /usr/bin/python3 -m unittest tests.test_ui tests.test_alpha_ui -v
LANGUAGE=fr dbus-run-session -- xvfb-run -a /usr/bin/python3 -m tools.check_alpha_ui
```

Le dernier contrôle nécessite X11/libXtst (paquet `libxtst6`) ; la CI l’installe.
Des avertissements de dépréciation GTK et de mesure d’infobulle peuvent apparaître
sous Xvfb ; ils ne remplacent pas les résultats des assertions.

## Paquet de test et essai client

Livraison vérifiée : commit [`c2792c1`](https://github.com/icfmp/Bible/commit/c2792c1),
[CI réussie](https://github.com/icfmp/Bible/actions/runs/39315036866),
[paquet de test corrigé (ZIP)](https://github.com/icfmp/Bible/actions/runs/39315036866/artifacts/12218475570).
Les deux jobs ont terminé avec succès, y compris les intégrations CrossWire,
la construction, l’installation et l’import du paquet. L’icône bleue intégrée
sur main pendant le travail est conservée. Les mises à jour de documentation
qui suivent ce commit ne changent pas le code de l’application ni le paquet.

La CI ne construit le Flatpak qu’après les tests et intégrations CrossWire.
Elle l’installe et vérifie SWORD/l’interface, puis joint dans l’artefact
**Bible-alpha-linux-x86_64** : `Bible-alpha.flatpak`, `SHA256SUMS`, `build-info.json`
(commit exact, architecture, résultat des prérequis et somme du fichier).
Les journaux de tests sont conservés dans **Bible-test-results**.

Sur [GitHub Actions](https://github.com/icfmp/Bible/actions), ouvrir l’exécution
réussie du commit correctif indiqué dans la livraison, télécharger l’artefact
(connexion GitHub nécessaire), puis décompresser le ZIP. Ouvrir le `.flatpak`
dans Logiciels GNOME et installer/mettre à jour. Le runtime provient de Flathub.
Le paquet reprend la licence GPL-2.0-only déjà autorisée et les notices de SWORD ;
aucun nouveau choix de licence ni changement de droits des contenus téléchargés.
La release **0.1.0-alpha.1 reste inchangée** ; aucune nouvelle release ni soumission
Flathub n’est effectuée dans cette tâche. L’artefact de test expire après 30 jours.

Si une alpha est déjà installée et que Logiciels ne propose pas la mise à jour,
réinstaller explicitement le paquet téléchargé, sans supprimer le profil :

```sh
flatpak install --user --reinstall ./Bible-alpha.flatpak
flatpak run io.github.icfmp.Bible
```

Pour vérifier le téléchargement : `sha256sum -c SHA256SUMS` dans le dossier extrait.
Les notes et ressources existantes restent dans le profil Flatpak ; aucune
migration de données n’est introduite.

**La validation manuelle du paquet corrigé sur le poste GNOME du client reste
à effectuer** : observer un téléchargement, essayer le sélecteur et les flèches,
le clavier, le thème sombre et la fenêtre étroite. Les contrôles Xvfb ne prouvent
pas ce parcours sur le poste du client. Les boutons inspirés de Bible.com restent
une proposition de barre d’outils dans la lecture ; aucune fonction audio ou
comparaison factice n’est ajoutée ici.
