# Catalogue CrossWire — issue #4

## Choisir et retrouver ses conditions

Ouvrir **Traductions** avec Ctrl+L, charger le catalogue, choisir une langue et
chercher un titre ou un identifiant. La recherche ignore les accents et la casse.
Les noms usuels de langues sont traduits ; les codes des autres langues restent
visibles plutôt que d’inventer une traduction.

La fiche présente le titre, la langue, la source et son URL, la licence brute,
les conditions et les attributions transmises par le fournisseur. Le bouton
Télécharger agit sur la traduction sélectionnée après filtrage. Les champs
inconnus restent explicites. Une licence autre que GPL/domaine public ne fait
plus disparaître la traduction. La disponibilité technique ne donne pas des
droits de redistribution, et les conditions affichées doivent être consultées.

Les ressources chiffrées sont signalées avec téléchargement désactivé. La
présence de `CipherKey`, même vide, suffit : une valeur vide ne signifie pas
que le texte est librement lisible. Aucun achat, récupération de clé,
déchiffrement ni contournement n’est implémenté. Un format non pris en charge
est signalé si la source le classe comme texte biblique.

Après installation, cocher **Traductions installées** pour retrouver les fiches
sans réseau ni chargement du catalogue. Les configurations originales restent
sur disque ; les champs légaux répétés sont conservés. Cela fonctionne aussi
avec les installations réalisées avant cette livraison, sans migration de leurs
fichiers ni changement de session. La provenance des nouvelles installations
est également enregistrée dans `.source.json`, à côté de leur configuration.

## Sources et mécanismes examinés

Sources officielles consultées depuis GitHub Actions, car le proxy local refuse
CrossWire et YouVersion :

- [Catalogue principal](https://www.crosswire.org/ftpmirror/pub/sword/raw/mods.d.tar.gz)
- [Registre des dépôts](https://www.crosswire.org/ftpmirror/pub/sword/masterRepoList.conf)
- [Configuration SWORD](https://wiki.crosswire.org/DevTools:conf_Files)
- [Vue d’ensemble YouVersion](https://developers.youversion.com/)
- [Utilisation de l’API](https://developers.youversion.com/api-usage)
- [Référence de l’API](https://developers.youversion.com/api)

Le registre annonce notamment CrossWire, Beta, Attic, Wycliffe, Bible.org,
eBible.org, Xiphos et Deutsche Bibelgesellschaft, avec des transports et chemins
distincts. Cette application utilise le **dépôt principal stable CrossWire** ;
l’accès aux archives et conditions des autres dépôts n’est pas validé. Ils ne
sont donc pas annoncés comme des sources installables. Aucun miroir ajouté
silencieusement, dépôt arbitraire ni import manuel.

Le catalogue `mods.d.tar.gz` fournit les configurations ; l’installation
utilise l’archive officielle `packages/rawzip/<identifiant>.zip`. Les licences
observées comprennent GPL, domaine public, Creative Commons, GFDL, permissions
accordées à CrossWire et distributions non commerciales. La fiche rapporte les
conditions, sans les réinterpréter en autorisation générale.

Les contrôles d’installation restent indépendants des licences : HTTPS,
identité, taille bornée, refus des traversées de chemins/liens et doublons,
contrôle CRC par lecture ZIP, DataPath contenu dans les ressources, pilote Bible
pris en charge, absence de chiffrement et lecture SWORD réelle avant publication
atomique. La licence, les conditions et la description de contexte du paquet
sont comparées à celles du catalogue sélectionné : en cas de changement, il
faut recharger le catalogue avant de télécharger. Un échec ne marque rien comme
installé et laisse les installations précédentes intactes. Il ne s’agit pas
d’une preuve de signature cryptographique de l’éditeur.

Le premier passage est découvert dans les index réels, sans imposer Genèse 1.
La navigation conserve les différences de canon, versification et versets
absents introduites dans l’issue #5.

## Français et Semeur

Le catalogue principal contient notamment `FreBA` (Bible Annotée), `FreBDM1707`
(Martin 1707), `FreBDM1744` (Martin 1744) et `FreLXXGiguet`. Pour Martin 1707,
CrossWire déclare « Copyrighted; Permission to distribute granted to CrossWire ».
L’attribution indique Philippe Lacombe ; la copie et le partage sont déclarés
possibles à condition de conserver la traduction et de citer
https://sites.google.com/view/martin1707. Ces conditions sont affichées dans
l’application et conservées avec la ressource. Ce n’est pas une autorisation
attribuée au projet par une simple étiquette de licence.

Le test réseau vise **FreBDM1707**, avec repli sur FreBA si cette première entrée
n’existe plus dans le catalogue, puis KJV comme contrôle anglais. Il ne livre
aucun texte biblique dans Git ou le Flatpak.

Le Semeur n’est pas déclaré disponible dans l’application. La recherche dans
les métadonnées du dépôt stable ne prouve pas son absence de tous les dépôts
SWORD ni de tous les services autorisés.

YouVersion documente désormais une API REST officielle pour les passages et
les métadonnées. L’application doit être enregistrée pour obtenir une App Key,
transmise dans l’en-tête `X-YVP-App-Key`. Les versions accessibles dépendent des
accords de licence acceptés. La liste `all_available` peut aussi inclure des
versions auxquelles l’application n’a pas accès : présence dans une liste et
permission de lecture sont donc distinctes. Aucune clé n’a été créée ni utilisée
pour ce projet. La disponibilité du Semeur pour cette application, les droits
de cache et le téléchargement intégral persistant n’ont pas été établis. Un
endpoint de consultation de passages ne suffit pas à les prouver. La démarche
suivante est un enregistrement officiel puis l’examen des licences/permissions
avec le fournisseur ; aucun connecteur ni extraction de pages n’est ajouté ici.

## Vérifications et essai

37 tests locaux passent avec SWORD 1.9, GTK 4.18 et libadwaita 1.7 sous Xvfb,
avec tests d’interface en français et anglais. Les fixtures sont des modules
RawText réels contenant des sentinelles de test. Elles couvrent les licences
hors de l’ancienne liste, les conditions répétées, le refus des paquets chiffrés,
le changement de conditions, le filtrage langue/recherche, les attributions hors
connexion et les ressources NT seules.

La CI teste les vrais téléchargements français et anglais, leur fidélité verse
par verset à SWORD et leur réouverture dans un processus avec réseau isolé.
Elle construit aussi le Flatpak GNOME 49. Les résultats effectifs de chaque
exécution sont visibles dans GitHub Actions ; les tests locaux ne prouvent pas
le téléchargement ni le build Flatpak.

Pour essayer : mettre à jour le dépôt, lancer `LANGUAGE=fr /usr/bin/python3 -m bible`,
ouvrir Ctrl+L, charger le catalogue, choisir Français, rechercher Martin et lire
la fiche avant de télécharger. Ouvrir Jean 3:16 depuis le titre central. Couper
le réseau, fermer puis relancer : vérifier le texte et retrouver les conditions
dans **Traductions installées**. L’essai manuel sur poste GNOME reste à faire ;
aucun test Windows/macOS ni publication Flathub n’est revendiqué.
