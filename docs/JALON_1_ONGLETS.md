# Jalon 1 — onglets, session et panneau d’étude (issue #3)

Ce document décrit le jalon historique #3. Les parcours ci-dessous tiennent
compte du [sélecteur et des commandes corrigés dans #8–#10](CORRECTIONS_ALPHA_8_10.md).

## Réalisation

Le lecteur utilise `Adw.TabView` et `Adw.TabBar`, avec fermeture et réordonnancement
natifs. Chaque `ReadingTab` conserve son propre lecteur SWORD, sa traduction,
sa référence canonique et sa position relative de défilement. Ouvrir une référence
dans un nouvel onglet conserve le passage de l’onglet d’origine. Changer de
traduction ou naviguer ne modifie que l’onglet actif.

Le catalogue et le transfert résident dans une fenêtre native séparée accessible
par la Header Bar. Le fournisseur CrossWire et la logique d’installation n’ont
pas changé. Une fenêtre de téléchargement fermée pendant le transfert est cachée ;
le transfert continue, et peut être retrouvé en rouvrant Traductions. Son résultat
met à jour les sélecteurs sans remplacer les passages des autres onglets.

`Adw.OverlaySplitView` affiche un état vide explicite pour l’étude. Le panneau
est à droite dans une fenêtre large ; le masquer rend sa largeur au lecteur.
Sous 760 pixels de large, il se superpose au contenu. Il n’affiche aucun faux
commentaire. Sa visibilité est conservée par onglet.

L’interface utilise les mêmes API GTK 4/libadwaita déjà présentes, sans ajout de
dépendance. `OverlaySplitView` et les breakpoints sont disponibles à partir de
libadwaita 1.4 ; le runner Ubuntu utilise une version compatible. Les API ont été
vérifiées par introspection et exécution locale avec libadwaita 1.7.6, GTK 4.18.6
et les bindings réels de SWORD 1.9.0.

## Persistance

Fichier `bible/session.json` sous le répertoire de données XDG ; il est indépendant
des dossiers des traductions. Schéma JSON version 1 : onglets dans l’ordre,
traduction, référence, position relative (0 à 1), visibilité de l’étude et indice
de l’onglet sélectionné. Aucune migration de données préexistantes.

Sauvegarde différée après changement et immédiate à la fermeture, par fichier
temporaire privé (0600), synchronisation puis remplacement atomique. Si le disque
refuse l’écriture, l’ancien fichier reste intact et une erreur est affichée.
La lecture valide le schéma, les noms de traductions, les types et les positions.
Un fichier corrompu ou de version future est conservé et l’enregistrement est
désactivé pour cette fenêtre : aucun remplacement silencieux par une session vide.

Une traduction absente ne supprime ni l’onglet ni sa référence ni sa position.
L’onglet affiche un message et permet de choisir une autre traduction installée.
Les onglets dont les ressources sont présentes restent lisibles hors connexion.
La position est une fraction du défilement ; une taille de fenêtre ou une
traduction différente peut déplacer légèrement le point exact visible.

## Vérifications

Tests automatisés locaux, avec les véritables bibliothèques GTK et SWORD et des
sentinelles de test clairement identifiées :

- Tests CrossWire/stockage/lecteur existants conservés.
- Session : ordre, sélection, positions et traductions absentes ; format futur
  ou corrompu ; valeurs dangereuses ; échec du remplacement atomique.
- GTK sous Xvfb et bus de session : deux passages indépendants ; changement de
  traduction dans un seul onglet ; fermeture ; réordonnancement ; restauration
  après destruction puis création d’une fenêtre ; défilement réellement rétabli,
  y compris le retour manuel en haut après ouverture d’un verset précis.
- Traduction supprimée entre deux ouvertures ; conservation du passage et des
  autres onglets ; session corrompue préservée.
- Mesure de la largeur allouée au lecteur avec et sans panneau ; fenêtre étroite ;
  actions clavier des onglets ; transfert poursuivi après masquage du catalogue.

Résultats locaux : **23 tests réussis** (8 du lecteur et de l’installation,
5 de persistance, 10 GTK). Les 10 tests GTK passent aussi avec `LANGUAGE=fr`.
Compilation syntaxique Python et contrôle du diff réussis.

La pipeline existante exécute automatiquement la suite complète. Elle conserve
le téléchargement réel de KJV et la lecture dans un processus sans réseau. Le
contrôle Flatpak importe aussi les modules de la nouvelle interface dans son
sandbox. Les résultats de CI doivent être consultés sur le commit livré.

## Essayer sur GNOME

```sh
git pull origin main
LANGUAGE=fr /usr/bin/python3 -m bible
```

Avec une traduction téléchargée :

1. Ouvrir la saisie directe (`Ctrl+K`), saisir `Gen.1.1` et valider avec Entrée.
   Créer volontairement un onglet avec `Ctrl+T`, puis y saisir `Gen.2.1`. Vérifier
   que les deux onglets restent distincts ; le sélecteur ne crée pas d’onglet.
2. Faire défiler chaque onglet, changer leur ordre et choisir une autre traduction
   dans l’un si plusieurs sont installées. Vérifier l’indépendance.
3. Basculer Étude par le bouton ou `F9`, redimensionner la fenêtre, puis masquer le
   panneau. Vérifier la place rendue au texte et le message d’état vide.
4. Fermer puis relancer sans réseau : vérifier onglets, traduction, passage,
   sélection et positions. Fermer un onglet avec `Ctrl+W`, en créer avec `Ctrl+T`.
5. Sur un profil de test, application fermée, déplacer temporairement le dossier
   d’une traduction hors de `bible/translations`. Relancer et vérifier que son
   onglet affiche l’absence de traduction sans perdre sa référence. Remettre le
   dossier et relancer pour retrouver la lecture.

Aucun essai manuel sur le poste GNOME du client n’est annoncé. Xvfb et les
mesures d’allocation ne remplacent pas ce contrôle du bureau réel. Pas encore de
fenêtres détachables, commentaires, notes, IA, comparaison ou lecture paginée.
Les limites du texte brut et des références SWORD décrites dans le prototype
restent applicables.
