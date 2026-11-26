"""Bound native tool validation; a malformed archive cannot terminate GTK."""

import subprocess
import sys


def verify(root, name):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bible.native_module_probe", str(root), name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        raise ValueError(
            "Native study module verification timed out; installed files were preserved"
        ) from None
    if result.returncode:
        raise ValueError(
            "SWORD could not verify the study module package; installed files were preserved"
        )


def main():
    # Failed third-party native decoding should not leave large core files.
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except ImportError:
        pass
    from .sword_provider import DictionaryReader, GeneralBookReader
    from .library import config
    from pathlib import Path

    section = config(next((Path(sys.argv[1]) / "mods.d").glob("*.conf")).read_bytes())[sys.argv[2]]
    factory = GeneralBookReader if section.get("ModDrv") == "RawGenBook" else DictionaryReader
    factory(sys.argv[1], sys.argv[2]).verify_readable()


if __name__ == "__main__":
    main()
