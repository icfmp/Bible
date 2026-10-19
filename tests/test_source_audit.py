"""Audit distinctions must not mistake an unsupported/hidden entry for absence."""
import io
import tarfile
import unittest
from tools.audit_affiliated_sources import Document, entries


class SourceAuditTests(unittest.TestCase):
    def test_missing_language_lock_and_unsupported_driver_remain_visible(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            fixtures = {
                'Visible': b'ModDrv=zCom\nLang=fr\n',
                'NoLanguage': b'ModDrv=RawCom4\n',
                'Locked': b'ModDrv=zCom4\nLang=en\nCipherKey=\n',
                'Unsupported': b'ModDrv=RawLD\nCategory=Commentaries\nLang=en\n',
            }
            for name, content in fixtures.items():
                content = f'[{name}]\n'.encode() + content
                member = tarfile.TarInfo(f'mods.d/{name}.conf')
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        found = {r['name']: r for r in entries(data.getvalue())}
        self.assertEqual(set(found), set(fixtures))
        self.assertTrue(all(r['commentary'] for r in found.values()))
        self.assertTrue(found['NoLanguage']['missing_language'])
        self.assertTrue(found['Locked']['locked'])
        self.assertFalse(found['Unsupported']['supported_driver'])
        self.assertTrue(found['Visible']['supported_driver'])

    def test_document_links_resolve_without_inventing_https_mirrors(self):
        document = Document('https://official.example/doc/index.html')
        document.feed('<a href="../modules/">Modules</a><a href="ftp://old.example/pub/">Old</a>'
                      '<script>hidden</script><p>Public documentation</p>')
        self.assertEqual(document.links, ['https://official.example/modules/', 'ftp://old.example/pub/'])
        self.assertNotIn('hidden', document.parts)
