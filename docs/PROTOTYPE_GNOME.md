# Prototype GNOME — issue #2

## Ce qui fonctionne

Fenêtre native GTK 4/libadwaita avec Header Bar, catalogue CrossWire réel,
téléchargement sur demande avec progression, erreurs et nouvelle tentative,
lecture locale par SWORD et navigation précédent/suivant entre chapitres.
Aucun texte biblique n'est embarqué. Le lancement n'effectue aucun appel réseau.

Le catalogue minimal présente les Bibles non chiffrées avec langue déclarée et
licence de domaine public ou GPL. La licence est affichée dans le sélecteur et la
configuration originale, contenant attribution et conditions, reste installée.
KJV est effectivement disponible, avec `DistributionLicense=GPL` dans le catalogue
observé. La disponibilité de FreSegond n'a pas été confirmée sous ce nom.

L'installation passe par un dossier provisoire puis un renommage atomique après
ouverture réelle par SWORD. Les transferts ont une limite de taille et un délai
réseau ; leur longueur est vérifiée quand annoncée. Le ZIP est vérifié par CRC,
les chemins sortants, liens symboliques et identités de ressource incohérentes
sont refusés. Une installation incomplète n'est pas annoncée comme utilisable.
Le réseau et l'installation s'exécutent sur un worker ; les changements GTK
passent par la boucle principale.

## Socle et versions

Python système, PyGObject, GTK 4, libadwaita et SWORD, sans dépendance pip pour
l'application. API communes à Ubuntu 24.04 (GTK 4.14/libadwaita 1.5) et Debian 13.
Les paquets de distribution gardent leurs mises à jour de sécurité ; leurs
versions exactes ne sont pas verrouillées par l'application.

Vérification locale cloud Debian 13 : Python 3.13.5, PyGObject 3.50.0, GTK 4.18.6,
libadwaita 1.7.6 et SWORD 1.9.0. Les paquets manquants ont été téléchargés depuis
Debian et extraits dans `/tmp`, puis chargés via les chemins temporaires Python,
GI et éditeur de liens, sans modifier le système.

Les bindings distribués ont été lus puis exécutés : `SWMgr`, `getModule`,
`VerseKey`, `setVersificationSystem`, `setAutoNormalize`, `getChapterMax`,
`getVerseMax`, `setKey`, `stripText`, `increment`, `decrement` et `popError`.
La validation désactive la normalisation pour éviter que « Gen.99 » soit déplacé
silencieusement dans un autre livre. La versification vient du module, avec le
défaut KJV de SWORD. Le texte est celui du filtre texte SWORD, sans génération.

La recette Flatpak cible GNOME 49, branche fixe bénéficiant des mises à jour de
runtime (commit non verrouillé). SWORD 1.9.0 et SWIG 4.3.0 sont verrouillés par
SHA-256 sur les archives sources Debian. C++17 est utilisé pour les bibliothèques
récentes du SDK. Le binding est généré avec SWIG et compilé pour le Python du SDK,
sans `distutils`, retiré des versions Python récentes. Le correctif
`sword-system-zlib.patch` retire de la liste d'installation `include/zconf.h`,
absent de l'archive DFSG ; zlib est fourni par le SDK.

Sources effectivement consultées :

- https://deb.debian.org/debian/pool/main/s/sword/ : sources 1.9.0,
  `bindings/swig`, `include/versekey.h`, `src/mgr/filemgr.cpp`, `cmake/README`.
- Documentation d'introspection embarquée dans les paquets GTK/libadwaita.
- https://deb.debian.org/debian/pool/main/s/swig/ : sources SWIG 4.3.0.
- https://github.com/flatpak/flatpak-builder/blob/main/src/builder-module.c :
  vérification du répertoire d'exécution des commandes après installation.

Les pages documentaires officielles citées dans le cadrage restent refusées par
le proxy de cette session, ainsi que CrossWire. Le runner GitHub dispose de l'accès
CrossWire et fournit les vérifications réelles complémentaires.

## Résultats vérifiés

Run du commit `3f7f3b5` :
https://github.com/icfmp/Bible/actions/runs/39210023315

- Job `prerequisites` réussi : dépendances, réseau, dix tests dont deux tests GTK.
- Catalogue réellement téléchargé et KJV sous GPL choisie par le test.
- Installation réelle, lecture des versets comparée au filtre SWORD et navigation.
- Réouverture avec appels réseau Python interdits.
- Lecture dans un autre processus exécuté par `sudo unshare --net --`, sans
  réseau ; empreinte des versets identique et navigation vérifiée.
- Job `flatpak` réussi : construction complète du manifeste et import du binding
  SWORD avec référence `John.1.1` dans le sandbox. Aucun paquet publié ni
  lancement graphique sur poste GNOME annoncé.

Vérifications locales supplémentaires : génération SWIG et compilation du binding
Python 3.13, construction CMake et installation de SWORD corrigé, lecture dans un
processus séparé, tests sur de vraies bibliothèques SWORD et GTK sous Xvfb.
Les fixtures locales sont des sentinelles identifiées, jamais présentées comme
une traduction biblique. Elles ne remplacent pas le téléchargement réel en CI.

Le test avec bus de session a permis de corriger une collision D-Bus dans les
tests : une seule application est désormais partagée entre leurs fenêtres, comme
dans le programme. Le catalogue utilise les continuations par antislash de SWORD,
non prises en charge initialement par le parseur INI standard ; régression testée.

Les avertissements SWIG/CMake et la dépréciation CSS sous GTK 4.18 n'ont pas empêché
les tests observés. Le diagnostic initial, antérieur au prototype, est conservé
dans `JALON_0_VERIFICATION.md`.

## Limites et essais manuels

Voir le README pour les commandes de lancement et de construction. Sur poste
GNOME : profil neuf vide, choisir puis télécharger une traduction, naviguer,
couper réellement le réseau, fermer et relancer, vérifier la lecture et les erreurs
avec nouvelle tentative. Aucun essai manuel sur le poste GNOME du client n'a été
réalisé depuis ce cloud. Xvfb ne prouve pas cette intégration de bureau.

Le texte est affiché par verset ; paragraphes, notes de traduction et autres
enrichissements restent à présenter. Références SWORD/OSIS (`John 1:1`, `Gen.2.1`),
sans noms de livres français. Validation et ouverture initiales sur Genèse 1 :
les ressources limitées à d'autres livres ne sont pas prises en charge.
Pas encore d'annulation/reprise de transfert, de mémorisation du dernier passage,
d'onglets, de notes, d'IA ou de synchronisation. Profils natif et Flatpak distincts.

YouVersion/Semeur : accès officiel, cache et téléchargement intégral toujours à
étudier ; aucune disponibilité hors connexion promise. Aucun contournement
ajouté. Windows/macOS : bindings et distribution GTK/libadwaita non validés.
Aucun paquet publié, aucune soumission Flathub, aucun choix formel de licence du
projet annoncé. Ce dernier reste à traiter avant la distribution publique.

## Suite du prototype

L’issue #3 ajoute les onglets et la restauration de session. Les limites ci-dessus
concernant leur absence décrivent uniquement la livraison initiale de l’issue #2.
Voir [le jalon 1](JALON_1_ONGLETS.md) et le README à jour.
