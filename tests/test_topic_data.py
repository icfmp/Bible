import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile
from bible import topic_data as data
from bible.topic_vocabulary import VOCABULARY,suggestions,title


def archive(path,rows=None,filename='topic-scores.txt'):
    header='Topic\tOSIS\tQuality Score (based on percentage of votes for the passage)\t# Generated 2026-10-19. CC-BY License: www.openbible.info/topics\n'
    text=header+(rows if rows is not None else ''.join(e[0]+'\tJohn.3.16\t20\n' for e in VOCABULARY))
    with zipfile.ZipFile(path,'w') as z:z.writestr(filename,text)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TopicDataTests(unittest.TestCase):
    def test_curated_bilingual_ambiguity_accents_and_no_sentence_claim(self):
        self.assertEqual(len(VOCABULARY),50)
        self.assertEqual(len({e[0] for e in VOCABULARY}),50)
        self.assertEqual({e[0] for e in suggestions('pardon')},
                         {'forgiveness','forgiveness of sins','forgiving others','reconciliation'})
        self.assertEqual(suggestions('RÉCONCILIATION')[0][0],'reconciliation')
        self.assertEqual(suggestions('inquietude')[0][0],'anxiety')
        self.assertEqual(suggestions('Holy-Spirit')[0][0],'holy spirit')
        self.assertEqual(suggestions('bonjour vocabulaire inconnu'),[])
        self.assertEqual(title(suggestions('grace')[0],'fr'),'Grâce')

    def test_real_sqlite_exact_deduplication_rank_and_no_topic_merging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'data.zip'
            rows=''.join(e[0]+'\tJohn.3.16\t20\n' for e in VOCABULARY)
            rows+='forgiveness\tJohn.3.16\t30\nforgiveness\tPs.3.1-Ps.3.2\t30\nforgiveness\t3John.1.15\t2\n'
            sha=archive(path,rows)
            with patch.object(data,'ARCHIVE_SHA256',sha):metadata=data.TopicData(root).install_archive(path)
            store=data.TopicData(root);self.assertEqual(metadata['topics'],50)
            rows=store.query('forgiveness')
            self.assertEqual([(r.start,r.score) for r in rows],[('Ps.3.1',30),('John.3.16',30),('3John.1.15',2)])
            self.assertEqual(len(store.query('reconciliation')),1)
            with self.assertRaises(data.ReferenceDataError):store.query('unreviewed topic')

    def test_failed_hash_and_invalid_schema_leave_installed_resource_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'data.zip';sha=archive(path);store=data.TopicData(root)
            with patch.object(data,'ARCHIVE_SHA256',sha):store.install_archive(path)
            before=store.path.read_bytes();path.write_bytes(b'corrupt')
            with self.assertRaises(data.ReferenceDataError):store.install_archive(path)
            sha=archive(path,'forgiveness\tJohn.99.1\t101\n')
            with patch.object(data,'ARCHIVE_SHA256',sha),self.assertRaises(data.ReferenceDataError):store.install_archive(path)
            self.assertEqual(store.path.read_bytes(),before);self.assertTrue(store.query('forgiveness'))

    def test_zip_path_score_bounds_reference_bounds_and_missing_vocabulary(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'data.zip'
            for rows,name in [('forgiveness\tJohn.1.1\t2\n','../topic-scores.txt'),
                              ('forgiveness\tJohn.1.1\t101\n','topic-scores.txt'),
                              ('forgiveness\tJohn.1.1\t-1\n','topic-scores.txt'),
                              ('forgiveness\t3John.1.16\t2\n','topic-scores.txt'),
                              ('forgiveness\tJohn.1.2-John.1.1\t2\n','topic-scores.txt')]:
                archive(path,rows,name)
                with self.assertRaises(data.ReferenceDataError):list(data.parse_archive(path))
            sha=archive(path,'forgiveness\tJohn.1.1\t2\n')
            with patch.object(data,'ARCHIVE_SHA256',sha),self.assertRaises(data.ReferenceDataError):
                data.TopicData(Path(temporary)/'missing').install_archive(path)


if __name__=='__main__':unittest.main()
