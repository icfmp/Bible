"""Verify eBible's actual French identities, package and offline SWORD fidelity."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from bible.library import Library,catalogue
from bible.providers import EBIBLE
from bible.sword_provider import Reader


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--module',default='frajnd2024eb');parser.add_argument('--package')
    parser.add_argument('--screenshot-prefix')
    args=parser.parse_args()
    library=Library(Path(args.profile)/'translations');name='ebible~'+args.module
    if not args.offline:
        resources={r.name:r for r in catalogue(EBIBLE)}
        from bible.catalogue_cache import CatalogueCache
        CatalogueCache(Path(args.profile)/'catalogue-cache').write(EBIBLE,resources.values())
        for code in ('fraLSG1910eb','fraFOB1744eb','francl2022eb','frajnd2024eb','frasbl2022eb'):
            resource=resources[code]
            print(json.dumps(dict(id=resource.id,language=resource.language,license=resource.license,
                                  description=resource.description,versification=resource.versification)),flush=True)
        if name not in library.installed():
            if args.package:
                def downloaded(url,out,progress):
                    assert url==EBIBLE.packages_url+args.module+'.zip'
                    out.write(Path(args.package).read_bytes())
                with patch('bible.library.download',side_effect=downloaded):library.install(resources[args.module])
            else:library.install(resources[args.module])
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline verification')):
        reader=Reader(library.root/name,name)
        chapter=reader.chapter('John.3.16')
        reference,text=next((r,t) for r,t in chapter.verses if r=='John.3.16')
        reader.module.setKey(reader.key(reference));direct=reader.module.stripText()
        direct=direct if isinstance(direct,str) else direct.c_str()
        assert text==direct and 'dieu' in text.casefold() and 'monde' in text.casefold()
        resource=library.resource(name);assert resource.source=='eBible' and resource.language=='fr'
        print(json.dumps(dict(offline=True,id=name,reference=reference,
                              version=reader.module.getConfigEntry('Version'),
                              sha256=hashlib.sha256(text.encode()).hexdigest())),flush=True)
        if args.screenshot_prefix:
            from bible.ui import Application,Window,Gtk
            from tests.test_ui import spin
            from PIL import ImageGrab
            app=Application.get_default() or Application();app.register()
            Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
            window=Window(app,library);window.present()
            try:
                window.active_tab.navigate(name,'John.3.16');spin(lambda:not window.active_tab._restoring_scroll,duration=.3)
                ImageGrab.grab().save(args.screenshot_prefix+'-reader.png')
                dialog=window.open_library();dialog._catalogue_requested=True
                spin(lambda:not dialog.preparing and not dialog._building_rows)
                dialog.language.set_selected(dialog.language.codes.index('fr'));spin(duration=.3)
                ImageGrab.grab().save(args.screenshot_prefix+'-catalogue.png')
                dialog.close()
            finally:window.close()


if __name__=='__main__':main()
