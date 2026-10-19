# Vérification de 0.1.0-alpha.1

Préversion publiée le 19 octobre 2026 :
https://github.com/icfmp/Bible/releases/tag/0.1.0-alpha.1

- Release GitHub 417477427 : `draft=false`, `prerelease=true`, vérifié par API
  depuis GitHub Actions et par la page publique marquée « Pre-release ».
- Étiquette et sources de l’application : `3325a912effd65c776885cf722052bc57e468d41`.
  L’étiquette n’a pas été déplacée pendant la reprise de publication.
- Workflow de reprise : https://github.com/icfmp/Bible/actions/runs/39282134761
  Le paramètre `source_ref: 0.1.0-alpha.1` impose le même commit aux deux jobs
  de vérification/construction et au checkout utilisé pour préparer les sources.
- Code de publication corrigé : `ce186ba42f537684c6798bf6421ca5740439d8dd`,
  enregistré séparément comme `publisher_commit` dans `provenance.json`.
  Les corrections de publication ne modifient ni `bible/` ni le manifeste du paquet.

## Résultats réellement observés

- Localement : 66 tests réussis sous Xvfb avec le cache accessible en écriture ;
  28 tests d’interface en français réussis avec le rendu Cairo sous Xvfb.
- Le journal CI du job `verification / prerequisites` confirme les 28 tests
  français (`Ran 28 tests in 11.574s`, `OK`), puis cinq contrôles CrossWire `PASS` :
  trois Bibles et deux commentaires, téléchargements réels, fidélité SWORD,
  attribution et réouverture hors connexion dans un espace réseau isolé.
  La suite générale précède la suite française dans ce même job.
- Le workflow construit le Flatpak, l’installe et charge SWORD et l’interface
  depuis le paquet installé. Le job de publication dépend de la réussite des
  deux jobs de vérification. Son rapport final indique `PUBLICATION_STATUS: success`.
- Les quatre fichiers de release ont été téléchargés depuis leurs URL publiques.
  `sha256sum --ignore-missing -c SHA256SUMS` confirme les trois fichiers listés.
- L’archive des sources a été ouverte : le commentaire PAX de `Bible-source.tar`
  contient le commit exact ci-dessus, les fichiers `LICENSE` et
  `THIRD_PARTY_NOTICES.md` sont présents, et les archives originales SWORD/SWIG
  correspondent aux SHA-256 épinglés dans le manifeste.

SHA-256 du Flatpak Linux x86_64 :

```text
91dddac2f7e3b3209862731e80fc9df46fbb016db07ce9234c7ddd2fc075706e
```

## Incidents et limites de vérification

- L’API GitHub depuis l’environnement local refuse les requêtes :
  `Get "https://api.github.com/repos/icfmp/Bible/releases": Forbidden`.
  La publication autorisée a donc été exécutée par GitHub Actions.
- La recherche du brouillon par étiquette a échoué avec
  `gh: Not Found (HTTP 404)`. La reprise utilise son identifiant ; elle a remplacé
  ses fichiers, vérifié leurs sommes après téléchargement, puis publié la release.
- L’ouverture de la PR demandée par les consignes du dépôt est refusée :
  `pull request create failed: GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)`.
  Les changements restent sur la branche `release/0.1.0-alpha.1`, sans fusion dans main.
- Les métadonnées publiques et l’API des nouveaux workflows continuent d’afficher
  `queued`, malgré les journaux terminés, les artefacts et la publication constatés.
  Il ne faut donc pas interpréter ce rapport comme l’observation d’un statut
  global GitHub « vert ». Les résultats ci-dessus proviennent des commandes,
  des journaux téléchargés et des fichiers effectivement contrôlés.
- La récupération directe du journal Flatpak a rencontré
  `gh: HTTP 503`, code `ServerBusy`, message `Egress is over the account limit.`.
  Le journal des tests et celui de publication ont pu être récupérés. Le contrôle
  du paquet et la dépendance de publication ont été vérifiés comme décrit plus haut.
- Les premiers essais locaux ont échoué faute de `xvfb-run` dans le PATH et de
  bindings SWORD ; les dépendances déjà préparées dans `/tmp` ont été retrouvées.
  Avec le cache initial non accessible en écriture, deux tests ont échoué par
  `AssertionError: GTK layout/task did not settle`. Après configuration du cache,
  la suite de 66 tests passe. Le parcours français a ensuite signalé une fois
  `AssertionError: 170 not greater than or equal to 340` ; le test ciblé puis les
  28 tests français passent avec le rendu Cairo. Aucune correction applicative
  n’a été introduite pour masquer ces résultats.

**L’essai manuel sur notre poste GNOME reste à effectuer**, notamment l’ouverture
graphique du Flatpak dans Logiciels, les portails de fichiers et l’usage réel
au clavier/lecteur d’écran. Aucune acceptation Flathub n’est annoncée.
