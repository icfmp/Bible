"""Assemble only existing, verified native captures and public receipts."""
from pathlib import Path
import hashlib,html,json,shutil,zipfile
base=Path('/tmp/bible-ready-benchmark');core=base/'final-installed-proof';signed=base/'final-renderer-update';out=base/'release-evidence-v25';assets=base/'alpha25-assets'
receipt=json.loads((base/'final-delivery-receipt.json').read_text());source=receipt['source'];assert source=='c7009d0162c0b2b85cc8f99e5b024e17e764bd3e'
assert json.loads((signed/'preservation.json').read_text())['preserved']
assert json.loads((signed/'signed-update.json').read_text())['updated']
assert json.loads((signed/'after-provenance.json').read_text())['source_commit']==source
assert json.loads((core/'candidate-build-info.json').read_text())['commit']=='2a19acaca475cfadc99696205b6ab144b7a7ed49'
files={}
def copy(p,relative):
 q=out/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);files[str(relative)]=hashlib.sha256(p.read_bytes()).hexdigest()
allowed={'ready.json','retention.json','entry.json','candidate-build-info.json','overview.html','installed-tests-fr.log','installed-tests-en.log','alpha24-signature.txt'}
for p in core.rglob('*'):
 if p.is_file() and (p.suffix=='.png' or p.name in allowed):copy(p,p.relative_to(core))
for name in ('runtime-standard-icons.json','before-provenance.json','after-provenance.json','signed-update.json','preservation.json','current-signed-combined.json','candidate-signed-combined.json','candidate-signed-single.json','candidate-signed-comparison.json','candidate-signed-study.json'):
 p=signed/name
 if p.exists():copy(p,Path('final-signed')/name)
paths=[]
for language in ('fr','en'):
 p=signed/f'final-signed-ready-{language}.log';text=p.read_text();assert 'Ran 27 tests' in text and '\nOK\n' in text;copy(p,Path('final-signed')/p.name)
 folder=signed/f'signed-selection-{language}';x=json.loads((folder/'retention.json').read_text())
 assert x['complete'] and x['app_import'].startswith('/app/') and x['renderer']=='GLRenderer' and x['action_icon']=='accessories-dictionary-symbolic'
 assert x['checks']['native_study_divider_drag_both_directions']
 assert x['app_action_sha256']=='9b332fa1ba1efdd355beae6f334c0944b61b9410be81758820bcc487da80a668'
 copy(folder/'retention.json',Path('final-signed')/folder.name/'retention.json')
 for mode in ('day','night'):
  path=Path('final-signed')/folder.name/f'selection-final-{mode}.png';copy(folder/f'selection-final-{mode}.png',path);paths.append(str(path))
copy(base/'final-delivery-receipt.json',Path('final-delivery-receipt.json'))
copy(base/'memory-validation.json',Path('memory-validation.json'))
page=(out/'overview.html').read_text()
intro='<h2>Final installed signed alpha — '+source+'</h2><p>The full corpus below was captured on source 2a19acaca475cfadc99696205b6ab144b7a7ed49. Later application changes are the original-text icon name (PR217) and the native Linux OpenGL default (PR229); explicit renderer overrides are preserved. All 27 dedicated Ready/link/pagination cases passed again in French and English on the final signed alpha. These four original screenshots show its final standard dictionary symbol. Other interface components in the corpus are unchanged. Receipts and file hashes distinguish both tested sources.</p><div class="grid">'
for p in paths:
 safe=html.escape(p,quote=True);intro+=f'<figure><a href="{safe}"><img src="{safe}" alt="Final signed selection {safe}"></a><figcaption>{safe}</figcaption></figure>'
intro+='</div>'
page=page.replace('<h1>Ready reading and notes — native GTK evidence</h1>','<h1>Ready reading and notes — native GTK evidence</h1>'+intro)
page=page.replace('<h2>#198 Selection</h2>','<h2>#198 Earlier corpus toolbar, before final standard-symbol change</h2>').replace('<h2>#198 Selection scrolled into view</h2>','<h2>#198 Earlier corpus selection, before final standard-symbol change</h2>')
(out/'overview.html').write_text(page)
files.pop('overview.html',None)
provenance={'full_gui_source':'2a19acaca475cfadc99696205b6ab144b7a7ed49','full_gui_run':42258008846,'full_gui_artifact':13524031815,'full_gui_artifact_sha256':'000e8db3fc8d6fac6b5edfaf360c9655f0b8b5000a1e817e0696aaeda69168c4','final_source':source,'final_signed_run':receipt['update'],'final_delta':'One original-text icon and assertions, plus Linux GSK OpenGL default and rendering documentation; verified by final-delivery-receipt.json','original_capture_files':files,'unmodified_pngs':True}
(out/'evidence-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(out/'README.txt').write_text('Bible alpha25 native GTK developer evidence\n\nExtract this ZIP and open overview.html. Original PNG pixels are unmodified. The full corpus is from source 2a19acaca475cfadc99696205b6ab144b7a7ed49; later changes are one icon name and the Linux native OpenGL default (the corpus already used OpenGL). Final signed source '+source+' passed the 27 dedicated acceptance cases in each language, and its current selection screenshots and retained-update receipts are under final-signed/. JSON and file hashes record both versions.\n\nBefore: alpha24-fr. Corpus after: candidate-fr/candidate-en. Final selection: final-signed/signed-selection-fr and -en. GTK4.20.4, composited X11/software OpenGL, real requested resources and retained isolated developer data. No customer profile, complete Bible module, credential or SQLite database is included. This is developer verification, not acceptance on the client GNOME/Wayland/hardware GPU desktop. See release notes for limitations.\n')
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n' for p in sorted(out.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
assets.mkdir(exist_ok=True);zpath=assets/'Bible-alpha25-GTK-evidence.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(out))
for mode,label in (('day','light'),('night','dark')):
 for folder,stage in (('alpha24-fr','before'),('candidate-fr','after')):shutil.copyfile(core/folder/f'note-dialog-{mode}.png',assets/f'GTK-notes-{stage}-{label}.png')
shutil.copyfile(base/'final-delivery-receipt.json',assets/'delivery-provenance.json')
(assets/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(assets.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print('Prepared final assets:',[(p.name,p.stat().st_size) for p in sorted(assets.iterdir())]);print('Native PNGs:',len(list(out.rglob('*.png'))))
