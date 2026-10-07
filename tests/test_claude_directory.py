"""Protect complete authored payloads and directory distribution boundaries."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'platforms/claude/cheremisina-marketing-skills'

class DirectoryPackageTests(unittest.TestCase):
    def test_complete_authored_payload_and_review_limits(self):
        source = ROOT / 'skills'
        expected = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        actual = {str(p.relative_to(PACKAGE / 'skills')): p.read_bytes()
                  for p in (PACKAGE / 'skills').rglob('*') if p.is_file()}
        self.assertEqual(actual, expected, 'Directory build dropped or altered a skill resource')
        self.assertEqual(len(list((PACKAGE / 'skills').glob('*/SKILL.md'))), 34)
        files = [p for p in PACKAGE.rglob('*') if p.is_file()]
        self.assertLessEqual(len(files), 512)
        self.assertFalse((PACKAGE / 'vendor').exists())
        self.assertFalse((PACKAGE / 'tests').exists())
        for p in files:
            if p.suffix not in {'.png', '.svg'}:
                self.assertLessEqual(p.stat().st_size, 256 * 1024, str(p))
        manifest = json.loads((PACKAGE / '.claude-plugin/plugin.json').read_text())
        self.assertEqual(manifest['name'], 'cheremisina-marketing-skills')
        self.assertTrue((PACKAGE / manifest['icon']).is_file())
        self.assertNotIn('hooks', manifest)
        self.assertNotIn('mcpServers', manifest)
