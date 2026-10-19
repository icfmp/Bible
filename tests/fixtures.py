"""Tiny real SWORD modules with sentinel text, never bundled application resources."""
from pathlib import Path
from tests.test_library import CONF


def module_fixture(root, name, entries, versification='KJV', nt_only=False, commentary=False):
    import Sword
    root = Path(root)
    path = root / 'modules/texts/rawtext/test'
    path.mkdir(parents=True)
    driver = Sword.RawCom if commentary else Sword.RawText
    driver.createModule(str(path), versification)
    module = driver(str(path), name, 'Test data only', None,
                           Sword.ENC_UTF8, Sword.DIRECTION_LTR, Sword.FMT_PLAIN,
                           'en', versification)
    for reference, text in entries:
        key = Sword.VerseKey()
        key.setVersificationSystem(versification)
        key.setText(reference)
        assert key.popError() == '\x00', reference
        module.setKey(key)
        module.setEntry(text)
    del module
    if nt_only:
        for item in path.glob('ot*'):
            item.unlink()
    conf = root / 'mods.d/test.conf'
    conf.parent.mkdir()
    conf.write_bytes(CONF.replace(b'[Test]', f'[{name}]'.encode()) +
                     f'Versification={versification}\n'.encode())
    if commentary:
        conf.write_bytes(conf.read_bytes().replace(b'ModDrv=RawText', b'ModDrv=RawCom'))
