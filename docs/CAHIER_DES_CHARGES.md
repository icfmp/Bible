# Bible — Cahier des charges produit
Cadrage initial : 18 octobre 2026, complété par les décisions alpha du 19 octobre 2026. Développement en cours ; ce document distingue les objectifs produit des fonctions effectivement livrées.

## 1. Intention
Bible est un logiciel libre de lecture et d'étude biblique pour le grand public, y compris les personnes sans connaissances techniques. Il doit permettre aussi bien la lecture quotidienne que l'étude approfondie. Ce n'est pas un gestionnaire personnel ni un logiciel réservé aux pasteurs.

Le client définit les usages et valide les livraisons ; le product manager prépare les choix et critères ; l'agent de développement réalise et vérifie les étapes. Ne pas présenter les propositions techniques comme des fonctionnalités déjà réalisées.

## 2. Plateformes et distribution
- Application native GNOME, avec Header Bar : priorité absolue à Linux/GNOME et à une intégration soignée.
- Compatibilité visée : Linux, Windows et macOS. Aucune version mobile.
- Interface française et anglaise dès la première version.
- Code public sur GitHub : https://github.com/icfmp/Bible
- Paquet Flatpak dès les premières livraisons ; soumission à Flathub après stabilisation. L'acceptation n'est pas garantie.
- Logiciel libre sous GNU GPL version 2 uniquement (`GPL-2.0-only`), choix autorisé par le client pour la préversion 0.1.0-alpha.1 après examen de SWORD. Les dépendances et les contenus conservent leurs propres licences.
- Orientation technique proposée : Python, GTK 4, libadwaita, SQLite et moteur SWORD. Vérifier le packaging et la portabilité ; tout changement de pile majeur doit être expliqué avant réalisation.
- L'ancienne maquette conçue pour Xiphos est une inspiration fonctionnelle ; aucun ancien code n'est à reprendre. Sa copie n'est pas encore dans ce dépôt.

## 3. Bibliothèque et téléchargements
### Décisions
- Aucune traduction complète préembarquée dans l'application.
- L'utilisateur choisit les traductions dans un catalogue et les télécharge pour les conserver localement.
- Téléchargement simple et rapide : fonction centrale, pas un supplément.
- Lecture et recherche exacte entièrement hors connexion une fois le téléchargement terminé.
- CrossWire : accès aux traductions et aux différents types de ressources disponibles dans les dépôts compatibles, notamment commentaires, dictionnaires et ouvrages.
- Présentation grand public par langue et type ; les termes techniques tels que module et dépôt restent dans les réglages avancés si nécessaires.
- Bible du Semeur souhaitée comme proposition au premier lancement.
- Bible.com / YouVersion : objectif d'accès aux traductions et de téléchargement pour usage hors connexion.
- Pas d'import manuel de fichiers : exclu du périmètre, y compris SWORD, USFM, OSIS, EPUB et PDF.

### Points à résoudre explicitement
Le client souhaite une capacité de téléchargement à l'initiative de chaque utilisateur et considère que celui-ci doit vérifier ses droits. Il a envisagé une récupération des pages si nécessaire. Cette demande ne constitue ni une preuve de permission donnée par les fournisseurs ni une validation juridique.

Évaluer d'abord les API et les modalités officielles d'accès. Distinguer accès à un passage, cache et téléchargement intégral persistant. Ne pas promettre le Semeur hors connexion avant d'avoir vérifié les possibilités techniques et les conditions applicables. L'achat d'un exemplaire ne doit pas être présenté comme une autorisation générale d'extraction depuis un autre service. Documenter les blocages et les solutions possibles ; ne pas cacher l'abandon de cet objectif.

### Critères proposés
Afficher progression et erreurs compréhensibles ; permettre annulation et reprise ou nouvelle tentative. Vérifier l'intégrité avant de déclarer une ressource installée. Préserver les notes lors d'une suppression ou mise à jour de traduction. Mesurer le temps réel d'installation sur des modules représentatifs, sans inventer de promesse chiffrée avant essai.

## 4. Lecture et navigation
- Sélection facile du livre, du chapitre, du passage et de la traduction.
- Décision alpha des issues #9–#10 : depuis le titre de la Header Bar, ouvrir une grande surface arrondie avec recherche et liste des livres à gauche (groupes Ancien/Nouveau Testament selon la ressource), nom du livre et grille de chapitres à droite. Noms dans la langue de l’interface, livre/chapitre actifs marqués et visibles. Sur petite largeur, adapter les deux zones en conservant leur accès.
- Le livre puis le chapitre modifient directement l’onglet actif, sans boutons de confirmation ni choix de destination. Le verset et la traduction restent accessibles discrètement ; aucun choix de verset n’est obligatoire pour ouvrir un chapitre. Ctrl+T et l’action dédiée créent les onglets ; le sélecteur n’en crée jamais. Ne pas inventer d’introductions.
- Deux chevrons circulaires restent visibles à mi-hauteur de la zone biblique, ancrés à ses bords et hors du texte grâce à des marges. Leur position ne dépend ni du défilement ni du panneau d’étude ; désactiver le sens sans destination réelle. Préserver les autres onglets, le focus clavier, le contraste et les noms accessibles français/anglais.
- Recherche ou saisie directe d'une référence.
- Trois modes mémorisés :
  1. Défilement continu traversant les chapitres.
  2. Défilement limité au chapitre, puis boutons précédent/suivant.
  3. Pagination comme une liseuse EPUB, selon la taille de fenêtre et la typographie, indépendante des limites des chapitres.
