"""Reviewed, deliberately partial FR/EN topic names; identifiers are source facts."""
import re
import unicodedata
from .i18n import LANGUAGE

# Source identifier, conventional French name, French/English search synonyms.
VOCABULARY=(
 ('forgiveness of sins','Pardon des péchés','pardon reçu; Dieu pardonne; forgiveness received; absolution'),
 ('forgiving others','Pardonner aux autres','pardon accordé; pardonner son prochain; forgiveness given'),
 ('reconciliation','Réconciliation','pardon; se réconcilier; restore relationships'),
 ('grace','Grâce','faveur; don gratuit'),
 ('faith','Foi','croire; croyance; belief'),
 ('hope','Espérance','espoir; attendre avec confiance'),
 ('love','Amour','aimer; charité; charity'),
 ('fear','Peur','crainte; effroi; afraid'),
 ('fear of the lord','Crainte du Seigneur','respect de Dieu; fear of God'),
 ('anxiety','Inquiétude','anxiété; souci; soucis; worry; worries'),
 ('peace','Paix','apaisement; paix intérieure; peaceful'),
 ('justice','Justice','équité; juste; fairness'),
 ('anger','Colère','irritation; fureur; angry'),
 ('wisdom','Sagesse','discernement; wise'),
 ('mercy','Miséricorde','compassion; pitié; merciful'),
 ('prayer','Prière','prier; prieres; pray'),
 ('suffering','Souffrance','souffrir; épreuve; douleur; pain'),
 ('work','Travail','travailler; métier; working'),
 ('death','Mort','mourir; décès; dying'),
 ('resurrection','Résurrection','ressusciter; relever des morts'),
 ('salvation','Salut','sauver; sauvé; saved'),
 ('healing','Guérison','guérir; maladie; heal'),
 ('trust','Confiance','se confier; faire confiance; trusting'),
 ('gratitude','Reconnaissance','gratitude; remerciement; thankful'),
 ('family','Famille','foyer; familial'),
 ('marriage','Mariage','époux; épouse; couple; married'),
 ('children','Enfants','enfant; parentalité; child'),
 ('friendship','Amitié','ami; amis; amie; friends'),
 ('repentance','Repentance','se repentir; regret; repentir'),
 ('temptation','Tentation','tenter; tenté; tempted'),
 ('humility','Humilité','humble; modestie'),
 ('patience','Patience','patient; persévérer; waiting'),
 ('generosity','Générosité','donner; partage; generous'),
 ('honesty','Honnêteté','intégrité; honnête; honest'),
 ('truth','Vérité','vrai; véridique; truthful'),
 ('courage','Courage','bravoure; hardiesse; brave'),
 ('joy','Joie','réjouir; réjouissance; joyful'),
 ('rest','Repos','se reposer; fatigue; resting'),
 ('creation','Création','créateur; créer; creator'),
 ('holy spirit','Saint-Esprit','Esprit saint; esprit de Dieu; spirit of God'),
 ('baptism','Baptême','baptiser; baptisé; baptized'),
 ('eternal life','Vie éternelle','éternité; eternal'),
 ('poverty','Pauvreté','pauvre; pauvres; poor'),
 ('wealth','Richesse','riche; argent; rich'),
 ('hospitality','Hospitalité','accueil; accueillir; welcome'),
 ('loneliness','Solitude','seul; isolement; lonely'),
 ('self control','Maîtrise de soi','tempérance; se maîtriser; self-control'),
 ('obedience','Obéissance','obéir; obéissant; obey'),
 ('faithfulness','Fidélité','fidèle; loyauté; faithful'),
 ('forgiveness','Pardon','pardonner; forgiving; forgiveness'),
)


def normalized(value):
    return ' '.join(re.findall(r'\w+', ''.join(c for c in unicodedata.normalize('NFKD',value.casefold())
                                            if not unicodedata.combining(c)),re.UNICODE))


def title(entry,language=None):return entry[1] if (language or LANGUAGE)=='fr' else entry[0].capitalize()


def suggestions(query,language=None,limit=50):
    words=normalized(query).split();ranked=[]
    for entry in VOCABULARY:
        terms=[normalized(t) for t in (entry[0],entry[1],*entry[2].split(';'))]
        if all(any(word==token or token.startswith(word) for term in terms for token in term.split()) for word in words):
            exact=normalized(query) in terms
            ranked.append((not exact,normalized(title(entry,language)),entry))
    return [entry for _,_,entry in sorted(ranked)[:limit]]
