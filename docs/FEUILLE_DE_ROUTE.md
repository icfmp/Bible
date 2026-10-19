# Bible — Feuille de route et première mission
Les étapes ci-dessous sont une proposition d'ordre de réalisation. Elles ne réduisent pas le périmètre produit du cahier des charges. Toute modification substantielle doit être signalée.

## Étape 0 — Valider le socle réel
Objectif : lever le risque Python/SWORD/Flatpak avant de développer toute l'interface.
- Lire AGENTS.md et docs/CAHIER_DES_CHARGES.md.
- Inspecter l'environnement disponible et noter les dépendances.
- Choisir des versions stables compatibles de Python, GTK 4, libadwaita et SWORD, en expliquant le choix.
- Éprouver les liaisons Python de SWORD et leur inclusion dans Flatpak.
- Étudier séparément l'API YouVersion et le téléchargement intégral, notamment pour le Semeur ; documenter les possibilités et inconnues. Ne pas laisser cette étude bloquer le prototype CrossWire.
- Étudier les contraintes Windows/macOS, sans prétendre avoir validé ces systèmes depuis un seul environnement Linux.

Livrable : note technique courte, prototype exécutable et instructions reproductibles. Si un élément bloque, fournir l'erreur réelle et une proposition étayée, pas une interface factice.

## Étape 1 — Première livraison utilisable sous GNOME
Périmètre :
- Fenêtre native avec Header Bar, onglets et panneau d'étude escamotable.
- Catalogue minimal réel CrossWire permettant de télécharger une traduction dont l'usage est autorisé.
- Aucun texte biblique complet embarqué.
- Affichage d'un chapitre réel et navigation précédent/suivant.
- Deux passages dans deux onglets indépendants.
- Restauration du dernier passage et des onglets.
- Chaînes d'interface préparées et disponibles en français et anglais.
- Manifest Flatpak et procédure de construction ; produire un paquet de test si l'environnement le permet.
- Tests ciblés de navigation, stockage et chargement ; essai visuel GNOME à organiser.

Acceptation :
1. Sur profil neuf, aucune traduction n'est annoncée installée.
2. Une ressource est téléchargée réellement ; progression et échec sont gérés.
3. Après désactivation du réseau, les chapitres installés restent lisibles.
4. Changer d'onglet retrouve son passage.
5. Fermer puis rouvrir l'application restaure les onglets.
6. Masquer le panneau rend l'espace au lecteur.
7. Le Flatpak démarre sur un poste GNOME cible ; tant que ce test n'est pas fait, le signaler.
8. Les textes affichés sont fidèles à la ressource, sans génération ou remplacement par l'IA.

Commencer par cette étape ; ne pas implémenter toute la feuille de route en une seule tâche.

## Étape 2 — Lecteur complet
- Recherche exacte hors connexion avec index fiable.
- Trois modes de lecture et conservation de l'ancre.
- Affichage configurable des numéros, réglages de texte et copie personnalisable.
- Comparaison de plusieurs traductions, adaptée à la largeur et à la versification.
- Aperçus de renvois, détachement/rattachement d'onglets, restauration des fenêtres.
- Vérifications clavier, accessibilité et hébreu/grec.

## Étape 3 — Étude et annotations
- Catalogue étendu aux types de ressources CrossWire, avec capacités déclarées.
- Commentaires suivant la sélection ; comparaison dédiée de deux commentaires.
- Lexiques, Strong et morphologie quand disponibles.
- Notes Markdown indépendantes de la traduction, labels et vue centrale.
- Surlignages masquables, sauvegarde et restauration des données.
- Ne pas traiter une étape comme terminée si un type de ressource reste non pris en charge sans l'indiquer.

## Étape 4 — Assistance intelligente et sources complémentaires
- Fournisseurs configurés par l'utilisateur ; protection des clés et consentement.
- Suggestions de labels existants.
- Interprétation des demandes naturelles ; exécution par fonctions déterministes.
- Recherche thématique avec passages sourcés et limites annoncées.
- Commande vocale : vérifier accès microphone dans Flatpak, langue et erreurs.
- Connecteur YouVersion et disponibilité du Semeur selon résultats de l'étude ; pas de disponibilité fictive.
- L'explication théologique assistée reste un chantier ultérieur distinct.

## Étape 5 — Distribution et portabilité
- Automatiser les contrôles et la construction Flatpak dans GitHub Actions, si les permissions le permettent.
- Métadonnées AppStream, icône, captures réelles, documentation française et anglaise.
- Choix formel de licence libre compatible avec les dépendances ; distinguer licence du logiciel et licences des contenus.
- Préparer puis soumettre à Flathub une version stabilisée ; ne pas annoncer une publication avant acceptation.
- Construire et tester réellement Windows et macOS ; anticiper signatures et éventuels coûts sans les engager.
- Suivre les défauts restants et fournir un journal des changements.

## Format attendu de chaque livraison
- Ce qui a été réalisé et pourquoi.
- Comment lancer et essayer la version.
- Vérifications exécutées et résultats, séparés des vérifications non réalisées.
- Limites connues et prochain travail recommandé.
- Changements versionnés et relisibles ; ne pas inventer un lien d'artefact ou de publication.

## Texte à donner à Codex pour démarrer
Lis AGENTS.md, docs/CAHIER_DES_CHARGES.md et cette feuille de route. Réalise l'étape 0 puis commence la première livraison GNOME de l'étape 1. Pour ce jalon réversible, suis AGENTS.md : commits vérifiés directement sur main si l'accès le permet ; en cas de refus, signale l'erreur exacte et prépare une pull request relisible. Vérifie réellement Python/SWORD/GTK/Flatpak. Commence par un module CrossWire utilisable pour les essais, sans embarquer de traduction complète. Préserve l'objectif YouVersion/Semeur comme étude séparée et documente les limites. N'ajoute pas d'IA, de synchronisation ou de fonctions hors périmètre à cette première livraison. Rapporte précisément les tests effectués, les blocages et la procédure pour essayer l'application.

