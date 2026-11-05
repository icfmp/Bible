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
    def register(self,number,code='org',changed=False,addresses=False,verified=True):
        system='YouVersion'+str(number)
        canon=json.loads((Path(__file__).parents[1]/'bible/versification_data/Original.json').read_text())['canon']
        if changed:canon['Gen'][0]+=1
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.source-versification'
            digest=write_index(path,system,canon,{b:1 if i<39 else 2 for i,b in enumerate(canon)})
            (path.parent/'.verified.json').write_text(json.dumps(dict(reference_index_sha256=digest,
                source_numbering=code,storage_numbering=system,all_text_notes_headings_verified=verified,source_addresses_sha256='a'*64 if addresses else None)))
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
        for number,options in ((900185,dict(code='unknown')),(900186,dict(changed=True)),
                              (900187,dict(addresses=True)),(900188,dict(verified=False))):
            system=self.register(number,**options)
            self.assertIsNone(reference_convention(system));self.assertIsNone(table(system))
            with self.assertRaises(VersificationMismatch):resolve('Gen.11.3',system,Canon('KJV'),require_entry=False)
