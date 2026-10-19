# Jalon 0 — prototype GNOME de l'issue #2

## Choix du socle

Python + PyGObject + GTK 4 + libadwaita et SWORD sont conservés. Le code utilise
les API communes à GTK 4.14/libadwaita 1.5 (Ubuntu 24.04), sans dépendance pip.
Les mises à jour de sécurité des paquets restent fournies par la distribution.
Les versions exactes de la distribution sont consignées par le diagnostic de CI.

Vérification locale dans le cloud Debian 13 : Python 3.13.5, PyGObject 3.50.0,
GTK 4.18.6, libadwaita 1.7.6, SWORD 1.9.0. Les bibliothèques manquantes ont été
extraites de paquets Debian dans `/tmp`, puis chargées via les chemins temporaires
Python/GI/éditeur de liens. Aucune installation système privilégiée nécessaire.

Les méthodes SWORD sont vérifiées dans les bindings SWIG distribués et par leur
exécution : `SWMgr`, `getModule`, `VerseKey`, `setVersificationSystem`,
`setAutoNormalize`, `getChapterMax`, `getVerseMax`, `setKey`, `stripText`,
`increment`, `decrement` et `popError`. La normalisation est désactivée pendant la
validation d'une référence, pour éviter que « Gen.99 » saute silencieusement dans
un autre livre. La versification vient du module, avec le défaut KJV de SWORD.

Le manifeste Flatpak cible GNOME 49, branche fixe. SWORD 1.9.0 et SWIG 4.3.0 sont
verrouillés par SHA-256 sur les archives sources Debian. Le runtime bénéficie de
ses mises à jour ; son commit exact n'est pas verrouillé. Le paquet ne contient
aucune traduction. Les bindings sont générés avec SWIG et compilés pour le Python
du SDK. Cette voie évite `distutils`, utilisé par le CMake amont SWORD 1.9.0 et
retiré des versions Python récentes. La génération et l'import du binding ont
été vérifiés localement avec SWIG 4.3.0 et Python 3.13. La construction complète
dans le sandbox Flatpak reste à confirmer par le job dédié.

Sources consultées pour le code et la construction :

- Source SWORD 1.9.0 redistribuée par Debian : https://deb.debian.org/debian/pool/main/s/sword/
  (notamment `bindings/swig`, `include/versekey.h`, `cmake/README`).
- Introspection et documentation embarquées dans les paquets Debian GTK 4 et libadwaita.
- Sources SWIG 4.3.0 : https://deb.debian.org/debian/pool/main/s/swig/

Les pages officielles GNOME, CrossWire et Flatpak citées dans le cadrage restent
refusées par le proxy de cette session ; leur consultation courante n'est donc
pas annoncée comme réalisée. La CI précédente validait les dépendances sur
Ubuntu ; la nouvelle CI ajoute les vérifications fonctionnelles.

## Comportement et limites

- Aucun accès réseau automatique au démarrage ; affichage des seules ressources installées.
- Catalogue obtenu de `mods.d.tar.gz`, filtré sur Bibles non chiffrées déclarées
  « Public Domain », avec descriptions et langues réelles.
- Téléchargement HTTPS dans un dossier provisoire, progression et vérification
  de longueur quand connue, limites de taille, CRC ZIP, refus des chemins sortants
  et des liens symboliques, puis ouverture réelle par SWORD avant renommage atomique.
- Une installation interrompue n'est pas annoncée comme utilisable. Une nouvelle
  tentative est possible avec le même bouton. Pas encore d'annulation/reprise.
- Opérations réseau et installation sur un worker ; GTK reçoit ses mises à jour
  par la boucle principale. Aucun balisage téléchargé exécuté ou rendu comme GTK.
- Lecture depuis les fichiers locaux avec le filtre texte de SWORD, sans génération
  de texte. Les enrichissements et notes du texte source restent à présenter.
- Premier chapitre de la Genèse utilisé pour valider et ouvrir une Bible ; les
  ressources limitées à d'autres livres ne sont pas encore prises en charge.
- Pas de mémorisation du dernier passage, onglets, annotations, IA ou synchronisation.

## Résultats locaux réels

- Sept tests du stockage/catalogue/transfert/lecteur : réussis, sur les vrais
  bindings SWORD et des données sentinelles de test.
- Test GTK sous Xvfb : ouverture de fenêtre, profil neuf vide, échec réseau
  asynchrone, boutons réactivés et nouvelle tentative réussie sur catalogue vide.
- Génération SWIG et compilation d'une extension SWORD Python 3.13 : réussies,
  import et référence `John.1.1` vérifiés.
- Catalogue et archive CrossWire depuis cette session : refus réel
  `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>`.
- Le test `tools.check_crosswire` est prévu sur le runner disposant de cet accès :
  téléchargement, comparaison des versets au filtre SWORD, réouverture avec appels
  réseau interdits et navigation. Son succès ne doit être annoncé qu'après CI.
- Aucun essai manuel sur le poste GNOME du client, Windows ou macOS.

Les avertissements locaux GTK portent sur l'absence de bus de session et la
méthode CSS dépréciée dans GTK 4.18, conservée pour GTK 4.14. SWORD/SWIG émettent
des avertissements de dépréciation. Ils n'ont pas empêché les tests observés.

## Sources complémentaires et portabilité

YouVersion/Semeur : accès officiel, cache et téléchargement intégral toujours à
étudier séparément ; aucune disponibilité hors connexion promise. Aucun scraping
ni contournement d'accès ajouté. Windows/macOS : bindings et distribution de GTK/
libadwaita non validés ; ces systèmes ne sont pas annoncés comme pris en charge
par ce prototype. Le choix formel de licence du projet reste à traiter avant une
distribution publique ; aucune licence de contenu n'est attribuée par l'application.
