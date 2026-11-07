"""Assemble verified public test receipts and original GTK PNGs, never profiles."""
from pathlib import Path
import hashlib,html,json,shutil,zipfile

base=Path(__file__).resolve().parent
manifest=json.loads((base/'delivery.json').read_text())
source=manifest['source'];roots={key:base/value['folder'] for key,value in manifest['artifacts'].items()}
signed=roots['signed'];provenance=json.loads((signed/'after-provenance.json').read_text())
assert provenance['source_commit']==source and str(provenance['ci_run'])==str(manifest['ci'])
assert provenance['signing_fingerprint']=='47A17230403EA4953745E6E020EB9FFCCECAFD8F'
assert json.loads((signed/'signed-update.json').read_text())['updated']
assert json.loads((signed/'preservation.json').read_text())['preserved']
assert json.loads((roots['installed']/'candidate-build-info.json').read_text())['commit']==manifest['candidate']
assert json.loads((roots.get('fidelity',roots['installed'])/'candidate-build-info.json').read_text())['commit']==manifest['candidate']
checks=[]
for key,folder in roots.items():
    for p in folder.rglob('alignment.json'):
        d=json.loads(p.read_text());assert d['complete'] and d['preserved'] and d['app_import'].startswith('/app/')
        assert d['renderer']=='GLRenderer'
        if not d['baseline']:assert len(d['resolver'])==294 and d['native_selector_changes']==4
        if key in ('fidelity','installed','signed'):assert d['fidelity_verses']>0
        checks.append(dict(proof=key,report=str(p.relative_to(folder)),language=d['language'],baseline=d['baseline'],
            resolver_vectors=len(d['resolver']),gui_checks=len(d['gui']),gesture_pairs=len(d['gestures']),
            commentary_changes=len(d['commentaries']),fidelity_verse_comparisons=d.get('fidelity_verses',0),
            restored=bool(d.get('restored_session_verified'))))
    for p in folder.rglob('commentary-gestures.json'):
        d=json.loads(p.read_text());assert d['complete'] and len(d['checks'])==30 and len(d['handoffs'])==9 and d['renderer']=='GLRenderer'
        if key=='animations':assert d['animations_enabled']
assert json.loads((signed/'signed-en/alignment.json').read_text())['restored_session_verified']
native=(signed/'signed-native-tests.log').read_text();assert '\nOK\n' in native and 'Ran ' in native
out=base/'release-evidence';assets=base/'alpha26-assets';out.mkdir(exist_ok=True);assets.mkdir(exist_ok=True)
allowed={'alignment.json','commentary-gestures.json','preservation.json','before-provenance.json','after-provenance.json',
    'baseline-provenance.json','candidate-build-info.json','build-info.json','signed-update.json','signed-native-tests.log',
    'before-signature.txt','after-signature.txt','baseline-signature.txt'}
for key,folder in roots.items():
    for p in folder.rglob('*'):
        if not p.is_file() or not (p.suffix=='.png' or p.name in allowed):continue
        target=out/key/p.relative_to(folder);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
