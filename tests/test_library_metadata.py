"""Repeated UI metadata reads reuse immutable attribution without stale sources."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bible.library import Library,config,resource_from_section


class LibraryMetadataTests(unittest.TestCase):
    def test_public_codes_come_from_provider_metadata_and_not_module_ids(self):
        from dataclasses import replace
        from bible.providers import PROVIDERS
        for provider in PROVIDERS:
            resource=resource_from_section('Internal123',{'Description':'Full edition','Abbreviation':'ABC'},provider)
            self.assertEqual(resource.public_code,'ABC')
            self.assertEqual(replace(resource,abbreviation='').public_code,'')
            self.assertEqual(replace(resource,abbreviation=resource.id).public_code,'' if '~' in resource.id else 'Internal123')
        resource=replace(resource,name='YV21',abbreviation='YV21')
        self.assertEqual(resource.public_code,'')
        for invalid in ('a\nb','x'*41):self.assertEqual(replace(resource,abbreviation=invalid).public_code,'')

    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.module=self.root/'Test';self.module.mkdir()
        (self.module/'.complete').write_text('Test')
        (self.module/'mods.d').mkdir()
        self.configuration=self.module/'mods.d/test.conf'
        self.configuration.write_text('[Test]\nDescription=Original\nModDrv=RawText\nLang=en\nCopyright=Original terms\n')
        self.library=Library(self.root)

    def test_repeated_reads_reuse_parsing_but_changed_terms_and_source_are_revalidated(self):
        with patch('bible.library.config',wraps=config) as parse:
            for _ in range(20):
                self.assertEqual(self.library.installed('bible'),['Test'])
                self.assertEqual(self.library.resource('Test').description,'Original')
            self.assertEqual(parse.call_count,1)
            self.configuration.write_text(self.configuration.read_text().replace('Original','Revised'))
            self.assertEqual(self.library.resource('Test').description,'Revised')
            self.assertIn('Revised terms',self.library.resource('Test').conditions)
            self.assertEqual(parse.call_count,2)
        provenance=self.module/'.source.json'
        provenance.write_text(json.dumps(dict(provider_id='crosswire',source='Recorded source',url='https://example.org/')))
        self.assertEqual(self.library.resource('Test').source,'Recorded source')
        provenance.write_text(json.dumps(dict(provider_id='unknown')))
        with self.assertRaisesRegex(ValueError,'identity mismatch'):self.library.resource('Test')
        provenance.unlink()
        self.assertEqual(self.library.resource('Test').source,'CrossWire')

    def test_replacement_with_same_size_and_mtime_and_removal_do_not_return_stale_attribution(self):
        self.library.resource('Test');before=self.configuration.stat()
        replacement=self.configuration.with_suffix('.new')
        replacement.write_text(self.configuration.read_text().replace('Original','Changed!'))
        import os
        os.utime(replacement,ns=(before.st_atime_ns,before.st_mtime_ns))
        replacement.replace(self.configuration)
        self.assertEqual(self.library.resource('Test').description,'Changed!')
        (self.module/'.complete').unlink()
        with self.assertRaisesRegex(ValueError,'not installed'):self.library.resource('Test')
