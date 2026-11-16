"""Offline checks that persistence keeps the reviewed local distribution."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'vendor/skills/turnstile-spin'

@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'requires bash')
class VendorPersistTests(unittest.TestCase):
    def run_helper(self, source, project, target):
        return subprocess.run([shutil.which('bash'), str(source / 'scripts/persist-skill.sh'), '--path', str(target / 'SKILL.md')],
                              cwd=project, env={'PATH': os.defpath}, text=True, capture_output=True, timeout=20)

    def test_copies_reviewed_bundle_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / '.claude/skills/turnstile-spin'
            result = self.run_helper(SOURCE, root, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'ok')
            for path in SOURCE.rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (target / path.relative_to(SOURCE)).read_bytes())
            result = self.run_helper(SOURCE, root, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['reason'], 'target_not_empty')

    def test_copy_failure_and_links_do_not_report_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'ordinary_file').write_text('untouched')
            result = self.run_helper(SOURCE, root, root / 'ordinary_file' / 'skill')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['reason'], 'copy_failed')
            self.assertEqual((root / 'ordinary_file').read_text(), 'untouched')
            local_source = root / 'local-source'; shutil.copytree(SOURCE, local_source)
            (local_source / 'untrusted-link').symlink_to(root / 'ordinary_file')
            target = root / 'target'; result = self.run_helper(local_source, root, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['reason'], 'copy_failed')
            self.assertFalse(target.exists())

    def test_target_outside_project_or_inside_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_helper(SOURCE, tmp, Path(tmp).parent / 'outside-skill')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['reason'], 'target_outside_project')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); local_source = root / 'source'; shutil.copytree(SOURCE, local_source)
            target = local_source / 'nested'; result = self.run_helper(local_source, root, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['reason'], 'target_inside_source')
            self.assertFalse(target.exists())

if __name__ == '__main__':
    unittest.main()
