from string import ascii_lowercase

from sqlalchemy.orm import scoped_session

from files.classes.marsey import Marsey

from files.helpers.const import ENABLE_EMOJI

marseys_const : list[str] = []
marseys_const2 : list[str] = []
christian_emojis : tuple = ()

def const_initialize(db: scoped_session):
	_initialize_marseys(db)

def _initialize_marseys(db: scoped_session):
	if not ENABLE_EMOJI: return
	global marseys_const, marseys_const2, christian_emojis
	christian_emojis = (':#marseyjesus:',':#marseyimmaculate:',':#marseymothermary:',
	                    ':#marseyfatherjoseph:',':#gigachadorthodox:',
						':#marseyorthodox:',':#marseyorthodoxpat:')
	marseys_const = [x[0] for x in db.query(Marsey.name)
	                                 .filter(Marsey.name != 'chudsey')
									 .all()]
	marseys_const2 = marseys_const.copy()
	marseys_const2.append('chudsey')
	marseys_const2.extend(ascii_lowercase)
	marseys_const2.extend(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
