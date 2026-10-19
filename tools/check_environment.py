#!/usr/bin/env python3
"""Report actual prototype prerequisites without installing or downloading content."""
import argparse
import importlib
import shutil
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', action='store_true',
                        help='Check official HTTPS endpoints (no Bible downloaded).')
    args = parser.parse_args()
    failures = []

    def check(label, action, required=True):
        try:
            print(f'OK {label}: {action()}')
        except Exception as error:
            if required:
                failures.append(label)
            print(f'{"FAIL" if required else "WARN"} {label}: {type(error).__name__}: {error}')

    print(f'Python: {sys.version.split()[0]}')
    check('PyGObject', lambda: importlib.import_module('gi').__version__)
    for name, version in [('Gtk', '4.0'), ('Adw', '1')]:
        def namespace(name=name, version=version):
            gi = importlib.import_module('gi')
            gi.require_version(name, version)
            return importlib.import_module(f'gi.repository.{name}').__name__
        check(name, namespace)
    check('SWORD Python', lambda: importlib.import_module('Sword').__file__)
    for command in ['flatpak', 'flatpak-builder']:
        def executable(command=command):
            path = shutil.which(command)
            if path is None:
                raise FileNotFoundError(command)
            return path
        check(command, executable)
    if args.network:
        for url in [
            'https://www.crosswire.org/ftpmirror/pub/sword/raw/mods.d.tar.gz',
            'https://pygobject.gnome.org/getting_started.html',
            'https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/',
            'https://www.crosswire.org/sword/develop/',
            'https://docs.flatpak.org/en/latest/first-build.html',
        ]:
            def endpoint(url=url):
                request = urllib.request.Request(url, method='HEAD')
                with urllib.request.urlopen(request, timeout=15) as response:
                    return response.status
            check(url, endpoint, required='crosswire.org' in url)
    print(f'{len(failures)} prerequisite(s) failed.')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
