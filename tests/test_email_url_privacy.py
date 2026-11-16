"""Email audit outputs must not retain recognized PII from supplied URL queries."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    base / skill / 'scripts/calculate_email_audit.py'
    for base in (ROOT / 'skills', ROOT / 'platforms/claude/cheremisina-marketing-skills/skills')
    for skill in ('che-audit-unisender-email', 'che-unisender-email-pipeline')
]
SAFE_URL = ('https://example.invalid/?utm_source=unisender&utm_medium=email'
            '&utm_campaign=test&utm_content=hero')


def load(path):
    spec = importlib.util.spec_from_file_location('email_audit_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload(status, url=SAFE_URL, campaign_type='primary'):
    return {
        'as_of': '2026-01-10T00:00:00+00:00',
        'campaigns': [{
            'campaign_id': 'test', 'campaign_type': campaign_type,
            'sent_at': '2026-01-01T00:00:00+00:00', 'observation_window': 'D+7',
            'utm_campaign': 'test', 'link_unique_clickers_status': 'unavailable',
            'source_status': {
                'unisender': 'partial', 'link_stats': 'partial', 'utm': status,
                'web_analytics': 'partial', 'web_analytics_comparison': 'partial',
                'crm': 'partial', 'resend_dedup': 'not_applicable',
            },
            'links': [{'url': url, 'utm_content': 'hero', 'unique_clickers': None}],
        }],
    }


class EmailUrlPrivacyTests(unittest.TestCase):
    def test_rejects_sensitive_query_for_all_utm_statuses(self):
        examples = ('?email=qa%40example.invalid', '?PHone=123',
                    '?other=qa%40example.invalid', '?name=',
                    '?qa%40example.invalid=1', '?note=ok;PHONE=123')
        for path in SCRIPTS:
            module = load(path)
            for status in ('complete', 'partial', 'missing', 'not_applicable'):
                campaign_type = 'excluded' if status == 'not_applicable' else 'primary'
                for query in examples:
                    with self.subTest(script=str(path.relative_to(ROOT)), status=status, query=query):
                        url = SAFE_URL + '&' + query[1:]
                        with self.assertRaisesRegex(ValueError, 'prohibited PII|email-like'):
                            module.calculate(payload(status, url, campaign_type))

    def test_incomplete_utm_keeps_valid_or_absent_urls_but_rejects_non_strings(self):
        for path in SCRIPTS:
            module = load(path)
            for status in ('partial', 'missing'):
                for url in (SAFE_URL, None, ''):
                    with self.subTest(script=str(path.relative_to(ROOT)), status=status, url=url):
                        result = module.calculate(payload(status, url))
                        self.assertEqual(result['campaigns'][0]['links'][0]['url'], url)
                for url in ({'email': 'qa@example.invalid'}, ['qa@example.invalid'], 0, False):
                    with self.subTest(script=str(path.relative_to(ROOT)), status=status, url=url):
                        with self.assertRaisesRegex(ValueError, 'url must be a string or null'):
                            module.calculate(payload(status, url))
                with self.assertRaisesRegex(ValueError, 'url must be a valid URL'):
                    module.calculate(payload(status, 'https://[invalid/?q=1'))

    def test_complete_utm_contract_and_cli_output(self):
        for path in SCRIPTS:
            module = load(path)
            with self.subTest(script=str(path.relative_to(ROOT))):
                self.assertEqual(module.calculate(payload('complete'))['campaigns'][0]['links'][0]['url'], SAFE_URL)
                for url in (None, '', 'https://example.invalid/'):
                    with self.assertRaises(ValueError):
                        module.calculate(payload('complete', url))
                with tempfile.TemporaryDirectory() as tmp:
                    folder = Path(tmp)
                    input_file, output_file = folder / 'input.json', folder / 'output.json'
                    input_file.write_text(json.dumps(payload('partial', SAFE_URL + '&email=qa%40example.invalid')))
                    result = subprocess.run([sys.executable, str(path), str(input_file), '--output', str(output_file)],
                                            cwd=folder, text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output_file.exists())
                    self.assertNotIn('qa@example.invalid', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
