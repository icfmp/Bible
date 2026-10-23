"""Curated conventional French names; preserve all publisher names as source data."""
from .i18n import LANGUAGE

FRENCH={
 'Jerusalem':'Jérusalem','Emmaus':'Emmaüs','Nod':'Nod','Babylon':'Babylone',
 'Bethlehem':'Bethléem','Bethany':'Béthanie','Bethphage':'Bethphagé','Nazareth':'Nazareth',
 'Capernaum':'Capernaüm','Galilee':'Galilée','Sea of Galilee':'Lac de Galilée',
 'Sea of Tiberias':'Lac de Tibériade','Jordan':'Jourdain','Jordan River':'Jourdain',
 'Jericho':'Jéricho','Gibeon':'Gabaon','Ai':'Aï','Hebron':'Hébron','Canaan':'Canaan',
 'Egypt':'Égypte','Assyria':'Assyrie','Syria':'Syrie','Damascus':'Damas',
 'Antioch':'Antioche','Tarsus':'Tarse','Ephesus':'Éphèse','Corinth':'Corinthe',
 'Athens':'Athènes','Rome':'Rome','Thessalonica':'Thessalonique','Philippi':'Philippes',
 'Colossae':'Colosses','Patmos':'Patmos','Smyrna':'Smyrne','Pergamum':'Pergame',
 'Thyatira':'Thyatire','Sardis':'Sardes','Laodicea':'Laodicée','Samaria':'Samarie',
 'Judea':'Judée','Tyre':'Tyr','Sidon':'Sidon','Gaza':'Gaza','Ashkelon':'Askalon',
 'Joppa':'Joppé','Caesarea':'Césarée','Caesarea Philippi':'Césarée de Philippe',
 'Mount Mizar':'Mont Mitsear','Mount Hermon':'Mont Hermon','Mount Zion':'Mont Sion',
 'Mount of Olives':'Mont des Oliviers','Mount Carmel':'Mont Carmel','Mount Sinai':'Mont Sinaï',
 'Sinai':'Sinaï','Horeb':'Horeb','Red Sea':'Mer Rouge','Salt Sea':'Mer Morte',
 'Dead Sea':'Mer Morte','Mediterranean Sea':'Mer Méditerranée','Nile':'Nil',
 'Euphrates':'Euphrate','Tigris':'Tigre','Eden':'Éden','Zion':'Sion',
 'Ziklag':'Tsiklag','Nineveh':'Ninive','Bethel':'Béthel','Beersheba':'Beer-Schéba',
 'Shechem':'Sichem','Shiloh':'Silo','Berea':'Bérée','Macedonia':'Macédoine',
 'Asia':'Asie','Cappadocia':'Cappadoce','Galatia':'Galatie','Cyprus':'Chypre',
 'Crete':'Crète','Malta':'Malte','Cyrene':'Cyrène','Libya':'Libye','Arabia':'Arabie',
 'Persia':'Perse','Ur':'Ur','Haran':'Charan','Ramah':'Rama','Gethsemane':'Gethsémané'}


def place_name(name):
    if not LANGUAGE.startswith('fr'):return name
    base,space,number=name.rpartition(' ')
    if space and number.isdigit():return FRENCH.get(base,base)+space+number
    return FRENCH.get(name,name)
