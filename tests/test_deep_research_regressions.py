"""Offline regressions for citation and claim-support verification."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASES = [ROOT / 'skills', ROOT / 'platforms/claude/cheremisina-marketing-skills/skills']


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResearchRegressions(unittest.TestCase):
    def test_citation_doi_and_url_independence(self):
        for base in BASES:
            module = load(base / 'che-deep-research/scripts/verify_citations.py', 'review_citations')
            for bibliography, doi_result, expected_ok, expected_status in [
                ('[1] Author (2024). "Specific research title". https://example.org/page DOI https://doi.org/10.1234/missing', (False, {'error': 'DOI not found (404)'}), False, 'unverified'),
                ('[1] Author (2024). "Specific research title". https://doi.org/10.1234/ok', (True, {'title': 'Specific research title', 'year': 2024}), True, 'verified'),
                ('[1] Author (2024). "Specific research title". https://example.org/page', (False, {}), True, 'url_verified'),
                ('[1] Author (2024). "Specific research title". https://doi.org/10.1234/ok', (True, {'title': 'Entirely different publication', 'year': 2020}), False, 'suspicious'),
            ]:
                with self.subTest(base=base, expected_status=expected_status), tempfile.TemporaryDirectory() as tmp:
                    report = Path(tmp) / 'report.md'
                    report.write_text('## Bibliography\n' + bibliography + '\n', encoding='utf-8')
                    verifier = module.CitationVerifier(report, strict_mode=True)
                    with patch.object(verifier, 'verify_doi', return_value=doi_result), patch.object(verifier, 'verify_url', return_value=(True, 'accessible')), patch.object(module.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(verifier.verify_all(), expected_ok)
                        result = verifier.verify_entry(verifier.extract_bibliography()[0])
                    self.assertEqual(result['status'], expected_status)

    def test_claim_contradiction_and_strict(self):
        for base in BASES:
            script = base / 'che-deep-research/scripts/verify_claim_support.py'
            module = load(script, 'review_claims')
            for claim, quote in [('Продажи выросли на 20%', 'Продажи упали на 20%'), ('Рынок растёт', 'Рынок снижается'), ('Sales increased by 20%', 'Sales decreased by 20%')]:
                with self.subTest(base=base, claim=claim):
                    self.assertNotEqual(module.compute_support_score(claim, [quote])[0], 'supported')
            self.assertEqual(module.extract_years('2024 2025'), {'2024', '2025'})
            self.assertEqual(module.compute_support_score('Продажи выросли', ['Продажи выросли'])[0], 'supported')
            for quote, expected_exit in [('Продажи упали', 1), ('Продажи выросли', 0), (None, 1)]:
                with self.subTest(base=base, quote=quote), tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp)
                    (path / 'claims.jsonl').write_text(json.dumps({'claim_id':'c1', 'section_id':'s', 'text':'Продажи выросли', 'evidence_ids':['e1']}, ensure_ascii=False)+'\n')
                    (path / 'evidence.jsonl').write_text(json.dumps({'evidence_id':'e1', 'quote':quote}, ensure_ascii=False)+'\n' if quote else '')
                    (path / 'sources.jsonl').write_text('')
                    result = subprocess.run([sys.executable, str(script), 'verify', '--dir', tmp, '--strict'], capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)
                    if expected_exit:
                        report = subprocess.run([sys.executable, str(script), 'report', '--dir', tmp], capture_output=True, text=True)
                        self.assertNotIn('All factual claims have adequate support', report.stdout)


if __name__ == '__main__':
    unittest.main()
