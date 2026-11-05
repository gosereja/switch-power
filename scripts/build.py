#!/usr/bin/env python3
"""Build a deterministic private distribution; never include local account data."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    version = json.loads((ROOT / 'plugins/switch-power/plugin.json').read_text())['version']
    base = 'switch-power-' + version
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = [ROOT / 'README.md', ROOT / 'LICENSE']
    for directory in ['plugins', 'scripts', 'tests', 'docs', 'specs/001-global-coordinator']:
        files.extend(p for p in (ROOT / directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    content = {}
    for p in sorted(files):
        if p.is_symlink():
            raise ValueError('Refusing symlink in release: ' + str(p))
        content[p.relative_to(ROOT).as_posix()] = p.read_bytes()
    content['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
        for name, data in sorted(content.items())).encode()
    archive = output / (base + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(content.items()):
            info = zipfile.ZipInfo(base + '/' + name, date_time=(2026, 11, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / (archive.name + '.sha256')).write_text(digest + '  ' + archive.name + '\n')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    print(build(parser.parse_args().out).resolve())
