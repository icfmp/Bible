#!/usr/bin/env python3
"""Run a CI command and expose its failure tail as a public Actions annotation."""
from collections import deque
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: ci_run.py command [arguments...]')
    tail = deque(maxlen=25)
    with subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True) as process:
        for line in process.stdout:
            print(line, end='', flush=True)
            tail.append(line.rstrip())
        result = process.wait()
    if result:
        message = '\n'.join(tail).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title=Integration failure::{message}', flush=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
