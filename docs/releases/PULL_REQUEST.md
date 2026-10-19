Préparer la première préversion Linux x86_64 `0.1.0-alpha.1` demandée par le client.

Le workflow de publication relance les contrôles et construit le Flatpak sur le
commit étiqueté. Il joint le paquet, sa somme SHA-256, les sources correspondantes
et les sources des dépendances compilées, puis vérifie les fichiers téléchargés
avant de rendre publique la release marquée Pre-release.

Les notes sont en français et expliquent l’installation graphique sous GNOME,
les fonctions, les limites et le signalement des problèmes. L’essai manuel sur
le poste GNOME du client reste à effectuer. Le client a autorisé GPL-2.0-only pour Bible, après lecture des notices SWORD
1.9.0. La licence et les notices des dépendances sont incluses dans le paquet.
