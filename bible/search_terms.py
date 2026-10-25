"""Word/phrase normalization and exact source-offset highlighting."""
import re
import unicodedata

LATIN_LANGUAGES={'en','fr','de','es','pt','it','la','nl','ro','ca'}


def normalized(value,language='und',offsets=False):
    latin=language.split('-')[0] in LATIN_LANGUAGES
    characters=[];positions=[]
    for index,char in enumerate(value):
        for part in unicodedata.normalize('NFD',char.casefold()) if latin else char.casefold():
            if latin and unicodedata.combining(part):continue
            if part.isalnum() or unicodedata.combining(part):
                characters.append(part);positions.append(index)
            elif characters and characters[-1]!=' ':
                characters.append(' ');positions.append(index)
    result=''.join(characters)
    return (result,positions) if offsets else result


def terms(query,language='und'):
    # Quoted phrases are contiguous; unquoted words are ANDed in any order.
    if query.count('"')%2:raise ValueError('Close the quoted phrase before searching.')
    parts=[phrase or word for phrase,word in re.findall(r'"([^"]*)"|([^\s"]+)',query)]
    result=[normalized(p,language).strip() for p in parts]
    result=[p for p in result if p]
    if not result:raise ValueError('Enter a word or phrase.')
    return tuple(dict.fromkeys(result))


def match_ranges(text,query,language='und'):
    value,offsets=normalized(text,language,True);ranges=[]
    for term in terms(query,language):
        for match in re.finditer(r'(?<!\w)'+re.escape(term)+r'(?!\w)',value):
            if match.end():ranges.append((offsets[match.start()],offsets[match.end()-1]+1))
    return tuple(sorted(set(ranges)))