- Changer de mode conserve une ancre de lecture.
- Taille de caractères et présentation confortables ; priorité à la lisibilité.
- Décision #12 du 20 octobre : un panneau Aa natif compact avec aperçu immédiat,
  sans Appliquer. Dans l’ordre : Livre/Simple avec aperçu de police, A−/valeur/A+
  jusqu’aux très gros caractères, mode Système/Jour/Nuit, quatre palettes nommées
  Blanc/Papier (sépia)/Gris sombre/Noir. Le choix de jour et celui de nuit sont
  mémorisés séparément ; sélectionner une palette ne désactive pas le suivi système.
- Mise en page repliable : interligne Serré/Normal/Aéré et colonne Étroite/Normale/
  Large ; rétablir les valeurs par défaut sans toucher aux données. Réglages locaux
  communs aux onglets ; commentaires cohérents, ancrage et sélection préservés.
- Suivre les notifications natives libadwaita clair/sombre et contraste élevé.
  Le contraste élevé prend temporairement priorité sur les palettes décoratives,
  avec une explication dans Aa ; restaurer ensuite les choix personnels. Conserver
  police/taille/interligne et références. Les composants natifs suivent Adwaita,
  les couleurs personnalisées restent limitées aux lecteurs. Aucun réglage de
  contraste élevé supplémentaire, horaire ni géolocalisation.
- Polices hors connexion, licences conservées et repli pour les écritures non
  couvertes. Contrôler palette, liens, numéros, sélection, focus et commandes.
  Le test système sur GNOME/Flatpak et lecteur d’écran demeure distinct des tests
  automatisés. Les modes de défilement/pagination restent un chantier séparé.
- Trois interrupteurs indépendants et mémorisés : afficher les surlignages, les numéros de chapitre, les numéros de verset.
- Masquer n'efface rien. Références et actions restent utilisables quand les numéros sont invisibles.
- Surlignages en plusieurs couleurs ; accès centralisé aux passages surlignés retenu comme proposition de présentation, à vérifier en maquette.
- Signets non prioritaires et exclus de la première version.

## 5. Onglets, fenêtres et session
- Plusieurs passages ouverts dans des onglets ; fonction indispensable.
- Chaque onglet conserve passage, position, traductions affichées et état des outils d'étude.
- Ouvrir un passage dans un nouvel onglet sans perdre la lecture actuelle.
- Onglets détachables dans des fenêtres indépendantes et rattachables ; utilisation sur plusieurs écrans.
- Restaurer la session : fenêtres, onglets, positions, traductions, outils et visibilité des panneaux.
- Adapter la restauration si un écran ou une ressource manque.
- Un renvoi biblique affiche d'abord un aperçu avec possibilité d'ouverture dans un nouvel onglet.

## 6. Comparaison et outils d'étude
### Traductions
- Plus de deux traductions possibles si la présentation reste lisible.
- Colonnes synchronisées sur le passage, avec largeur minimale confortable.
- Si l'espace manque, proposer un sélecteur pour les traductions supplémentaires au lieu de comprimer toutes les colonnes.
- Maquette et essai nécessaires pour valider ce comportement ; pas de nombre fixe de colonnes imposé à toutes les fenêtres.
- Gérer explicitement les différences de canon et de versification. Ne pas supposer qu'un numéro de verset correspond partout au même passage.

### Ressources
- Panneau d'étude escamotable par un bouton dans la Header Bar ; lecture simple avec panneau caché.
- Le commentaire suit automatiquement le verset sélectionné.
- Sans entrée correspondante, indiquer l'absence de commentaire ; ne pas conserver un contenu trompeur provenant du verset précédent.
- Plusieurs commentaires ouverts, accessibles par onglets ou sélecteur.
- Comparaison dédiée : passage au-dessus, deux commentaires côte à côte dans un espace élargi ; chacun défile indépendamment mais suit le même passage.
- Petite fenêtre : un commentaire visible à la fois.
- Clic sur un mot : définition, Strong et morphologie quand les ressources fournissent effectivement ces données. Cela peut aussi concerner une traduction liée aux mots originaux.
- L'hébreu, le grec, les diacritiques et le sens d'écriture doivent être vérifiés.

## 7. Notes et labels
- Notes liées à un verset ou à un passage, indépendantes de la traduction et de la langue affichée.
- Conserver la traduction d'origine comme information de contexte, sans limiter la visibilité de la note.
- Markdown avec mise en forme légère ; boutons simples pour gras, italique, listes et liens.
- Vue centrale « Mes notes » : toutes les notes, référence et aperçu ; recherche dans le contenu ; tri par date ou ordre biblique ; ouverture de la note avec son passage.
- Indicateur dans le texte pour les passages annotés.
- Labels libres, plusieurs par note ; autocomplétion des labels existants.
- Filtrer les notes par labels et combiner avec la recherche.
- IA facultative : proposer des labels d'après la note en privilégiant ceux qui existent ; validation par l'utilisateur ; ne pas multiplier les synonymes.
- Préserver les notes et labels indépendamment des fichiers téléchargés ; prévoir migrations et sauvegarde/restauration simples.
- Pas de serveur propre, pas de compte Bible obligatoire, pas de synchronisation dans la première version.

