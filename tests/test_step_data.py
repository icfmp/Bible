"""STEP parsing, edition identity, exact lemma counts and atomic replacement."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible import step_data
from bible.step_data import StepData,token_rows


def fixtures(root):
    # Deliberately tiny test-only TSVs, never advertised as real full corpora.
    values={'greek-lexicon':'G3056\tG3056 =\tG3056\tλόγος\tlogos\tG:N-M\tword\tTEST definition\n'}
    for name,code in [('greek-gospels','Jhn'),('greek-rest','Act')]:
        values[name]=f'{code}.1.1#01=NKO\tλόγος (logos)\tword\tG3056=N-NSM\tλόγος=word\tNA27+TR\n'
        values[name]+=f'{code}.1.1#02=K\tOTHER\tother\tG0001=N\tOTHER=other\tTR\n'
    for name,code in [('hebrew-torah','Gen'),('hebrew-history','Jos'),('hebrew-writings','Psa'),('hebrew-prophets','Isa')]:
        fields=[f'{code}.1.1#01=L','בָּרָא',"ba.Ra'",'he created','{H1254A}','HVqp3ms','','','H1254A','','','{H1254A=בָּרָא=to create}']
        values[name]='\t'.join(fields)+'\n'
    files={};pins={}
    for name,value in values.items():
        path=root/name;path.write_text(value);files[name]=path
        pins[name]=(name,hashlib.sha256(path.read_bytes()).hexdigest(),path.stat().st_size)
    return files,pins


class StepDataTests(unittest.TestCase):
    def test_filtered_corpora_lexical_lookup_counts_and_failed_update_retains_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);files,pins=fixtures(root);store=StepData(root/'study')
            with patch.object(step_data,'FILES',pins),patch.object(step_data,'EXPECTED_COUNTS',{'tagnt-na27':2,'tahot-main':4}):
                store.install_files(files)
                self.assertEqual(store.lookup('G3056')['lemma'],'λόγος')
                self.assertEqual(store.lookup('H1254A')['gloss'],'to create')
                self.assertEqual([r['id'] for r in store.candidates('H1254')],['H1254A'])
                words=store.verse('tagnt-na27','John.1.1');self.assertEqual(len(words),1)
                self.assertEqual(words[0]['source_key'],'Jhn.1.1#01=NKO')
                occurrences=store.occurrences('tagnt-na27','G3056',limit=1)
                self.assertEqual((occurrences['tokens'],occurrences['verses']),(2,2))
                self.assertEqual(occurrences['references'],['John.1.1'])
                before=store.path.read_bytes();files['greek-rest'].write_text('corrupt')
                with self.assertRaises(ValueError):store.install_files(files)
                self.assertEqual(store.path.read_bytes(),before)
                files,_=fixtures(root)
                calls=[0]
                def cancelled():calls[0]+=1;return calls[0]>12
                with self.assertRaises(InterruptedError):store.install_files(files,cancelled)
                self.assertEqual(store.path.read_bytes(),before)
                self.assertFalse(list(store.root.glob('.step-index-*')))
            self.assertEqual(StepData(store.root).lookup('G3056')['gloss'],'word')
            with self.assertRaises(ValueError):store.lookup('G3056 OR 1=1')

    def test_alternate_title_addresses_remain_distinct_and_excluded_readings_stay_out(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'tokens'
            lines=[]
            for reference,reading,word in [('Psa.51.0(51.1)','L','one'),('Psa.51.0(51.2)','L','two'),('Psa.51.1','X','excluded'),('Psa.51.2','Q(K)','qere')]:
                fields=[f'{reference}#01={reading}',word,'form','TEST gloss','{H1254A}','H','','','','','','{H1254A=lemma=gloss}']
                lines.append('\t'.join(fields))
            path.write_text('\n'.join(lines))
            rows=[r for _,r in token_rows(path,'tahot-main')]
            self.assertEqual([r['form'] for r in rows],['one','two','qere'])
            self.assertEqual(rows[0]['reference'],rows[1]['reference'])
            self.assertNotEqual(rows[0]['source_key'],rows[1]['source_key'])
