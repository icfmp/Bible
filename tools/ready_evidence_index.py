"""Index unmodified private GTK screenshots; never publish Bible resource files."""
import html
import json
from pathlib import Path
import sys


def main():
    root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
    def read(path):
        try:return json.loads((root/path).read_text())
        except (OSError,ValueError):return {}
    build=read('candidate-build-info.json')
    cases=[
        ('#185 Source notes','source-note-tooltip-day','source-note-popover-night'),
        ('#187 / #188 Search','search-text-1200-day','search-topics-360-night'),
        ('#189 / #196 Study','study-references-day','study-commentaries-night'),
        ('#191 / #194 Reading appearance','appearance-1200-day','appearance-360-night','reading-preferences'),
        ('#192 Chapter headings','youversion-YV21-day-study','youversion-YV21-heading-off'),
        ('#193 Header order','reader-1200-day','reader-360-night'),
        ('#197 Passage picker','passage-1200-day','passage-360-night'),
        ('#198 Selection','selection-day','selection-night'),
        ('#200 / #201 Notes','note-dialog-day','note-workspace-night'),
    ]
    def gallery(label,paths):
        images=[]
        for path in paths:
            if not (root/path).is_file():continue
            safe=html.escape(path,quote=True)
            images.append(f'<figure><a href="{safe}"><img loading="lazy" src="{safe}" alt="{safe}"></a><figcaption>{safe}</figcaption></figure>')
        return '<h2>'+html.escape(label)+'</h2><div class="grid">'+''.join(images)+'</div>'
    checks={name:bool(read(name+'/ready.json').get('complete')) for name in ('alpha24-fr','candidate-fr','candidate-en','candidate-offline')}
    checks.update({name:bool(read(name+'/retention.json').get('complete')) for name in ('retention-fr','retention-en')})
    body='<h1>Ready reading and notes — native GTK evidence</h1><p>Candidate source: <code>'+html.escape(build.get('commit','Not available'))+'</code></p>'
    body+='<p>Unmodified screenshots from real installed Flatpaks, real requested resources, composited X11 and software OpenGL. These are developer checks, not acceptance on the client’s GNOME desktop. Publication is a separate step.</p>'
    body+='<p>Report completion: '+html.escape(json.dumps(checks))+'</p>'
    body+='<p>Download the artifact and open this file locally. Click an image for its original full size. <code>alpha24-fr</code> is before; <code>candidate-fr</code> and <code>candidate-en</code> are after. JSON receipts and test logs are retained alongside the images.</p>'
    for label,files in cases:
        paths=[prefix+'/'+name+'.png' for name in files for prefix in ('alpha24-fr','candidate-fr','candidate-en')]
        body+=gallery(label,paths)
    body+=gallery('Narrow windows with enlarged interface text',[str(p.relative_to(root)) for p in sorted(root.glob('*/quick-note-360-*.png'))]+[str(p.relative_to(root)) for p in sorted(root.glob('*/appearance-360-large-ui-text.png'))])
    body+=gallery('#190 Translation download footers',[str(p.relative_to(root)) for p in sorted(root.glob('*/translation-download-footer-*.png'))])
    body+=gallery('#202 Manual and suggested linked passages',[str(p.relative_to(root)) for p in sorted(root.glob('*/linked-passages-360-*.png'))])
    body+='<h2>#199 Entry-to-first-usable-paint</h2><p>Cold means a fresh application process; OS/font/disk caches were not flushed. Warm means re-entry in that same process. The book stream is recreated normally. Compare alpha and master rows for the same resource/reference on this runner.</p><table><tr><th>Installed branch</th><th>Case</th><th>Entry</th><th>Seconds</th><th>Main-loop max gap (ms)</th></tr>'
    for path in sorted(root.glob('entry-*/entry.json')):
        data=json.loads(path.read_text())
        for entry in data.get('entries',[]):
            values=[path.parent.name,data.get('resource','')+' '+data.get('reference',''),entry['iteration'],f"{entry['first_usable_paint_seconds']:.3f}",f"{entry['max_main_loop_gap_ms']:.1f}"]
            body+='<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in values)+'</tr>'
    body+='</table>'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Native GTK evidence</title><style>body{font:16px system-ui;margin:24px;color:#202020}p{max-width:1100px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}figure{margin:0}img{max-width:100%;height:auto;border:1px solid #888}figcaption{font-size:12px;overflow-wrap:anywhere}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:8px;text-align:left}</style>'+body+'</html>'
    (root/'overview.html').write_text(page)


if __name__=='__main__':main()