(out/'delivery.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'matrix-summary.json').write_text(json.dumps(checks,indent=2)+'\n')
parts=['<!doctype html><meta charset="utf-8"><title>Bible alpha26 GTK evidence</title>',
    '<style>body{font:16px sans-serif;max-width:1300px;margin:2em auto;padding:0 1em}img{max-width:100%;height:auto}figure{margin:1em 0}code{overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1em}table{border-collapse:collapse}td,th{padding:.5em;border:1px solid #aaa;text-align:left}</style>',
    '<h1>Bible alpha.26 — original installed GTK evidence</h1>',
    '<p>Final signed source <code>'+html.escape(source)+'</code>. Unchanged alpha.25 baseline: <code>c7009d0162c0b2b85cc8f99e5b024e17e764bd3e</code>. Candidate checks use <code>'+html.escape(manifest['candidate'])+'</code>; its Git tree matches the final merged source. Diagnostic helper revisions, build/artifact IDs and hashes are recorded in delivery.json.</p>',
    '<p>All PNGs below are unmodified native GTK captures. Linux x86_64, GTK 4.20.4, composited X11/software OpenGL. No customer profile, complete Bible resource, credential or annotation database is included. These checks do not certify GNOME/Wayland or hardware GPUs. See release notes for genuinely unsupported book mappings.</p>',
    '<h2>Before and after — MHC following</h2><p>The baseline shows NFC/LSG with MHC unavailable. The final signed view shows NFC/KJV with the correctly followed MHC range; the comparison translation differs and is explicitly visible.</p><div class="grid">']
featured=[('signed/before-fr/youversion-YV2367-FreSegond1910-before.png','Before: signed alpha.25, NFC/LSG, MHC unavailable'),
    ('signed/signed-fr/youversion-YV2367-MHC-after.png','After: final signed source, NFC/KJV, MHC Genesis 1:1–2')]
for relative,caption in featured:
    assert (out/relative).is_file();safe=html.escape(relative,quote=True)
    parts.append(f'<figure><a href="{safe}"><img src="{safe}" alt="{html.escape(caption,quote=True)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>')
parts.append('</div><h2>Measured test matrices</h2><table><tr><th>Proof/report</th><th>Resolver vectors</th><th>GTK openings</th><th>Wheel pairs</th><th>Verse-body comparisons</th><th>Restart verified</th></tr>')
for d in checks:
    rel=d['proof']+'/'+d['report'];safe=html.escape(rel,quote=True)
    parts.append(f'<tr><td><a href="{safe}">{html.escape(rel)}</a></td><td>{d["resolver_vectors"]}</td><td>{d["gui_checks"]}</td><td>{d["gesture_pairs"]}</td><td>{d["fidelity_verse_comparisons"]}</td><td>{d["restored"]}</td></tr>')
parts.append('</table><h2>Final signed light/dark and French/English views</h2><div class="grid">')
for language in ('fr','en'):
    for p in sorted((out/'signed'/('signed-'+language)).glob('*.png')):
        rel=str(p.relative_to(out));safe=html.escape(rel,quote=True)
        parts.append(f'<figure><a href="{safe}"><img loading="lazy" src="{safe}" alt="{safe}"></a><figcaption>{safe}</figcaption></figure>')
parts.append('</div><h2>All independent native captures</h2><ul>')
for p in sorted(out.rglob('*.png')):
    rel=str(p.relative_to(out));safe=html.escape(rel,quote=True);parts.append(f'<li><a href="{safe}">{safe}</a></li>')
parts.append('</ul><p><a href="delivery.json">Source/build/artifact provenance</a> · <a href="signed/preservation.json">Retained linked data</a> · <a href="SHA256SUMS">File checksums</a></p>')
(out/'overview.html').write_text('\n'.join(parts))
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n' for p in sorted(out.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
with zipfile.ZipFile(assets/'Bible-alpha26-GTK-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(out))
standalone={'NFC-before-MHC.png':featured[0][0],'NFC-after-MHC.png':featured[1][0],
    'NFC-after-light.png':'signed/signed-fr/youversion-YV2367-day-after.png',
    'NFC-after-dark.png':'signed/signed-fr/youversion-YV2367-night-after.png'}
for name,relative in standalone.items():shutil.copyfile(out/relative,assets/name)
shutil.copyfile(out/'delivery.json',assets/'delivery-provenance.json')
(assets/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(assets.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
notes=(base/'release-notes-template.md').read_text()
for key,value in dict(SOURCE=source,CI=manifest['ci'],PUBLICATION=manifest['publication'],REVISION=provenance['packaging_revision'],OSTREE=provenance['flatpak_commit'],SIGNED_RUN=manifest['artifacts']['signed']['run'],ANIMATIONS_RUN=manifest['artifacts']['animations']['run']).items():notes=notes.replace('{{'+key+'}}',str(value))
assert '{{' not in notes
(base/'release-notes.md').write_text(notes)
print(json.dumps(dict(source=source,pngs=len(list(out.rglob('*.png'))),matrices=checks,assets=[p.name for p in assets.iterdir()]),indent=2))
