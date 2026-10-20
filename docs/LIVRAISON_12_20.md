# Lecture, bibliothèque et notes — issues restantes

Le [complément Aa de la #12](APPARENCE_12.md) intègre les décisions actualisées :
Livre/Simple, A−/A+, modes Système/Jour/Nuit, palettes séparées, mise en page
et priorité automatique au contraste élevé, sans perdre les autres travaux.

## Fonctionnement livré dans le code

- **#12 et #15** : commandes de comparaison et Aa dans la Header Bar, icônes
  distinctes Bibliothèque/Mes notes, menu de repli sur petite largeur. Colonne
  centrée, police sérif réglable, interligne et numéros en exposant ; préférences
  locales atomiques séparées des notes. Paragraphes, lignes et titres extraits
  prudemment de l’OSIS/ThML ; repli sur le texte SWORD exact si les mots divergent.
  Aucune lecture audio, aucun surlignage factice. Comparaison d’une seconde Bible
  installée de même versification, empilée si les colonnes seraient trop étroites.
- **#16** : Livres/Historique dans le sélecteur, Livres à l’ouverture. Historique
  indépendant par onglet, limité à 100 passages, conservé à la fermeture. Retour
  sans ajouter de visite, suppression de la suite après une nouvelle navigation.
  Une ressource absente reste dans l’historique avec un message explicite.
  Alt+Gauche/Droite parcourt les visites ; Alt+Page précédente/suivante les chapitres.
- **#18** : téléchargement en haut du sélecteur, près de la version et de Fermer.
  Ouvre la bibliothèque Bibles sans changer le passage.
- **#19** : liste virtualisée Explorer/Installées, catalogue chargé automatiquement,
  actualisation dans l’en-tête, filtres type/langue/source, fiche et retour sans
  perdre les filtres. Recherche de langue par nom localisé, nom natif ou code.
  Babel/CLDR 2.18.0 et ISO 639-3 4.18.0 sont épinglés, disponibles hors connexion ;
  `az` et `azb` restent distincts. Les langues inconnues ne sont pas devinées.
- **#20** : Mes notes occupe la fenêtre principale ; Lecture et ses onglets restent
  vivants. Liste/éditeur côte à côte, navigation entre les deux sur petit écran.
  Labels existants consultables, aperçu, dates locales avec date exacte en
  infobulle, Markdown sécurisé et boutons compacts. Enregistrer/Abandonner/
  Continuer l’édition protègent changement de note, retour et fermeture. Le même
  éditeur et la même gestion des conflits servent aux notes rapides. La base et
  le format des sauvegardes restent inchangés.
- **#13** : SVG 128 unités, symbolique et variante Devel ; exports 32 à 512 pixels.
  Livre bleu, pages ivoire, signet ocre et titre Bible conservés. Les lettres sont
  vectorisées. `python3 tools/export_vector_icons.py` exige Inkscape.
- **#17** : le canal Flatpak signé, ses vérifications et sa CI sont déjà dans le
  snapshot public de main utilisé comme base. Les changements ne remplacent pas
  les préversions existantes. Une publication du canal public reste à vérifier.

## Vérification de ressources réelles

Les captures de `captures/remaining-issues/` montrent GTK/libadwaita sous Xvfb,
avec le module danois du domaine public **DanDetteBiblen**. Une note de démonstration
est explicitement marquée comme donnée de test. Aucun module complet n’est commité.

Le chapitre 1 Corinthiens 15 a été contrôlé sur **DanDetteBiblen** (ThML,
paragraphes présents) et **PorRecebida** (Plain, absence de structure). Pour chacun,
les 58 versets gardent tous leurs mots après retrait des seuls espaces de
présentation. Les deux lecteurs fonctionnent avec `socket.create_connection`
interdit. Sources téléchargées depuis le dépôt public documenté AndBible Extra,
à partir des ZIP originaux ; ce contrôle de lecture ne prouve pas l’accès aux
catalogues CrossWire depuis cet environnement. Les titres et lignes poétiques
sont aussi testés sur des fixtures explicitement synthétiques.

## Essayer

Les dépendances et la commande de lancement sont dans le README. Ouvrir un
passage installé, modifier Aa, activer une comparaison, naviguer puis revenir via
Historique. Créer une note, ouvrir Mes notes, modifier son texte puis choisir
Lecture pour essayer les trois réponses de protection. Réduire à 360 pixels.
Fermer et relancer sans réseau pour vérifier session, préférences et notes.

## Résultats locaux

- Suite complète : **102 tests réussis** sous GTK 4.18/libadwaita 1.7 et SWORD 1.9.
- Interface française : **44 tests réussis** ; fonctionnalités nouvelles :
  **5 tests spécifiques d’apparence réussis**, intégrés à ces suites. Les neuf
  tests précédents d’historique/espaces restent inclus dans la suite complète.
- Interactions natives X11 : clics, clavier, recherche, fermeture du sélecteur,
  navigation en surimpression, onglets indépendants et commandes Aa réussis.
- `actionlint`, compilation Python, analyse JSON/SVG et `git diff --check` réussis.

Ces ensembles se recouvrent et ne doivent pas être additionnés. Des avertissements
GTK de mesure de labels et de dépréciation subsistent ; ils ne font pas échouer
les assertions. Les captures ne remplacent pas une revue visuelle sur le poste cible.

## Limites de validation et publication

L’essai manuel sur le poste GNOME du client reste à effectuer. Les captures Xvfb
ne valident pas GNOME Logiciels ni les portails. App Icon Preview n’est pas installé
ici ; la revue dans cet outil reste à faire, même si les exports et les icônes
symboliques chargées par GTK ont été contrôlés.

Après le redémarrage de l’environnement, aucun identifiant GitHub n’est configuré.
La base est le snapshot public `e001640e5474329637c1a9833ab579af47d01e68`, importé
localement sous le commit `d8fc09e` ; ce dernier n’a pas la même ascendance Git.
Le patch de livraison ne contient que les changements ajoutés à ce snapshot :
le reprendre sur le vrai main avant publication, sans pousser le commit de
snapshot ni forcer l’historique.

L’accès Git renvoie `fatal: could not read Username for 'https://github.com':
terminal prompts disabled`. Le SDK Flathub est également inaccessible :
`URLError: <urlopen error Tunnel connection failed: 403 Forbidden>`.
Aucun nouveau Flatpak ni nouvelle release ne sont annoncés comme publiés ; la CI
GitHub de ces nouveaux changements n’a pas pu être lancée. Les alpha.1 et alpha.2
restent intactes. Les résultats locaux détaillés accompagnent le patch livré.
