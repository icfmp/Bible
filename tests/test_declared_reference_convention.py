"""A declared, verified reference convention is separate from storage identity."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from bible.source_versification import write_index,register_index,reference_convention
from bible.reference_resolution import resolve,VersificationMismatch
from bible.reference_targets import Canon
from bible.versification_mapping import table,to_base,from_base
from tests.test_source_versification import native_available


@unittest.skipUnless(native_available(),'Requires the packaged source-index extension')
class DeclaredConventionTests(unittest.TestCase):
    def register(self,number,code='org',changed=False,addresses=False,verified=True,canon=None,address_index=None):
        system='YouVersion'+str(number)
        if canon is None:canon=json.loads((Path(__file__).parents[1]/'bible/versification_data/Original.json').read_text())['canon']
        if changed:canon['Gen'][0]+=1
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.source-versification'
            nt={b for i,b in enumerate(json.loads((Path(__file__).parents[1]/'bible/versification_data/Original.json').read_text())['canon']) if i>=39}
            digest=write_index(path,system,canon,{b:2 if b in nt else 1 for b in canon})
            address_sha='a'*64 if addresses else None
            if address_index is not None:
                data=json.dumps(address_index.data()).encode();(path.parent/'.source-addresses.json').write_bytes(data)
                address_sha=hashlib.sha256(data).hexdigest()
            (path.parent/'.verified.json').write_text(json.dumps(dict(reference_index_sha256=digest,
                source_numbering=code,storage_numbering=system,all_text_notes_headings_verified=verified,source_addresses_sha256=address_sha)))
            register_index(path)
        return system

    def test_declared_convention_reuses_mapping_in_both_directions(self):
        system=self.register(900184)
        self.assertEqual(reference_convention(system),'Original')
        for ref in ('Gen.11.3','Ps.33.1','Ps.33.15'):
            self.assertEqual(resolve(ref,system,Canon('Original'),require_entry=False).start,ref)
            self.assertEqual(resolve(ref,'Original',Canon(system),require_entry=False).start,ref)
        self.assertEqual(resolve('Gen.32.1',system,Canon('KJV'),require_entry=False).start,'Gen.31.55')
        self.assertEqual(resolve('Gen.31.55','KJV',Canon(system),require_entry=False).start,'Gen.32.1')
        self.assertEqual(resolve('Ps.3.2',system,Canon('KJV'),require_entry=False).start,'Ps.3.1')
        self.assertEqual(resolve('Ps.3.1','KJV',Canon(system),require_entry=False).start,'Ps.3.2')
        with self.assertRaises(VersificationMismatch):resolve('Num.25.19',system,Canon('KJV'),require_entry=False)
        self.assertEqual(resolve('Num.25.18',system,Canon('KJV'),require_entry=False).start,'Num.25.18')

    def test_matching_shape_alone_never_creates_a_mapping(self):
        for number,options in ((900185,dict(code='unknown')),
                              (900187,dict(addresses=True)),(900188,dict(verified=False))):
            system=self.register(number,**options)
            self.assertIsNone(reference_convention(system));self.assertIsNone(table(system))
            with self.assertRaises(VersificationMismatch):resolve('Gen.11.3',system,Canon('KJV'),require_entry=False)

    def test_unrelated_book_difference_does_not_revoke_verified_books(self):
        system=self.register(900186,changed=True)
        self.assertIsNotNone(table(system))
        # Equal dimensions elsewhere in the changed book are not independent
        # evidence: keep that entire book unavailable in both directions.
        for ref in ('Gen.1.1','Gen.11.3'):
            with self.assertRaises(VersificationMismatch):resolve(ref,system,Canon('KJV'),require_entry=False)
            with self.assertRaises(VersificationMismatch):resolve(ref,'KJV',Canon(system),require_entry=False)
        self.assertEqual(resolve('John.3.16',system,Canon('KJV'),require_entry=False).start,'John.3.16')
        self.assertEqual(resolve('John.3.16','KJV',Canon(system),require_entry=False).start,'John.3.16')

    def test_extra_and_missing_books_are_local_capabilities(self):
        original=json.loads((Path(__file__).parents[1]/'bible/versification_data/Original.json').read_text())['canon']
        for number,canon in ((900215,{'Tob':[2],'John':original['John']}),
                             (900216,{'John':original['John']})):
            system=self.register(number,canon=canon)
            self.assertIsNotNone(table(system))
            self.assertEqual(resolve('John.3.16',system,Canon('KJV'),require_entry=False).start,'John.3.16')
            self.assertEqual(resolve('John.3.16','KJV',Canon(system),require_entry=False).start,'John.3.16')
            with self.assertRaises(ValueError):resolve('Gen.1.1','KJV',Canon(system),require_entry=False)
            if 'Tob' in canon:
                with self.assertRaises(VersificationMismatch):resolve('Tob.1.1',system,Canon('KJVA'),require_entry=False)

    def test_verified_address_transform_does_not_claim_numbering_equivalence(self):
        from bible.source_units import AddressIndex,ChapterUnits,SourceUnit
        from bible.source_sections import SectionIndex,SourceChapter
        # Identical native dimensions conceal different public identities.
        # Both section remapping and overlapping-unit remapping stay local.
        for number,index in ((900217,AddressIndex(SectionIndex.allocate([
                SourceChapter('John.2','2',True),SourceChapter('John.1','1',True)]))),
                (900218,AddressIndex(chapters=[ChapterUnits('John.1',[
                    SourceUnit(('John.1.1',),'1'),SourceUnit(('John.1.1','John.1.2'),'1–2')])]))):
            system=self.register(number,address_index=index)
            self.assertEqual(resolve('Gen.11.3',system,Canon('KJV'),require_entry=False).start,'Gen.11.3')
            self.assertEqual(resolve('Gen.11.3','KJV',Canon(system),require_entry=False).start,'Gen.11.3')
            with self.assertRaises(VersificationMismatch):resolve('John.1.1',system,Canon('KJV'),require_entry=False)
            with self.assertRaises(VersificationMismatch):resolve('John.1.1','KJV',Canon(system),require_entry=False)

    def test_empty_chapter_slots_do_not_change_native_canon_validation(self):
        original=json.loads((Path(__file__).parents[1]/'bible/versification_data/Original.json').read_text())['canon']
        system=self.register(900219,canon={'Tob':[0,3,0,2],'John':original['John']})
        self.assertEqual(table(system)['canon']['Tob'],[0,3,0,2])
        self.assertEqual(resolve('John.3.16',system,Canon('KJV'),require_entry=False).start,'John.3.16')
        self.assertEqual(resolve('John.3.16','KJV',Canon(system),require_entry=False).start,'John.3.16')
        with self.assertRaises(VersificationMismatch):resolve('Tob.2.1',system,Canon('KJVA'),require_entry=False)

    def test_changed_source_declaration_revokes_a_previously_cached_capability(self):
        system=self.register(900189)
        self.assertIsNotNone(table(system))
        self.assertEqual(self.register(900189,code='unknown'),system)
        self.assertIsNone(reference_convention(system));self.assertIsNone(table(system))
        with self.assertRaises(VersificationMismatch):resolve('Gen.11.3',system,Canon('KJV'),require_entry=False)
