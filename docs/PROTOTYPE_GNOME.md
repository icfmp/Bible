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
- Catalogue obtenu de `mods.d.tar.gz`, filtré sur Bibles non chiffrées de langue déclarée, avec licence de domaine
  public ou GPL affichée, descriptions et langues réelles.
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
- Deux tests GTK sous Xvfb : ouverture de fenêtre, profil neuf vide, échec réseau
  asynchrone, boutons réactivés et nouvelle tentative réussie sur catalogue vide ; affichage et navigation sur données sentinelles installées.
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

## Première exécution de la nouvelle CI

Le run du commit `68a5716` valide les dépendances et les tests GTK. Le test
CrossWire échoue ; l'API Actions reste refusée (`Forbidden`) et GitHub demande
une connexion pour consulter les logs détaillés. Le lanceur `tools/ci_run.py`
remonte désormais les dernières lignes d'échec dans une annotation publique,
pour permettre le diagnostic de cette intégration sans inventer sa cause.

Le test de deuxième fenêtre a révélé une collision d'enregistrement D-Bus entre
deux instances de l'application dans le même processus de test :
`An object is already exported for the interface org.gtk.Application at /io/github/icfmp/Bible`.
Le test partage maintenant une seule application entre les fenêtres, comme le fait
le programme réel. Reproduction puis vérification de la correction effectuées
avec `dbus-run-session` et Xvfb : les deux tests GTK passent.

L'échec CrossWire a été identifié dans les annotations du run `ef80b11` :
`configparser.ParsingError` sur des lignes de copyright dans une description.
Le parseur suit désormais la continuation par antislash de
`FileMgr::getLine` dans les sources SWORD, et accepte les clés sans valeur.
Un test de régression vérifie ce format. Les huit tests du cœur passent aussi
avec la bibliothèque SWORD compilée localement depuis l'archive source.

La recette Flatpak utilise C++17 pour la compatibilité avec les bibliothèques
récentes du SDK. La compilation complète de SWORD depuis les sources a été
réalisée localement en C++17, ainsi que l'import des bindings et une lecture dans
un processus séparé. L'intégration CI est étendue pour exécuter cette lecture
via `sudo unshare --net --`, comparer l'empreinte des versets et vérifier la
navigation sans réseau dans ce processus. Le résultat du sandbox reste à confirmer.

Après correction du format, le catalogue renvoie bien des ressources réelles.
Le filtre exclut maintenant les entrées auxiliaires sans langue. Le catalogue
minimal accepte aussi les déclarations GPL, avec licence visible dans le
sélecteur et configuration originale conservée. Le test en ligne exige une
traduction connue (FreSegond ou KJV) plutôt que la première entrée du catalogue.

Le build Flatpak en C++17 compile SWORD mais rencontre ensuite une erreur réelle
d'installation : `file INSTALL cannot find "/run/build/sword/include/zconf.h"`.
L'archive Debian DFSG supprime ce fichier zlib embarqué ; le SDK fournit zlib.
Le correctif `packaging/sword-system-zlib.patch` retire uniquement cet en-tête de
la liste d'installation. La construction et l'installation locale des sources
corrigées sont vérifiées. Le résultat de construction Flatpak reste à suivre.
