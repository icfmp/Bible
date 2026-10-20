# Livraison et état des issues jusqu’à la #25

Périmètre : issues ouvertes #12, #13, #15 à #20, #24 et #25, après relecture de
leurs descriptions GitHub. Les livraisons déjà réalisées et le correctif de
revue `2cd501c` sont conservés. Les #26, #27 et #28 restent hors de cette tâche.
Une issue ouverte n’est pas présentée comme clôturée lorsqu’une validation ou
une opération d’administration manque encore.

## État par issue

| Issue | Code disponible dans la livraison | Validation ou action restante |
| --- | --- | --- |
| #12 | Header Bar, comparaison réelle, Aa immédiat, polices hors connexion, modes et palettes jour/nuit, contraste élevé système, numéros indépendants | Essai manuel GNOME/Flatpak et lecteur d’écran. Le surlignage est suivi dans #27, sans commande factice. |
| #13 | SVG sur canevas GNOME, symbolique, Devel, exports transparents 32–512, installation desktop/Flatpak | Revue dans App Icon Preview à 32/64 et sur le bureau GNOME : outil indisponible, archive officielle refusée en HTTP 403. |
| #15 | Colonne et titres, structure OSIS/ThML conservatrice, ancrages et fidélité ; direction RTL explicite dans les lecteurs Bible, comparaison et commentaire | Validation visuelle finale sur le poste cible ; un source sans structure ne reçoit aucun titre inventé. |
| #16 | Historique indépendant par onglet, maximum 100 visites, restauration, retour/avance sans ajout, Livres par défaut | Validation utilisateur et CI du commit final. |
| #17 | Canal signé, workflows, contrôles de publication et script de configuration déjà sur main | Activation administrateur, publication et installation/mise à jour publiques HTTPS entre deux révisions non réalisées ; API GitHub refusée ici. |
| #18 | Téléchargement dans l’en-tête du sélecteur, accès contextuel au catalogue Bibles | Essai utilisateur du prochain Flatpak. |
| #19 | Explorer/Installées, catalogue automatique, filtres et détail avec retour, recherche des langues CLDR/ISO et attributions hors connexion | Essai utilisateur des catalogues et installations ; accès réseau variable selon les fournisseurs. |
| #20 | Mes notes dans la fenêtre principale, liste/éditeur adaptatifs, labels et filtres, Markdown sûr, sauvegarde/abandon et protection des brouillons | Essai utilisateur de consultation et d’édition. |
| #24 | Plein écran natif demandé, livre paginé à une/deux pages, Bible/commentaire, ancrage interne, notes après clic corrigées, sortie et reprise | Plein écran effectif GNOME/Wayland et paquet CI à essayer ; commentaire rendu avec les paragraphes dépouillés SWORD, format riche limité. Aide manuelle Ne pas déranger ; automatisation suivie dans #28. |
| #25 | Entrées continues et plages natives SWORD, suivi automatique bidirectionnel, priorités utilisateur, glissements prolongés corrigés | Essai GNOME/pavé tactile physique/accessibilité ; l’interface présente un commentaire à la fois. |

Les numéros absents de cette liste ne correspondent pas à une nouvelle issue
ouverte à développer dans ce périmètre ; les anciennes réalisations ne sont
pas recommencées. La PR #23 reste la livraison à publier/fusionner après CI.

## Compléments réalisés

### Sens de lecture des ressources

La direction native de SWORD est exposée une seule fois par le fournisseur,
avec prise en charge du caractère retourné par les bindings SWIG. Elle est
appliquée à la vue biblique ordinaire, à la comparaison et au commentaire, ainsi
qu’au lecteur paginé existant. Le texte RTL est aligné à droite ; le titre de
chapitre conserve son centrage. Revenir à une ressource LTR rétablit la direction
et l’alignement. L’interface française/anglaise et ses commandes restent LTR.
Aucun texte ni référence n’est modifié par cette présentation.

### Défilement par barre native

Un nouveau scénario X11 a reproduit une perte de suivi pendant un glissement
prolongé : GestureClick cessait sa reconnaissance dès que la pression devenait
un glissement, puis le délai d’intention utilisateur expirait. Le contrôleur
observe désormais les mouvements réels du pointeur avec le bouton enfoncé pour
renouveler cette intention. Le simple survol ne change pas le panneau pilote.
Le déplacement programmatique d’un panneau suiveur ne simule aucun événement.

Le scénario vérifie la molette dans les deux panneaux et deux glissements de
plus de 1,5 seconde. Le suivi est contrôlé pendant chaque étape, pas seulement
après le relâchement. Une longue entrée garde sa véritable plage ; ni parcours
proportionnel des versets, ni visites artificielles dans l’historique.