## 8. Copie
Un bouton Copier et trois options indépendantes :
- Inclure les numéros de versets.
- Inclure la référence.
- Inclure le nom de la traduction.

Toutes les combinaisons sont possibles, notamment texte seul. Mémoriser les choix pour copier ensuite en un clic. Les options de copie sont indépendantes des options d'affichage. Copier un ou plusieurs versets avec une mise en forme propre.

## 9. Recherche, commandes naturelles et voix
- Une entrée compréhensible pour chercher et naviguer en langage naturel.
- Exemples : « Ouvre Jean, chapitres 1 à 3 », « Trouve les versets contenant grâce ou pardon », « Trouve les passages sur le pardon », « Compare avec le Semeur ».
- Distinguer recherche exacte dans le corpus sélectionné et recherche thématique par sens.
- Recherche exacte : résultats vérifiables et exhaustifs dans le périmètre annoncé.
- Recherche thématique : afficher les véritables textes et références ; ne pas promettre l'exhaustivité.
- L'IA peut interpréter une demande, mais les références, citations et actions doivent être validées par l'application.
- Bouton de commande vocale souhaité. Même logique que la saisie ; clarifier seulement les ambiguïtés utiles. Détails du fournisseur de transcription à étudier.
- Le fonctionnement classique de lecture, navigation et recherche exacte reste disponible sans IA et hors connexion.
- Les fonctions IA en ligne nécessitent la connexion et la configuration utilisateur ; ne pas les annoncer comme disponibles hors connexion.

## 10. Configuration IA
- Chaque utilisateur choisit et configure son fournisseur, avec sa propre clé API si nécessaire.
- Aucun coût d'IA pris en charge par le porteur du projet.
- Configuration simple, test de connexion, explication de la facturation par le fournisseur.
- Stockage sécurisé des clés ; pas de clés dans Git, les journaux, les notes ou les sauvegardes ordinaires.
- Consentement explicite avant l'envoi de notes à un fournisseur ; expliquer ce qui est transmis.
- Fournisseurs et modèles exacts à sélectionner techniquement ; ne pas imposer un unique service sans décision explicite.
- Explication biblique par IA : évolution future à explorer, pas exigence de première version.
- Piste pour cette évolution : l'utilisateur choisit les commentaires sources ; distinguer Bible, citations des commentaires et synthèse ; citations ouvrables ; rendre visibles les désaccords et les limites.
- Public de différentes traditions chrétiennes : ne pas imposer silencieusement une interprétation confessionnelle, ni prétendre à une neutralité sans présupposés.

## 11. Exclusions et qualité
- Liste de prière définitivement exclue.
- Plans de lecture : éventualité future, hors périmètre actuel.
- Pas de tâches, rappels, objectifs quotidiens ou suivi d'habitudes.
- Pas de version mobile ; pas d'import manuel ; pas de synchronisation initiale.
- Navigation au clavier, contraste, zoom, libellés accessibles, thèmes clair/sombre et fenêtre redimensionnable.
- Téléchargements, indexation et appels réseau ne doivent pas bloquer l'interface.
- Les données téléchargées, notes Markdown et réponses IA sont des données non fiables : rendu et actions à encadrer.
- Ne jamais présenter une fonction simulée ou une capture comme une intégration fonctionnelle.
- Vérifier la fidélité des textes, paragraphes, notes de traduction et références ; aucune paraphrase IA dans le texte biblique affiché.

## 12. Références de départ à vérifier lors de l'implémentation
- GNOME HIG : https://developer.gnome.org/hig/
- PyGObject : https://pygobject.gnome.org/
- CrossWire : https://www.crosswire.org/sword/
- YouVersion : https://developers.youversion.com/
- Flathub : https://docs.flathub.org/

Ces références orientent l'étude technique ; leur présence ne signifie pas qu'une intégration ou une permission a été validée.


## Complément de réalisation — lecture #24 et suivi #25

La branche de livraison ajoute un mode immersif paginé pour la Bible et le
commentaire actif, avec ancre interne au verset/à l’entrée, ainsi que la lecture
continue des entrées et leur suivi automatique dans les deux sens. Les clés,
liens et limites proviennent de SWORD. Les entrées absentes et les différences
de versification ne sont pas compensées par des correspondances inventées.
Le prototype conserve un commentaire visible à la fois.

Voir [le guide et ses limites](LECTURE_IMMERSIVE_24_25.md). Ces changements sont
vérifiés localement ; ils ne constituent pas une nouvelle release Flatpak
publiée ni un essai manuel GNOME. La suspension automatique des notifications
n’est pas annoncée : le repli d’aide manuelle prévu par #24 est utilisé.
