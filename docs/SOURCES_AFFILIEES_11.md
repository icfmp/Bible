# Issue #11 — première tranche : diagnostic des sources

État : **commencée**, pas encore livrée dans l’application. Branche
`feat/11-commentary-sources`. L’alpha.2 conserve son catalogue CrossWire existant.
Aucun fournisseur ni identifiant installé n’est modifié dans cette tranche.

## Mesures réelles

Audit du 19 octobre 2026, commit `3694358`,
[exécution réussie](https://github.com/icfmp/Bible/actions/runs/39317872806).
Le rapport JSON complet est dans l’artefact **issue-11-source-audit** de cette
exécution et dans les notes Git `refs/notes/source-audit` associées au commit.

Le catalogue principal CrossWire contient **429 entrées, dont 41 commentaires**
identifiés par leur pilote ou catégorie. Parmi ces 41 : aucun sans langue,
aucun avec `CipherKey`, aucun avec un pilote hors de la liste déjà prise en charge.
Ces critères ne retirent donc aucun de ces commentaires lors de cet audit.
Cela ne constitue pas une validation de lecture des 41 ouvrages.
Aucun nombre de commentaires supplémentaires Xiphos/AndBible n’est encore annoncé.

Le registre standard officiel indique pour Xiphos :

```text
HTTPPackagePreference=Xiphos|ftp.xiphos.org|/pub/xiphos
FTPSource=Xiphos|ftp.xiphos.org|/pub/xiphos
```

Le wiki officiel donne encore d’autres chemins historiques pour Xiphos et explique
qu’**AndBible Extra** héberge les modules libres de Xiphos, initialement pour
contourner une incompatibilité de transport FTP/HTTPS entre logiciels. Cette
mention du wiki ne prouve ni une URL de catalogue actuelle, ni la présence de
tous les ouvrages Xiphos. Le registre récent et le wiki diffèrent : vérifier les
endpoints réellement disponibles avant de les ajouter à l’application.
Aucun accès protégé ni contrôle technique ne sera contourné.

L’accès au manuel Xiphos a échoué depuis le runner : **`HTTP Error 403: Forbidden`**.
Le wiki, le registre et le catalogue CrossWire ont été accessibles ; le rapport
conserve l’erreur sans abandonner leurs résultats.

## Travail suivant

1. Retrouver les endpoints AndBible Extra dans les sources officielles d’AndBible,
   puis mesurer ses commentaires et ceux des autres sources pertinentes ; lister
   langues, pilotes, chiffrement, doublons et différences avec CrossWire.
2. Définir les fournisseurs stables et leurs chemins séparés de catalogue/paquets.
   Prévoir des résultats partiels avec erreurs visibles et nouvelle tentative.
3. Choisir explicitement une politique de collision : garder les identifiants
   historiques CrossWire et préserver notes, sessions et provenance hors connexion.
   Le nom interne SWORD et l’identité de stockage doivent rester distincts si
   plusieurs sources fournissent un même nom ; aucune migration implicite.
4. Ajouter la provenance et le choix de source dans la bibliothèque, conserver
   les conditions visibles et les contrôles d’archives/compatibilité.
5. Installer réellement un commentaire supplémentaire, vérifier lecture hors
   connexion et suivi de verset, puis produire un paquet de test depuis ce commit.

Ces étapes restent à réaliser ; cette tranche ne clôt pas l’issue #11.
La branche permet la revue prévue par AGENTS.md pour les politiques de sources.
La création automatique des PR est actuellement refusée par le dépôt GitHub
(erreur observée lors de la préparation alpha.2 :
`GitHub Actions is not permitted to create or approve pull requests (createPullRequest)`).

## Reproduire

```sh
python3 -m unittest tests.test_source_audit -v
python3 -m tools.audit_affiliated_sources
```

Les deux tests de l’audit passent : les entrées sans langue, verrouillées ou avec
pilote non pris en charge restent distinguées ; les liens documentés sont résolus
sans transformer un endpoint FTP en miroir HTTPS supposé. L’audit réseau passe
dans GitHub Actions et produit `affiliated-sources-audit.json`. Il ne télécharge
que documentation et métadonnées, aucun texte biblique/commentaire complet.

Sources :
- https://wiki.crosswire.org/Official_and_Affiliated_Module_Repositories
- https://www.crosswire.org/ftpmirror/pub/sword/masterRepoList.conf
- https://www.crosswire.org/ftpmirror/pub/sword/raw/mods.d.tar.gz
- https://xiphos.org/manual/module-manager.html (403 constaté)