## Blocages vérifiés

### #17 — activation du canal alpha

La commande `python3 -m tools.setup_alpha_channel` a été retentée. Elle échoue
dès la première requête, avant création de clé ou modification du dépôt :

```text
Get "https://api.github.com/repos/icfmp/Bible/contents/.github/workflows/alpha-channel.yml?ref=main": Forbidden
```

Le code de configuration est déjà livré. L’opération restante exige un poste
fiable avec `gh` authentifié en administrateur du dépôt, après CI verte sur main :

```sh
python3 -m tools.setup_alpha_channel
```

Le workflow doit ensuite prouver l’installation depuis le `.flatpakref` public,
puis `flatpak update --user` entre deux révisions signées. Aucun canal public
ni lien d’installation hypothétique n’est annoncé. Les bundles existants restent
une solution de secours ; aucune donnée personnelle n’est effacée.

### #13 — outil App Icon Preview

La source indiquée par le manifeste Flathub officiel a été essayée :
`https://gitlab.gnome.org/World/design/app-icon-preview/-/releases/3.5.1/downloads/app-icon-preview-3.5.1.tar.xz`.
Résultat : `curl: (22) The requested URL returned error: 403`.
La vérification dans cet outil n’est donc pas revendiquée. Les captures GTK et
exports déjà fournis restent des preuves distinctes ; ils ne remplacent pas
App Icon Preview ni une revue visuelle sur le bureau cible.

## Essayer

Appliquer le patch de livraison sur la base publique indiquée dans son bilan,
puis laisser GitHub Actions vérifier et construire le Flatpak. Pour un essai
natif avec les dépendances du README : `/usr/bin/python3 -m bible`.

Ouvrir une Bible et un commentaire installés, essayer Aa, comparaison, historique,
Bibliothèque et Mes notes. Faire défiler chaque panneau à la molette puis faire
glisser longuement sa barre : il doit guider l’autre sans ajouter de visites.
Avec une ressource hébraïque RTL, contrôler le sens du texte puis revenir à une
ressource LTR. F11 ouvre l’immersion ; F10 révèle ses commandes ; Échap ferme
le menu puis quitte. Vérifier une note créée après clic sur chacune des deux
pages et la copie exacte après changement de taille 64 → 24.

Les essais Xvfb n’attestent pas GNOME Logiciels, le compositeur Wayland, un pavé
tactile physique ni le lecteur d’écran. Le test manuel sur le poste GNOME reste
à effectuer. Aucun nouveau Flatpak local ni nouvelle release n’est annoncé.

## Résultats réellement exécutés sur ce complément

- **118 tests complets réussis** et **60 tests français réussis** ; groupes
  recouvrants, y compris les correctifs de revue #23 et les nouveaux essais RTL.
- Scénarios X11 français réussis : commandes Aa, sélecteur et onglets ; F11,
  pages, F10 et Échap ; molette dans les deux panneaux, survol sans changement
  de pilote et deux glissements prolongés avec suivi pendant le mouvement.
- La régression du glissement a été reproduite avant correction. Après correction,
  la Bible traverse Genèse 1:2 à 1:8 durant le glissement ; le commentaire reste
  neuf étapes sur sa plage native Genèse 1:2–3 puis passe à son entrée suivante.
  Les références viennent des fixtures synthétiques, pas d’un corpus inventé
  présenté comme une traduction réelle. Le test attend l’entrée actuellement
  visible pendant le chargement progressif, plutôt qu’une position périmée.
- **51 versets réels de Jean 1 (HebNTFD)** relus dans GTK hors connexion Python,
  tous identiques aux mots du texte natif SWORD après retrait des seuls espaces
  de présentation. Direction RTL et alignement à droite contrôlés dans le lecteur,
  interface LTR préservée. Licence déclarée : Public Domain, source AndBible Extra.
- Compilation Python, `actionlint` et `git diff --check` réussis.

[Empreintes des versets et attribution](captures/through-25/hebrew-offline.json),
[capture réelle GTK/Xvfb](captures/through-25/hebrew-offline.png).
Aucun module complet n’est joint. L’interdiction des requêtes Python de ce
contrôle ne constitue pas une isolation réseau du système d’exploitation.
Des avertissements GTK de mesure, dépréciations et ResourceWarning SQLite
subsistent dans la suite sans échec d’assertion.

La CI distante de ce nouveau complément et sa construction Flatpak doivent être
exécutées après publication par le product manager. Les résultats locaux ne sont
pas présentés comme une CI GitHub verte. Aucun ancien tag/release n’est modifié.
