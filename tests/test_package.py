import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
try:
    import build
except ModuleNotFoundError:
    build = None


class PackageTests(unittest.TestCase):
    def test_reproducible_archive_has_runtime_installers_and_valid_checksums(self):
        self.assertIsNotNone(build, 'Release packager is missing')
        with tempfile.TemporaryDirectory() as name:
            first = build.build(Path(name) / 'first')
            second = build.build(Path(name) / 'second')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                base = 'switch-power-0.1.0/'
                self.assertIn(base + 'scripts/install.py', names)
                self.assertIn(base + 'plugins/switch-power/plugin.json', names)
                self.assertFalse(any('.tools/' in n or '__pycache__' in n or '.git/' in n for n in names))
                hashes = archive.read(base + 'SHA256SUMS').decode().splitlines()
                for line in hashes:
                    digest, path = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256(archive.read(base + path)).hexdigest(), digest)
                manifest = json.loads(archive.read(base + 'plugins/switch-power/plugin.json'))
                self.assertEqual(manifest['name'], 'switch-power')


if __name__ == '__main__':
    unittest.main()
