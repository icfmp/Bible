# Catalogue multisource — issue #11

La bibliothèque consulte CrossWire, AndBible Extra (miroir de ressources Xiphos),
AndBible et STEP Bible en HTTPS, sans saisie d’URL. Le type, la langue, la recherche
et le nouveau filtre par source se combinent. Chaque choix et sa fiche indiquent
la provenance. Les conditions brutes restent visibles avant téléchargement,
y compris licence inconnue ou restrictive ; aucune exclusion silencieuse de licence.
Une langue absente est affichée avec le code `und`, sans éliminer la ressource.

## Comparaison mesurée

Audit du 19 octobre 2026 : [exécution](https://github.com/icfmp/Bible/actions/runs/39320409509),
commit `8b459d4`. Rapport complet dans **issue-11-source-audit** et dans les notes
Git `refs/notes/source-audit`. Chiffres de cet instant, non promesse de disponibilité future.

| Source examinée | Entrées | Commentaires | Noms absents de CrossWire |
|---|---:|---:|---:|
| crosswire | 429 | 41 | 0 |
| andbible-extra | 71 | 4 | 4 |
| andbible | 20 | 1 | 1 |
| step | 61 | 3 | 2 |
| xiphos-http | 84 | 8 | 7 |

Les 41 commentaires CrossWire ont tous une langue, un pilote déjà pris en charge
et aucune clé de chiffrement déclarée : ces filtres n’expliquent pas leur différence
avec Xiphos. Les nouveaux catalogues HTTPS apportent **sept noms de commentaires**
absents du catalogue principal lors de cet audit :

| Commentaire | Langue | Pilote | Source HTTPS ajoutée |
|---|---|---|---|
| Augustin | en | RawCom4 | andbible-extra |
| Chrysostom | en | RawCom4 | andbible-extra |
| Gill | en | zCom | andbible-extra |
| Kretzmann | en | zCom | andbible-extra |
| TSKe | en | zCom | andbible |
| Eng_MHM | en-Latn | zCom | step |
| TNotes | en | zCom | step |

Aucun de ces sept commentaires ne déclare `CipherKey` dans le catalogue examiné.
Cela ne valide pas la lecture ni tous les passages des sept ressources.
`VarApp` est également présent chez CrossWire et STEP : les deux provenances sont
conservées explicitement, sans choix arbitraire ni remplacement entre sources.

Le dépôt Xiphos standard est accessible en HTTP et FTP (`/pub/xiphos`), avec 84
entrées et huit commentaires dans les deux transports lors de l’audit. Son miroir
HTTPS AndBible Extra contient Augustin, Chrysostom, Gill et Kretzmann, pas tous les
ouvrages Xiphos : `Luther` existe déjà chez CrossWire ; `BibleArtBW` et
`DoreWoodcutsCom` sont de catégorie Images (rendu non pris en charge), et `NETnote`
n’est pas dans ce miroir. Aucune URL HTTPS Xiphos n’est inventée. L’application
conserve l’exigence HTTPS pour l’installation et n’ajoute pas directement HTTP/FTP.
Les Images/Maps restent non installables même si leur pilote est celui d’un commentaire.
Les dictionnaires, ouvrages généraux et autres types restent hors du lecteur actuel.

Le catalogue eBible a répondu **`HTTP Error 403: Forbidden`** depuis le runner ;
il n’est pas ajouté comme source fonctionnelle. Le manuel Xiphos renvoie la même
erreur, mais les sources logicielles et le wiki sont accessibles. Aucun refus n’a
été contourné. Les résultats des autres sources sont conservés.

## Identités et conservation des données

Les identifiants CrossWire historiques restent inchangés (`KJV`, `Clarke`, etc.).
Les autres installations utilisent `fournisseur~nom`, par exemple
`andbible-extra~Kretzmann`. Le caractère séparateur n’est pas autorisé dans les
anciens noms SWORD ; il empêche les collisions avec ces noms. Chaque installation
reste isolée dans son dossier. Le moteur reçoit le nom SWORD original, sans
modifier les configurations ou les textes fournis.

`.source.json` conserve l’identifiant stable, le nom interne, la source et son URL.
L’attribution est relue sur disque hors connexion. Les installations historiques
sans ce fichier restent attribuées à CrossWire. Aucune réécriture du profil, des
notes SQLite ni des anciennes sessions n’est effectuée. Le format de session
reste version 1 et accepte en plus les nouveaux identifiants ; les anciens sont
inchangés. Une ancienne alpha ne saura pas rouvrir une session utilisant ces
nouveaux identifiants : ne pas rétrograder le même profil après cet essai.

Un même nom dans deux sources donne deux choix avec provenance visible et deux
dossiers distincts. Une ressource déjà installée n’est jamais écrasée. Si le
catalogue et le paquet ne portent plus les mêmes conditions, identité, pilote ou
versification, le téléchargement échoue avec invitation à recharger le catalogue.
Le ZIP est borné, vérifié (CRC), extrait sans liens ni traversée de chemins, puis
ouvert réellement par SWORD avant installation atomique. Aucune somme distante
non fournie par le catalogue n’est inventée ; l’intégrité ZIP/HTTPS ne constitue
pas une signature des ouvrages par leurs auteurs.

## Disponibilité partielle

Les sources sont chargées indépendamment dans des workers. L’échec d’une source
n’efface pas les résultats réussis des autres. Le statut indique la source et
l’erreur ; **Charger le catalogue** permet de réessayer. Les ressources déjà
installées et leurs fiches restent accessibles avec **Ressources installées**,
sans réseau. Le chargement attend au maximum les délais des requêtes en cours ;
pas d’annulation/reprise partielle de transfert ajoutée dans cette livraison.

## Vérifications

Tests de collision de noms, chemins de paquets distincts, attribution hors
connexion, anciens profils, conservation des fichiers existants, absence de langue,
conditions et refus des formats/chiffrements non pris en charge. Tests GTK du
filtre par source, du résultat partiel, de la nouvelle tentative, de l’installation,
du suivi de verset et de la restauration de session. L’interface française compte
36 tests réussis localement, dont les nouvelles régressions multisources.

L’intégration `tools.check_affiliated_commentary` installe KJV et le commentaire
supplémentaire Kretzmann dans un dossier temporaire. Elle compare le texte affiché
par GTK au texte natif SWORD, suit deux entrées réellement indexées et vérifie que
l’absence d’une entrée efface l’ancien commentaire. Un second processus ouvre les
mêmes ressources avec le réseau isolé en CI (`sudo unshare --net --`), compare les
sommes des textes et la provenance, puis vérifie la session.

Le premier essai a échoué sur une hypothèse du test : **`AssertionError: John.3.16`**.
Kretzmann s’installe mais ses sections ne donnent pas une entrée exacte à chaque
verset. Le test utilise désormais les entrées réelles, et conserve un contrôle
explicite des versets absents. Le lecteur ne rapproche pas automatiquement une
section voisine d’un verset absent. La réussite finale de cette intégration et du
paquet sera indiquée avec leur exécution de CI dans la livraison.

```sh
python3 -m unittest tests.test_providers tests.test_provider_ui -v
python3 -m tools.audit_affiliated_sources
dbus-run-session -- xvfb-run -a python3 -m tools.check_affiliated_commentary
```

Aucun texte biblique/commentaire complet n’est versionné ni embarqué dans Bible.
Essai manuel du paquet sur le poste GNOME, lectures des six autres commentaires
supplémentaires et typographie complète des ressources non latines restent à faire.

## Sources officielles consultées

- [AndBible, configuration des dépôts au commit examiné](https://github.com/AndBible/and-bible/blob/7e73c11508f32e4f531d531f6d5b110dd2a1f204/app/src/main/res/raw/repositories.txt)
- [AndBible, choix et priorité des sources](https://github.com/AndBible/and-bible/blob/7e73c11508f32e4f531d531f6d5b110dd2a1f204/app/src/main/java/net/bible/service/download/RepoFactory.kt)
- [Xiphos, code du gestionnaire de ressources](https://github.com/crosswire/xiphos/blob/52302cb051d17e2bbe6846be52a942fb2490f75a/src/backend/module_manager.cc)
- https://wiki.crosswire.org/Official_and_Affiliated_Module_Repositories
- https://www.crosswire.org/ftpmirror/pub/sword/masterRepoList.conf
- https://xiphos.org/manual/module-manager.html (403 observé)

## Livraison vérifiée

[CI complète réussie](https://github.com/icfmp/Bible/actions/runs/39321775585),
commit applicatif `e78a578c8aca0daa928d0e1c21f8f7c34c8d4266` : **80 tests**, **36 tests
français**, interactions X11, intégrations CrossWire et commentaire affilié réussis.
Kretzmann : texte GTK fidèle à SWORD à **Jean 1:1 puis Jean 1:19**, absence explicite
à **Jean 3:2**, mêmes textes et provenance après réouverture dans `unshare --net`.
Le contrôle confirme aussi l’absence de routes réseau dans ce second processus.

[Flatpak Linux x86_64 de cette livraison (ZIP)](https://github.com/icfmp/Bible/actions/runs/39321775585/artifacts/12221070724)
(connexion GitHub nécessaire, conservation 30 jours). La construction, l’installation
et l’import SWORD/interface du paquet ont réussi. Le ZIP contient le paquet,
`SHA256SUMS` et `build-info.json` identifiant ce même commit. Les commits de
documentation suivants ne changent pas le code du paquet.

Décompresser, ouvrir `Bible-alpha.flatpak` avec Logiciels GNOME. Si une alpha est
déjà installée et que Logiciels ne propose pas le remplacement :

```sh
sha256sum -c SHA256SUMS
flatpak install --user --reinstall ./Bible-alpha.flatpak
flatpak run io.github.icfmp.Bible
```

Ouvrir **Bibliothèque**, charger le catalogue, choisir **Commentaires**, puis la
source **AndBible Extra (Xiphos)** et **Kretzmann**. Télécharger après lecture des
conditions ; ouvrir une Bible KJV et le panneau Étude, choisir Jean 1:1 puis 1:19.
Couper le réseau, fermer et rouvrir : vérifier la lecture et l’attribution.
Jean 3:2 n’a pas d’entrée exacte dans cette ressource : le panneau doit indiquer
l’absence plutôt que reprendre une section voisine. Les notes existantes ne sont
pas supprimées. La validation manuelle sur le poste GNOME du client reste à faire.
