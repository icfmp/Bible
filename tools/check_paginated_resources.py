"""Offline fidelity/GUI checks on previously installed, explicitly chosen resources.

Usage: python -m tools.check_paginated_resources PROFILE BIBLE COMMENTARY OUTPUT
No download is performed. OUTPUT records checks actually executed under GTK.
"""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from unittest.mock import patch

from bible.library import Library
from bible.paged_sources import BiblePages, CommentaryPages
from bible.pagination import paginate
from bible.preferences import ReadingPreferences
from bible.session import Session, SessionStore, TabState
from bible.sword_provider import Reader, CommentaryReader
from tests.test_ui import spin


def main():
    directory,bible,commentary,output=sys.argv[1:]
    from bible.ui import Application,Window,Gtk
    library=Library(Path(directory)/'translations')
    reader=Reader(library.root/bible,bible)
    comments=CommentaryReader(library.root/commentary,commentary)
    app=Application();app.register();widget=Gtk.TextView()
    result={'source_conditions':{name:{'source':library.resource(name).source,'license':library.resource(name).license,'conditions':library.resource(name).conditions} for name in (bible,commentary)},'network':'Python socket connections and URL downloads forbidden during checks','bible':bible,'commentary':commentary,'checks':[]}
    with patch('socket.create_connection',side_effect=AssertionError('offline')),patch('urllib.request.urlopen',side_effect=AssertionError('offline')):
        for source,keys in [(BiblePages(reader,library.resource(bible)),['John.1','John.2']),
                            (CommentaryPages(comments,library.resource(commentary)),[comments.index.locate('John.1.1'),comments.index.locate('John.1.19')])]:
            for key in keys:
                assert key is not None
                for size in (19,64):
                    doc=source.document(key,ReadingPreferences(size=size))
                    plan=paginate(widget,doc,ReadingPreferences(size=size),360,500)
                    assert ''.join(doc.text[p.start:p.end] for p in plan.pages)==doc.text
                    if source.kind=='commentary':assert doc.text==comments.index.text(key)
                    result['checks'].append({'kind':source.kind,'key':str(key),'size':size,'pages':len(plan.pages),'characters':len(doc.text),'sha256':hashlib.sha256(doc.text.encode()).hexdigest()})
        assert comments.index.locate('John.1.2') is None
        SessionStore(Path(directory)/'session.json').save(Session([TabState(bible,'John.1.1',study_visible=True,commentary=commentary)]))
        window=Window(app,library);window.present();window.set_default_size(1180,780)
        try:
            spin(lambda:not window.active_tab._restoring_scroll and not window.study._positioning,duration=.3)
            assert window.study.entry_text==comments.index.text(comments.index.locate('John.1.1'))
            # Use actual X11 keyboard events, then inspect native section anchors.
            from tools.check_alpha_ui import X11Input
            native=X11Input()
            try:
                window.study.text.grab_focus()
                control=native.x11.XKeysymToKeycode(native.display,native.x11.XStringToKeysym(b'Control_L'))
                native.xtest.XTestFakeKeyEvent(native.display,control,True,0);native.key('End')
                native.xtest.XTestFakeKeyEvent(native.display,control,False,0);native.x11.XFlush(native.display)
                spin(lambda:not window.study._positioning,duration=.4)
                section=comments.index.sections[window.study.visible_section()]
                assert window.active_tab.state.reference==section.start, (window.active_tab.state.reference,section)
                window.active_tab.text.grab_focus()
                native.xtest.XTestFakeKeyEvent(native.display,control,True,0);native.key('Home')
                native.xtest.XTestFakeKeyEvent(native.display,control,False,0);native.x11.XFlush(native.display)
                spin(lambda:not window.study._positioning,duration=.3)
                assert window.active_tab.state.reference==window.active_tab.visible_reference()
                result['native_bidirectional_sync']=True
            finally:native.close()
            window.active_tab.navigate(bible,'John.1.1');window.study.refresh(force=True)
            spin(lambda:not window.study._positioning and not window.active_tab._restoring_scroll,duration=.3)
            original=window.active_tab.state.reference
            assert window.enter_immersion('commentary')
            spin(lambda:window.immersion.stream.cursor is not None,duration=.3)
            immersion=window.immersion;seen=[]
            import gi
            gi.require_version('GdkX11','4.0')
            from gi.repository import GdkX11  # registers surface.get_xid
            immersion.top.set_reveal_child(False);spin(duration=.3)
            capture=Path(output).with_suffix('.png')
            subprocess.run(['import','-window',str(window.get_surface().get_xid()),str(capture)],check=True)
            while True:
                for view,address in zip(immersion.views,immersion.addresses):
                    plan=immersion.stream.plan(address.key);page=plan.pages[address.index]
                    assert view.get_buffer().props.text==plan.document.text[page.start:page.end]
                    text=view.get_buffer().props.text
                    if text:
                        last=view.get_iter_location(view.get_buffer().get_iter_at_offset(len(text)-1))
                        assert last.y+last.height+view.get_top_margin()<=view.get_height()+1, (last.y,last.height,view.get_height(),immersion._geometry,window.preferences.value)
                    seen.append(view.get_buffer().props.text)
                if not immersion.turn(1):break
                spin(duration=.03)
            assert ''.join(seen)==comments.index.text(comments.index.locate('John.1.1'))
            assert window.active_tab.state.reference==original
            window.leave_immersion();spin(lambda:not window.study._positioning)
            window.active_tab.navigate(bible,'John.1.2');window.study.refresh(force=True)
            assert window.study.entry_text==''
            assert window.study.status.get_text()
            result['gui']={'long_entry_partition_exact':True,'bible_unchanged_during_commentary':True,'missing_entry_cleared':True,'display':'GTK under current display; GNOME manual validation separate'}
        finally:window.close()
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
