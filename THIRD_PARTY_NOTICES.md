# Dépendances et contenus

Bible est distribué sous GNU GPL version 2 uniquement (`GPL-2.0-only`),
selon le fichier `LICENSE`. Ce choix a été autorisé par le client pour la
préversion 0.1.0-alpha.1.

La licence du logiciel Bible ne remplace pas les licences ci-dessous ni celles
des Bibles et commentaires téléchargés. Aucune traduction complète n’est incluse.

## SWORD 1.9.0

Copyright CrossWire Bible Society, selon les notices de chaque fichier.
Les fichiers `LICENSE` et les en-têtes de la version 1.9.0 fournie indiquent la
GNU General Public License version 2. La bibliothèque et les bindings générés
sont inclus dans le Flatpak. Sa licence est installée dans
`/app/share/licenses/sword/LICENSE`.

Source originale épinglée :
https://deb.debian.org/debian/pool/main/s/sword/sword_1.9.0+dfsg.orig.tar.xz

Le correctif `packaging/sword-system-zlib.patch`, les options de compilation et
la génération des bindings sont dans `packaging/io.github.icfmp.Bible.json`.
L’archive de sources jointe à la release contient ces éléments et l’archive
originale de SWORD, permettant de reconstruire la version distribuée.

## SWIG 4.3.0

Outil de construction, non installé dans le paquet final. SWIG est distribué
sous GPL version 3 ou ultérieure ; les fichiers de bibliothèque et le code généré
bénéficient de l’exception décrite dans `LICENSE` et `LICENSE-UNIVERSITIES` de
ses sources. Conserver ces notices et consulter leurs termes complets.

Source originale épinglée :
https://deb.debian.org/debian/pool/main/s/swig/swig_4.3.0.orig.tar.gz

Cette archive est également jointe dans les sources de la release.

## Runtime GNOME

Le runtime org.gnome.Platform 49, téléchargé séparément depuis Flathub, fournit
notamment Python, PyGObject, GTK 4 et libadwaita sous leurs licences respectives.
Les sources et métadonnées du runtime sont disponibles via Flatpak/Flathub :
https://github.com/GNOME/gnome-build-meta

## Ressources CrossWire

Le téléchargement est volontaire. Les conditions, la provenance et la licence
déclarée par le module sont présentées dans le catalogue et les informations du
module. Les conditions d’une ressource ne s’étendent pas aux autres ressources.

## Babel 2.18.0 et CLDR

Babel fournit hors connexion les noms localisés et natifs des langues et le
format des dates. Le paquet Python est sous licence BSD à trois clauses ; ses
données CLDR conservent la licence Unicode. Les deux notices sont installées
sous `/app/share/licenses/babel/`. Le manifeste épingle le wheel original et
son SHA-256. Les codes des ressources restent distincts : les alias servent
uniquement à présenter leur nom.

## iso-codes 4.18.0

La base ISO 639-3 et sa traduction française complètent CLDR pour les langues
moins répandues. Licence LGPL-2.1-or-later, conservée sous
`/app/share/licenses/iso-codes/COPYING`. Source originale épinglée :
https://deb.debian.org/debian/pool/main/i/iso-codes/iso-codes_4.18.0.orig.tar.xz

Lors d’une distribution, joindre cette archive aux sources correspondantes,
avec le manifeste de construction. Aucun service de traduction n’est appelé.
