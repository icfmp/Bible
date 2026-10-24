# Canal alpha Flatpak — issue #17

## État réel de cette livraison

L’activation publique a réussi au workflow
[39325789404](https://github.com/icfmp/Bible/actions/runs/39325789404) :
installation publique et mise à jour entre deux révisions signées validées.
La configuration et la clé existantes doivent être conservées. **Ne pas relancer
la configuration initiale ci-dessous pour réparer une publication.**

Installation : https://icfmp.github.io/Bible/alpha/Bible.flatpakref

La publication suivante
[39325929556](https://github.com/icfmp/Bible/actions/runs/39325929556) a échoué :
`error: Listing refs: opendir(refs/remotes): No such file or directory`.
Git ne conserve pas les répertoires vides OSTree. La restauration recrée maintenant
les répertoires structurels manquants sans réinitialiser le dépôt, modifier sa
configuration, remplacer la clé ni ajouter de faux fichiers de références.

Le test `tests.test_channel_storage` publie deux vrais commits OSTree via un
aller-retour Git et vérifie leur filiation et leur intégrité avec `ostree fsck`.
Le contrôle Flatpak et la publication publique restaurent aussi depuis Git avant
la seconde révision. Ils vérifient `flatpak update` et des fichiers sentinelles
créés dans un sous-dossier distinct du profil applicatif, sans remplacer les
données existantes. Ces sentinelles contrôlent la conservation des fichiers ;
elles ne constituent pas une validation fonctionnelle des notes de l’utilisateur.
La clé du contrôle local est éphémère et distincte de la clé publique stable.
L’essai manuel sur le poste GNOME du client reste nécessaire.

## Configuration unique à effectuer par le product manager

Après revue et fusion de cette branche, depuis le dépôt à jour sur un poste
fiable avec Python 3, GnuPG, Git et `gh` déjà connecté au compte administrateur :

```sh
python3 -m tools.setup_alpha_channel
```

Cette commande :

1. Vérifie que le workflow est présent sur main et que la connexion peut
   administrer `icfmp/Bible` ; refuse un site Pages existant non géré par ce canal.
2. Crée une clé dédiée RSA 3072 de signature, valable deux ans, **une seule fois**.
   Sauvegarde la clé et son certificat de révocation dans le dossier privé
   `$XDG_DATA_HOME/bible-alpha-signing` (par défaut `~/.local/share/bible-alpha-signing`),
   hors Git, avec accès restreint. Conserver cette sauvegarde hors ligne.
3. Transmet la clé privée au secret Actions `BIBLE_FLATPAK_GPG_KEY` par l’entrée
   standard de `gh`, sans l’afficher. Enregistre son empreinte dans la variable
   `BIBLE_FLATPAK_GPG_FINGERPRINT`. Une clé existante n’est pas régénérée.
4. Active Pages avec `build_type=workflow` et enregistre l’URL HTTPS réellement
   retournée par GitHub dans `BIBLE_ALPHA_PAGES_BASE_URL`, puis marque ce site géré
   avec `BIBLE_ALPHA_PAGES_MANAGED=1`.
5. Déclenche la publication depuis la dernière CI réussie sur main. Celle-ci doit
   contenir au minimum le commit correctif `c2792c1` (#8–#10 et icône).

Si une organisation restreint Pages/environnements Actions, traiter l’erreur
réelle indiquée par `gh` ; ne pas désactiver la protection GPG pour la contourner.
La commande ne supprime aucun profil de Bible et ne change pas les installations
Flatpak du poste qui l’exécute.

Le workflow fournit **le lien exact du `.flatpakref` dans son résumé uniquement
après la réussite de l’installation et de la mise à jour publiques**. Avant cette
réussite, utiliser les bundles des releases, sans annoncer le canal actif.

## Identité et distribution

- Application : `io.github.icfmp.Bible`.
- Architecture du dépôt : `x86_64`.
- Branche Flatpak : `alpha`.
- Référence complète : `app/io.github.icfmp.Bible/x86_64/alpha`.
- Nom de remote suggéré et vérifié : `bible-alpha`.
- Runtime : GNOME 49, distribué séparément par Flathub.

L’URL racine vient de l’API Pages ; le dépôt est sous `alpha/repo`. Les fichiers
`alpha/Bible.flatpakref`, `alpha/bible-alpha.flatpakrepo` et `alpha/bible-alpha.gpg`
sont générés avec cette URL et la véritable clé publique. Une page française
propose l’installation graphique, les sources correspondantes et les releases
de secours. Aucun mécanisme de mise à jour n’est ajouté à l’interface de Bible.

Le workflow réutilise le bundle construit par la CI verte du **même commit** ;
il vérifie run, dépôt, branche main, ascendance, architecture, référence, empreinte
du paquet et `build-info.json`. L’import puis `build-commit-from` changent la
branche de distribution en `alpha` et signent les nouvelles révisions, sans
changer le code applicatif. La provenance distingue commit Git, commit OSTree,
révision du paquet et CI. Les sources de Bible et les archives originales de
SWORD/SWIG, vérifiées par SHA-256, sont proposées avec leurs instructions de
construction ; aucune Bible ni commentaire complet n’est embarqué.

## Publication and storage retention

Application deliveries reuse the bundle from green GNOME CI for the exact
source commit. The workflow checks repository, main ancestry, architecture,
Flatpak identity and bundle SHA-256. A stable dedicated key signs the alpha
commits and summaries. The remote, ref, public flatpakref and signing identity
remain unchanged. Each delivery verifies a fresh public installation and a
subsequent public update with user-data sentinels.

### Corresponding sources on GitHub Releases

The public, **non-numbered technical prerelease**
[alpha-source-archives](https://github.com/icfmp/Bible/releases/tag/alpha-source-archives)
stores one `Bible-<full-source-commit>-sources.tar.gz` asset per distributed
source commit. This is storage, not an application milestone; numbered release
#87 remains paused. No numbered application tag is created or moved.

Historical archives retain their exact bytes and SHA-256 digests. Every initial
upload is downloaded again through its public HTTPS URL and verified byte for
byte before any staged Pages copy is removed. Uploads never overwrite assets.
Later publications validate previously recorded asset IDs, sizes and digests,
refusing replacement or corruption. A failed upload or verification leaves all
local source archives intact and cannot persist/deploy the staged site.

The [source catalogue](https://icfmp.github.io/Bible/alpha/sources.html) lists
all archives and checksums; `alpha/sources.json` provides the same machine-readable
mapping. Current provenance retains `source_archive` and `source_sha256`, adding
`source_url` for the public asset. The landing page links to the current archive
and historical catalogue. **Old direct Pages tarball URLs are retired**; use the
catalogue's Releases URLs. GitHub Pages cannot supply per-file HTTP redirects.
Previously published numbered-release assets are unchanged.

New archives use the compact layout introduced for #95: omit historical GUI
validation output (`docs/captures`, `docs/evidence`, `wiki/images`), retaining
application/build scripts, original icon sources, preferred dependency sources,
licenses, tests and all pinned dependency archives. CI builds the installed
Flatpak from this exact project tar layout. Historical archives are not repacked.

### Active OSTree repository on Pages

Keep the current alpha commit and its **nine immediate parents**, plus complete
object trees reachable from every other ref at the same depth. OSTree's
`prune --refs-only --depth=9` removes only unreachable objects; shared files needed
by retained trees remain. Run `ostree fsck` after pruning. Remove derived static
deltas so obsolete deltas do not independently accumulate; clients fetch normal
signed objects. An older installed client can update directly to the current
alpha even when its original server-side commit has been pruned. Arbitrary
historical downgrades beyond the retained window are no longer promised.

All preparation occurs on a copy. Persistence uses a normal child commit on
`flatpak-alpha-data`, refusing concurrent changes. Its previous Git history is
kept as a recovery copy, including migrated archives and pruned OSTree objects;
no force push or history rewrite occurs. Pages publishes the complete prepared
site. A **200,000,000-byte** total-site guard stops preparation before persistence
or deployment, well below the [1 GB Pages limit](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
This does not remove GitHub's other storage/bandwidth/Actions quotas.

### One-time maintenance and verification

`Maintain alpha distribution storage` is a manual main-only workflow, serialized
with normal alpha publication. It reuses the already published application:
no rebuild, new application commit, signing-key change or numbered release.
Before migration it installs the public alpha, selects the actual #90 commit
and records independent note/preference/resource sentinels. It uploads/verifies
all corresponding sources, prunes the staged repository, checks unchanged
application provenance and signed channel files, then persists and deploys.
After deployment it verifies a fresh signed installation with GTK startup and
an actual update of that older client without changing its data. Numbered
release metadata is compared before and after. Reports, source catalogue,
provenance and the previous data-branch recovery commit are retained in the
`alpha-storage-verification` workflow artifact.

The channel regression workflow also installs a signed test Flatpak, generates
twelve newer revisions, prunes the original server-side commit, and updates the
original client successfully. This tests the full-object fallback, not merely
an update where both commits remain on the server. Automated Xvfb startup is
not manual validation on the client's GNOME desktop.

If a post-deployment public check fails, report that failure; do not claim a
verified migration. The preceding data-branch commit recorded in the artifact
provides the full previous site for recovery through a normal new child commit
and Pages deployment, without moving published application tags or changing
client data.

## Passage depuis un ancien bundle

Les anciens bundles utilisent généralement la branche `master`. Examiner d’abord :

```sh
flatpak list --user --app --columns=application,branch,origin
flatpak info --user --show-ref io.github.icfmp.Bible
flatpak info --user --show-origin io.github.icfmp.Bible
```

Après confirmation que l’installation à remplacer est celle sur `master`, fermer
Bible, puis la désinstaller explicitement **sans supprimer ses données** :

```sh
flatpak uninstall --user io.github.icfmp.Bible//master
```

Ouvrir ensuite le `.flatpakref` public vérifié par le workflow, avec Logiciels
GNOME, ou installer ce fichier téléchargé. Une fois le canal installé :

```sh
flatpak run --user io.github.icfmp.Bible//alpha
flatpak update --user
```

Aucune commande de suppression de profil ni de remote générique n’est exécutée
automatiquement. L’ancien profil n’est pas migré dans cette tâche ; le client
accepte un nouvel essai propre, mais son effacement reste facultatif et manuel.
Les branches d’une même application peuvent partager des données : éviter de
faire fonctionner simultanément une ancienne alpha et le canal alpha.

GNOME Logiciels peut proposer les mises à jour ; leur application automatique
dépend des réglages du poste. Il reste à essayer ce parcours graphique sur le
poste réel. Les métadonnées de boutique AppStream du bundle initial sont encore
sommaires ; les contrôles vérifient son fichier desktop, l’icône et le lancement,
pas une publication sur une boutique.

## Gestion de la clé

Le secret doit rester stable entre les exécutions et accessible uniquement au
workflow de publication de confiance sur main. Aucun secret n’est utilisé dans
les tests de PR de forks. La sauvegarde privée et le certificat de révocation
ne doivent entrer ni dans Git ni dans un artefact public.

Avant expiration, prolonger la clé existante et remettre son export privé dans
le secret, puis publier le certificat public renouvelé. Conserver l’empreinte.
Un changement d’empreinte est refusé par le préparateur : un renouvellement de
clé distincte exige une procédure de transition, signature avec les clés utiles
et mise à jour explicite de la confiance chez les clients ; ne jamais remplacer
le secret par une clé générée à chaque run. En cas de perte/compromission, arrêter
la publication, utiliser la sauvegarde/révocation et documenter la transition.

## Références consultées

- https://docs.flatpak.org/en/latest/hosting-a-repository.html
- https://docs.flatpak.org/en/latest/repositories.html
- [Sources officielles des instructions Flatpak consultées](https://github.com/flatpak/flatpak-docs/tree/1017976c15fe847c48603de9301d873aeb77b197)
- https://github.com/flatpak/flatpak/blob/main/doc/flatpak-build-commit-from.xml
- https://github.com/flatpak/flatpak/blob/main/doc/flatpak-build-update-repo.xml
- https://github.com/actions/upload-pages-artifact
- https://github.com/actions/deploy-pages
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

## Résultats vérifiés de cette branche

[CI réussie](https://github.com/icfmp/Bible/actions/runs/39323977929), commit
`9e96ce9` : huit tests des refus de publication et de conservation des données,
puis intégration Flatpak réelle sur un client neuf.

- Installation depuis le `.flatpakref` du serveur statique de test : commit
  `d1111e8f188c7b08f72615f0fea66cf513157b51e4d0dd6819f5aa1ecacdef33`.
- Lancement de Bible dans le sandbox : **`Bible GTK startup OK`** ; fichier
  desktop, icône, runtime et référence alpha contrôlés.
- `flatpak update --user` : nouveau commit installé
  `4bebd2b8b71ff20c97d221a251b077823a32947e1ae46faae3b641a5871bd879`.
- Origine `bible-alpha`, signature du commit et vérification du résumé activées.
- Résumés `summary` et `summary.idx` altérés : refus par un client distinct sans cache.
- La branche de données conserve les objets antérieurs et l’historique, sans
  publier les fichiers du runner ni les sentinelles privées des tests.

Les messages de portail/accessibilité sous Xvfb et un avertissement d’import du
bundle Flatpak n’ont pas empêché ces assertions. Ils ne valident pas l’intégration
complète à GNOME Logiciels sur un poste réel. Les déploiements Pages et les tests
HTTPS publics ne sont pas exécutés : la configuration propriétaire ci-dessus
reste nécessaire. Ces tests locaux signés ne sont pas présentés comme une
publication publique réussie.
