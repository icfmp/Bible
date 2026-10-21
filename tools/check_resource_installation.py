"""Real resource installation and offline restart; disposable TEST profile only."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def wait(predicate,timeout=180):
    from gi.repository import GLib
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        GLib.MainContext.default().iteration(False)
        if predicate():return
        time.sleep(.005)
    raise AssertionError('Resource task did not finish')


def direct(root,name,reference,system):
    import Sword
    manager=Sword.SWMgr(str(root));module=manager.getModule(name)
    key=Sword.VerseKey();key.setVersificationSystem(system);key.setText(reference)
    module.setKey(key);text=module.stripText()
    return text if isinstance(text,str) else text.c_str()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--replay-packages');parser.add_argument('--require-packaged',action='store_true');args=parser.parse_args()
    import bible
    if args.require_packaged:assert bible.__file__.startswith('/app/'),bible.__file__
    from bible.library import Library,catalogue
    from bible.providers import EBIBLE,CROSSWIRE,module_name
    from bible.sword_provider import Reader
    from bible.ui import Application,Window,Gtk
    root=Path(args.profile);library=Library(root/'translations');manifest=root/'resource-check.json'
    app=Application();app.register();Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    window=Window(app,library);window.present()
    try:
        if not args.offline:
            resources=[r for r in catalogue(EBIBLE) if r.language in ('fr','fra','fre')]
            other={r.name:r for r in catalogue(CROSSWIRE)}
            resources.extend(other[name] for name in ('KJV','FreCrampon') if name in other)
            assert len(resources)>=7,'Expected French controls and two additional real resources'
            dialog=window.open_library();dialog._catalogue_requested=True;results=[]
            for resource in resources:
                dialog.resources=[resource];dialog.update_languages();dialog.open_details(None,0)
                if args.replay_packages and resource.provider_id==EBIBLE.id:
                    from unittest.mock import patch
                    payload=(Path(args.replay_packages)/(resource.name+'.zip')).read_bytes()
                    with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(payload)):
                        dialog.install();wait(lambda:not dialog.busy)
                else:dialog.install();wait(lambda:not dialog.busy)
                assert resource.id in library.installed(),(resource.id,dialog.status.get_text())
                assert dialog.installed_state.get_visible() and not dialog.download_button.get_visible()
                assert window.active_tab.navigate(resource.id,'John.3.16')
                reader=window.active_tab.reader
                text=dict(reader.chapter('John.3.16').verses)['John.3.16']
                assert text==direct(library.root/resource.id,resource.name,'John.3.16',reader.versification)
                result=dict(id=resource.id,driver=reader.module.getConfigEntry('ModDrv'),system=reader.versification,
                            version=reader.module.getConfigEntry('Version'),sha256=hashlib.sha256(text.encode()).hexdigest(),
                            installed_ui=True,immediate_reader=True)
                results.append(result);print(json.dumps(result),flush=True)
            dialog.close();manifest.write_text(json.dumps(results,indent=2)+'\n')
        else:
            for result in json.loads(manifest.read_text()):
                name=result['id'];reader=Reader(library.root/name,name)
                assert window.active_tab.navigate(name,'John.3.16')
                text=dict(reader.chapter('John.3.16').verses)['John.3.16']
                assert hashlib.sha256(text.encode()).hexdigest()==result['sha256']
                assert text==direct(library.root/name,module_name(name),'John.3.16',reader.versification)
                print('OFFLINE RESTART PASS',name,reader.versification,flush=True)
    finally:window.close()


if __name__=='__main__':main()
