#!/usr/bin/env python3
"""Install Switch Power and verify its native Codex registration."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', help='Path to the native Codex CLI')
    parser.add_argument('--codex-home', help='Target Codex profile directory')
    parser.add_argument('--coordinator', action='store_true', help='Also apply the Sol/high default')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Python 3.11 or newer is required')
    options = []
    for flag, value in [('--codex', args.codex), ('--codex-home', args.codex_home)]:
        if value:
            options.extend([flag, value])
    steps = [('install.py', ['install'])]
    if args.coordinator:
        steps.append(('configure.py', ['apply']))
    steps.append(('verify_native.py', []))
    scripts = Path(__file__).resolve().parent
    for script, action in steps:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(scripts / script), *options, *action])
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
