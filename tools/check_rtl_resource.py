"""Verify an installed RTL SWORD resource in an isolated, offline GTK profile.

Usage: python -m tools.check_rtl_resource PROFILE RESOURCE OUTPUT.json
Requires ImageMagick for the screenshot. Does not download or modify the profile.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch
from bible.library import Library
from bible.session import Session,SessionStore,TabState
from tests.test_ui import spin


def main():
    profile,name,output=sys.argv[1:]
    resource_root=Path(profile).resolve()/'translations'/name
    assert resource_root.is_dir()
    from bible.ui import Application,Window,Gtk
    import gi
    gi.require_version('GdkX11','4.0')
    from gi.repository import GdkX11  # register X11 surface methods
    app=Application();app.register()
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);(root/'translations').mkdir()
        (root/'translations'/name).symlink_to(resource_root,target_is_directory=True)
        SessionStore(root/'session.json').save(Session([TabState(name,'John.1.1')]))
        with patch('socket.create_connection',side_effect=AssertionError('offline')),patch('urllib.request.urlopen',side_effect=AssertionError('offline')):
            window=Window(app,Library(root/'translations'));window.present();window.set_default_size(1180,780)
            try:
                tab=window.active_tab;spin(lambda:not tab._restoring_scroll,duration=.3)
                assert tab.reader.rtl
                assert tab.text.get_direction()==Gtk.TextDirection.RTL
                assert tab.text.get_justification()==Gtk.Justification.RIGHT
                assert window.get_direction()!=Gtk.TextDirection.RTL
                normalize=lambda text:re.sub(r'\s+','',text)
                buffer=tab.text.get_buffer();checks=[]
                for reference,text in tab.current.verses:
                    first,last=tab._verse_ranges[reference];body=tab._marker_ends[reference]
                    actual=buffer.get_text(buffer.get_iter_at_offset(body),buffer.get_iter_at_offset(last),False)
                    assert normalize(actual)==normalize(text),reference
                    checks.append({'reference':reference,'sha256_words':hashlib.sha256(normalize(text).encode()).hexdigest()})
                resource=window.library.resource(name)
                result={'resource':name,'source':resource.source,'license':resource.license,'conditions':resource.conditions,
                        'resource_direction':'RTL','native_reader_direction':'RTL','native_justification':'RIGHT',
                        'interface_direction':'LTR','network':'Python sockets and URL requests denied during checks',
                        'chapter':tab.current.reference,'verses':checks,'display':'GTK/Xvfb; not a manual GNOME/Wayland test'}
                target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-window',str(window.get_surface().get_xid()),str(target.with_suffix('.png'))],check=True)
                target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                print(f'PASS: {len(checks)} verses match native SWORD; RTL reader, LTR interface; offline Python; {target}')
            finally:window.close()


if __name__=='__main__':main()
