# Issue #2 — diagnostic du socle

## Statut

Le jalon n'est pas réalisé. Aucun prototype graphique, téléchargement de traduction,
lecture hors connexion ou paquet Flatpak n'a été validé. Cette livraison contient
uniquement un diagnostic reproductible des prérequis ; elle ne clôt pas l'issue #2.
Les exigences du cahier des charges restent inchangées.

## Vérifications réelles — environnement cloud Debian 13, 19 octobre 2026

Commande exécutée :

```sh
/usr/bin/python3 tools/check_environment.py --network
```

Résultat : code de sortie 1, dix prérequis en échec.

| Composant | Résultat observé |
| --- | --- |
| Python système | 3.13.5 |
| PyGObject | 3.50.0, import réussi |
| GTK 4 | `ValueError: Namespace Gtk not available for version 4.0` |
| libadwaita | `ValueError: Namespace Adw not available` |
| SWORD Python | `ModuleNotFoundError: No module named 'Sword'` |
| Flatpak / flatpak-builder | exécutables absents |
| Serveur graphique de test Xvfb | exécutable absent |
| Catalogue CrossWire | `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>` |
| Archive CrossWire KJV.zip | même refus, vérifié séparément par requête GET |
| Documentations officielles | même refus sur les quatre pages ci-dessous |

Sources officielles dont la consultation a été tentée, sans succès :

- https://pygobject.gnome.org/getting_started.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/
- https://www.crosswire.org/sword/develop/
- https://docs.flatpak.org/en/latest/first-build.html

Les versions présentes ne sont pas une sélection de dépendances validée.
Le choix et le verrouillage des versions compatibles restent à faire après accès
aux sources officielles. L'outil de diagnostic n'installe rien et ne télécharge
aucun texte biblique ; l'option réseau teste les en-têtes HTTP des sources.

## Lever les blocages et essayer

Configurer l'environnement pour autoriser les domaines `www.crosswire.org`,
`pygobject.gnome.org`, `gnome.pages.gitlab.gnome.org` et `docs.flatpak.org`.
Prévoir également `api.github.com` pour les opérations GitHub par API.
Les éventuelles redirections et dépendances supplémentaires devront être vérifiées
à partir de leurs erreurs réelles. Aucun contournement du proxy n'est proposé.

Sur un poste Debian disposant des paquets correspondants, la commande de préparation
suivante est une piste à vérifier par un administrateur, non une installation testée :

```sh
sudo apt update
sudo apt install python3 python3-gi python3-sword gir1.2-gtk-4.0 gir1.2-adw-1 flatpak flatpak-builder
/usr/bin/python3 tools/check_environment.py --network
```

Cet environnement ne dispose pas de `sudo`. Les paquets GTK n'ont pas de candidat
dans ses index APT actuels ; aucune installation système n'a été réalisée.
Utiliser le Python système pour accéder aux bindings de la distribution.
Un diagnostic réussi ne prouverait pas encore la lecture ou le packaging.

Il n'existe pas encore de commande pour lancer le prototype. Après déblocage,
il reste à éprouver SWORD sur une vraie ressource autorisée, développer la fenêtre
GTK native et le téléchargement asynchrone avec progression, erreur et nouvelle
tentative, puis vérifier la navigation et la fidélité hors connexion. Construire
ensuite le Flatpak et le lancer sur un poste GNOME. Aucun manifeste spéculatif
n'est présenté comme une recette fonctionnelle.

## Limites complémentaires

YouVersion et Semeur : ni modalités officielles d'accès ni téléchargement intégral
hors connexion vérifiés. Aucune disponibilité promise. Windows et macOS : aucun
build ou essai réalisé ; l'accès aux bindings SWORD et la distribution de GTK/
libadwaita y restent à étudier. Aucun changement de pile technique décidé.

## Vérifications non réalisées

Pas de test GUI, poste GNOME, intégration SWORD, transfert réel, fidélité de texte,
lecture hors connexion, navigation ni construction Flatpak. Aucun corpus ou texte
biblique factice ajouté. Les seules vérifications positives sont l'import PyGObject,
l'exécution du diagnostic et la compilation syntaxique de son code Python.
