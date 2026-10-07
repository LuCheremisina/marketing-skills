"""Observable correctness of merged exports and incomplete email baselines."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

def load_script(path):
    spec = importlib.util.spec_from_file_location('tested_skill', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class IncompleteBaselineTests(unittest.TestCase):
    def test_missing_numerator_does_not_become_complete_rate(self):
        for skill in ('che-audit-unisender-email', 'che-unisender-email-pipeline'):
            with self.subTest(skill=skill):
                module = load_script(ROOT / 'skills' / skill / 'scripts/calculate_email_audit.py')
                rows = [dict.fromkeys(module.COUNT_FIELDS, 10) for _ in range(2)]
                for row in rows:
                    row['metrics'] = defaultdict(lambda: None)
                rows[0]['leads'] = 2
                rows[1]['leads'] = None
                result = module.weighted_baseline(rows)
                self.assertIsNone(result['weighted_rates']['lead_cr'])
                rows[1]['leads'] = 4
                self.assertEqual(module.weighted_baseline(rows)['weighted_rates']['lead_cr'], 0.3)

    def test_missing_denominator_blocks_cross_coverage_rate(self):
        for skill in ('che-audit-unisender-email', 'che-unisender-email-pipeline'):
            with self.subTest(skill=skill):
                module = load_script(ROOT / 'skills' / skill / 'scripts/calculate_email_audit.py')
                rows = [dict.fromkeys(module.COUNT_FIELDS, 10) for _ in range(2)]
                for row in rows:
                    row['metrics'] = defaultdict(lambda: None)
                rows[0]['delivered'] = 90
                rows[1]['delivered'] = None
                rows[0]['unique_clickers'] = rows[1]['unique_clickers'] = 9
                self.assertIsNone(module.weighted_baseline(rows)['weighted_rates']['ctr'])

class CoverExportTests(unittest.TestCase):
    def test_export_uses_explicit_paths_and_preserves_existing_output(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow unavailable; image execution not verified')
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / 'source.png'
            Image.new('RGB', (640, 360), 'white').save(source)
            script = ROOT / 'skills/che-cover-production/scripts/export_article_cover.py'
            cmd = [sys.executable, str(script), '--input', str(source), '--slug', 'synthetic-cover', '--output-dir', str(base / 'result'), '--png-width', '320', '--png-height', '180', '--webp-width', '160', '--webp-height', '90']
            completed = subprocess.run(cmd, cwd=base, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with Image.open(base / 'result/synthetic-cover-cover.png') as opened:
                self.assertEqual(opened.size, (320, 180))
            with Image.open(base / 'result/synthetic-cover-cover.webp') as opened:
                self.assertEqual(opened.size, (160, 90))
            before = source.read_bytes()
            output_before = (base / 'result/synthetic-cover-cover.png').read_bytes()
            repeated = subprocess.run(cmd, cwd=base, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((base / 'result/synthetic-cover-cover.png').read_bytes(), output_before)

if __name__ == '__main__':
    unittest.main()
