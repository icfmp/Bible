"""Read an installed resource in a separate process (optionally a network namespace)."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from bible.sword_provider import Reader


def main():
    root, name = sys.argv[1:]
    with patch('urllib.request.urlopen', side_effect=AssertionError('Offline')):
        reader = Reader(Path(root), name)
        chapter = reader.chapter('Gen.1.1')
        assert reader.chapter(chapter.following).previous == 'Gen.1.1'
        digest = hashlib.sha256(json.dumps(chapter.verses, ensure_ascii=False).encode()).hexdigest()
        print(digest)


if __name__ == '__main__':
    main()
