"""Check the two exact, reference-only publisher indexes in the native patch."""
import json
from pathlib import Path
from bible.youversion_osis import BOOKS

ROOT=Path(__file__).resolve().parents[2]


def header():
    lines=['// Bible contributors, GPL-2.0-only. Reference bounds only; no Scripture text.',
        '// Generated from the audited edition indexes; see matching JSON provenance.',
        '#ifndef CANON_YOUVERSION_H','#define CANON_YOUVERSION_H','SWORD_NAMESPACE_START']
    for edition in (93,131):
        data=json.loads((ROOT/f'bible/versification_data/YouVersion{edition}.json').read_text())
        assert list(data['canon'])==list(BOOKS.values())
        assert data['explicit_only'] is True and not data['forward'] and not data['reverse']
        values=[n for chapters in data['canon'].values() for n in chapters]
        assert len(values)==1189 and all(type(n)is int and 1<=n<=300 for n in values)
        lines.append(f'static int vm_youversion{edition}[] = {{')
        lines.extend('    '+', '.join(map(str,values[i:i+25]))+',' for i in range(0,len(values),25));lines.append('};')
    return '\n'.join([*lines,'SWORD_NAMESPACE_END','#endif'])+'\n'


def check():
    patch=(ROOT/'packaging/sword-osis-fidelity.patch').read_text()
    section=patch.split('+++ b/include/canon_youversion.h\n',1)[1]
    actual='\n'.join(line[1:] for line in section.splitlines()[1:] if line.startswith('+'))+'\n'
    assert actual==header(),'Native source bounds differ from the audited indexes'


if __name__=='__main__':check();print('Publisher index tables reproduce the native patch')
