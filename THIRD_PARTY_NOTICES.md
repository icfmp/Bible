# Dépendances et contenus

## JSword versification data (LGPL-2.1-or-later)

The expanded reference-only tables in `bible/versification_data` derive from
AndBible/JSword revision `6ebd10a005fa7761e611c048ececea1430e22546`.
Copyright CrossWire Bible Society and the individual JSword authors, including
Chris Burrell; original per-file notices are preserved in the complete upstream
source archive under `third_party/jsword`. The data retains LGPL 2.1 or later;
Bible's own GPL-2.0-only license is unchanged. No Scripture text is included.

`tools/versification/export.py` executes the original parser to expand its canon,
forward/reverse maps, verse-part qualifiers and absent sections into JSON.
The source archive, transformation source, dependency checksum lock and full
LGPL 2.1 text are included in this repository and the corresponding-source
distribution. See `third_party/jsword/provenance.json` for the immutable URL and
archive checksum. The installed Flatpak includes these JSON tables and the
license/provenance under `/app/share/licenses/jsword`. They can be replaced in
a local rebuild; no Java runtime or online mapping service is needed.

## Approved GNOME symbolic icons

The notebook and library SVG assets are the original 16 px GNOME Icon
Development Kit assets by Jakub Steiner, copied without redrawing from:
https://gitlab.gnome.org/Teams/Design/icon-development-kit/-/raw/main/icons/notebook.svg
and https://gitlab.gnome.org/Teams/Design/icon-development-kit/-/raw/main/icons/library.svg.
Their embedded RDF metadata declares CC0 1.0:
https://creativecommons.org/publicdomain/zero/1.0/.
Metadata is retained in the bundled files. The app's GPL-2.0-only license is
unchanged; no artwork is fetched at runtime.

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

## Polices DejaVu 2.37

Le menu Aa propose Livre (DejaVu Serif) et Simple (DejaVu Sans). Le Flatpak
installe les variantes normale, grasse, italique/oblique et grasse italique de
ces deux familles, sans téléchargement de police à l’exécution. Pango/fontconfig
conserve le repli vers d’autres familles pour les écritures non couvertes.

Paquets Debian originaux `fonts-dejavu-core` et `fonts-dejavu-extra` 2.37-8,
épinglés avec SHA-256 dans le manifeste. Polices dérivées de Bitstream Vera :
licence Bitstream Vera et modifications DejaVu dans le domaine public. Les
fichiers sont redistribués sans modification, avec les notices originales sous
`/app/share/licenses/dejavu/`. Les polices mathématiques et autres familles du
paquet extra ne sont pas installées. Source amont : https://dejavu-fonts.github.io/

## Optional OpenBible.info cross-reference data

User-requested download from <https://www.openbible.info/labs/cross-references/>;
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
Bible imports reference relationships and community scores, validates addresses,
and indexes/deduplicates/ranks them locally; no ESV quotations are included.
The Library and preview retain source/license credit. The audited dataset date,
checksum, numbering limits and transformations are documented in
[OPENBIBLE_REFERENCES_47.md](docs/OPENBIBLE_REFERENCES_47.md). This optional dataset
is not part of the application bundle. Installed Bible excerpts retain their
own resource terms.


## Optional OpenBible.info geographical data and Natural Earth coastlines

On explicit Library installation, Bible downloads the pinned OpenBible
[Bible-Geocoding-Data](https://github.com/openbibleinfo/Bible-Geocoding-Data)
(CC BY 4.0), with OpenStreetMap-derived components credited to © OpenStreetMap
contributors under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
No images, thumbnail payloads or OSM polygons are imported. Candidate coordinates,
reference associations and identification evidence are validated and transformed
into a local SQLite resource; source notices are retained in that resource.

The separate [Natural Earth](https://www.naturalearthdata.com/) 1:50m modern
coastline is public domain. Its vectors supply a simplified offline overview,
not historical boundaries or a street atlas. Attribution, source commits,
checksums, exact transformations and limits are documented in
[PLACE_CARDS_49_DESIGN.md](docs/PLACE_CARDS_49_DESIGN.md). Both datasets are
optional downloads and contain no imported Scripture quotations. Installed Bible
excerpts retain their own resource terms.


## Optional OpenBible.info topic relationships

Explicit Library download from <https://www.openbible.info/topics/> under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The local SQLite index
contains supplied English topic identifiers, Bible-reference ranges and quality
scores; no website ESV quotations are imported. Exact range duplicates retain
the maximum source score. The application exposes a deliberately partial,
curated 50-topic French/English vocabulary with authored synonyms, retaining
source identifiers and credit. Community associations are not doctrinal
conclusions. Source date, ZIP checksum, schema, transformations and coverage
are documented in [TOPIC_SEARCH_48.md](docs/TOPIC_SEARCH_48.md). Installed Bible
excerpts retain their own resource terms.
