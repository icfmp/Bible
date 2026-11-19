"""Audit application icon references without importing GTK or starting Bible."""
import ast
import json
from pathlib import Path
import re


def references(root):
    result={};computed=[]
    for path in sorted((Path(root)/'bible').rglob('*')):
        if path.suffix not in ('.py','.ui','.css','.xml'):continue
        text=path.read_text();relative=str(path.relative_to(root))
        for number,line in enumerate(text.splitlines(),1):
            for name in re.findall(r'''["']([a-z][a-z0-9-]*-symbolic(?:-rtl)?)["']''',line):
                result.setdefault(name,[]).append(f'{relative}:{number}')
        if path.suffix=='.py':
            for node in ast.walk(ast.parse(text)):
                if isinstance(node,(ast.JoinedStr,ast.BinOp)) and '-symbolic' in ast.unparse(node):
                    # Current dynamic widgets select from literal names. A new
                    # assembled name requires an explicit, reviewable inventory.
                    computed.append(f'{relative}:{node.lineno}')
    return result,sorted(set(computed))


def main():
    root=Path(__file__).resolve().parents[1]
    used,computed=references(root)
    print(json.dumps(dict(icons=used,unreviewed_computed_names=computed),indent=2))


if __name__=='__main__':main()
