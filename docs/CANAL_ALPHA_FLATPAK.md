# Canal alpha Flatpak — issue #17

## État réel de cette livraison

**Préparé et testé sur dépôt statique local ; pas encore publié sur Pages.**
Branche `feat/17-flatpak-alpha-channel`, à ouvrir en PR par le product manager.
Le test installe le véritable paquet alpha.2 depuis un `.flatpakref` servi par un
dépôt OSTree signé, lance son interface GTK, signe une seconde révision, puis
vérifie que `flatpak update --user` installe son nouveau commit. Les vérifications
GPG des commits et résumés restent activées ; un client neuf refuse un résumé
altéré. Les deux révisions contrôlées ont le même code applicatif `c2792c1`, avec
messages de commits OSTree distincts : ce test vérifie une mise à jour de paquet,
pas une nouvelle fonction de Bible. La clé de ce test est éphémère, jamais publiée
comme clé du canal réel.

L’inspection GitHub a constaté :

- `has_pages: false` ; lecture de Pages : **`gh: Not Found (HTTP 404)`**.
- Secret `BIBLE_FLATPAK_GPG_KEY` indisponible.
- API de configuration des secrets, depuis Actions :
  **`gh: Resource not accessible by integration (HTTP 403)`**.

Aucune ancienne page n’est écrasée, aucune clé privée n’est versionnée ni jointe
aux artefacts. Alpha.1 et alpha.2 restent les solutions de secours publiées.
**Aucune URL d’installation publique de ce canal n’est encore annoncée vérifiée.**
La validation HTTPS publique entre deux révisions et l’essai GNOME du client
restent à effectuer après activation.

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

## Déploiements et conservation

Après fusion, toute réussite du workflow **Vérifier le socle GNOME** sur main
peut publier le canal. Le déclenchement manuel de secours demande l’identifiant
numérique d’une CI verte sur main. Une CI de fork/branche non fusionnée, un
artefact changé ou un commit antérieur aux corrections est refusé.

Une seule publication peut s’exécuter à la fois. L’ascendance du dernier commit
source empêche les retours en arrière si les CI terminent dans le désordre.
La branche de données `flatpak-alpha-data` conserve les objets, deltas et sources
déjà publiés ; une modification concurrente est refusée avant de pousser. Le
travail se fait sur une copie et Pages déploie un artefact complet. L’échec d’une
préparation ou d’un déploiement garde le dernier site servi ; un échec de contrôle
après déploiement est rapporté et ne doit pas être présenté comme une validation.

Chaque publication signe deux révisions contrôlées du même code vérifié :
publication de la première, installation depuis son URL HTTPS publique sur un
client de validation neuf, publication de la seconde, puis `flatpak update` sur
ce même client et comparaison des commits installés. Les preuves publiques sont
conservées dans `alpha-public-verification`. Les clés privées restent uniquement
dans le secret et un dossier temporaire du runner, nettoyé même en cas d’échec.

Les deltas statiques complets et incrémentaux sont générés. Les anciens objets
ne sont pas supprimés automatiquement ; les clients anciens peuvent encore
récupérer les objets nécessaires. Le site est limité à **512 Mio**, sous la limite
Pages de 1 Go : dépasser ce seuil interrompt la nouvelle publication, sans
supprimer le dernier dépôt. Une rétention plus élaborée demandera une revue
explicite. Le canal alpha reste soumis aux quotas de stockage, bande passante
et exécution GitHub ; il ne constitue pas une soumission à Flathub.

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
