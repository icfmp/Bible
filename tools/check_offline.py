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
        first = reader.first_reference()
        chapter = reader.chapter(first)
        following = reader.neighbours(first)[1]
        if following:
            assert reader.neighbours(following)[0] == first
            assert reader.chapter(following).verses
        digest = hashlib.sha256(json.dumps(chapter.verses, ensure_ascii=False).encode()).hexdigest()
        print(digest)


if __name__ == '__main__':
    main()
