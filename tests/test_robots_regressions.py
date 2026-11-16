"""Offline root-URL robots checks; network and crawler behavior are not exercised."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASES = [ROOT / 'skills', ROOT / 'platforms/claude/cheremisina-marketing-skills/skills']


def load(path):
    bs4 = types.ModuleType('bs4')
    bs4.BeautifulSoup = object
    with patch.dict(sys.modules, {'requests': types.ModuleType('requests'), 'bs4': bs4}):
        spec = importlib.util.spec_from_file_location('robots_auditor', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class RobotsRegressions(unittest.TestCase):
    def test_groups_and_ambiguity(self):
        cases = [
            ('User-agent: *\nDisallow: /\n\nUser-agent: GPTBot\nAllow: /\n', 'allowed'),
            ('User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n', 'blocked'),
            ('User-agent: GPTBot\nDisallow: /\nAllow: /\n', 'unknown'),
            ('User-agent: GPTBot\nDisallow: /*\n', 'unknown'),
            ('User-agent: GPTBot\nDisallow: /\n\nUser-agent: GPTBot\nAllow: /\n', 'unknown'),
            ('User-agent: *\nDisallow: /\n\nUser-agent: GPTBot\n', 'unknown'),
        ]
        for base in BASES:
            module = load(base / 'che-seo-geo-auditor/scripts/audit_website.py')
            for body, expected in cases:
                with self.subTest(base=base, body=body):
                    fixture = {'status': 200, 'text': body, 'headers': {}, 'error': None}
                    with patch.object(module, 'fetch_url', return_value=fixture):
                        result = module.check_robots_txt('https://example.invalid')
                    actual = 'blocked' if 'GPTBot' in result['ai_bots_blocked'] else 'unknown' if 'GPTBot' in result['ai_bots_unknown'] else 'allowed'
                    self.assertEqual(actual, expected)
                    self.assertEqual(result['scope'], 'root_url_only')
                    if body.startswith('User-agent: GPTBot\nUser-agent: ClaudeBot'):
                        self.assertIn('ClaudeBot', result['ai_bots_blocked'])
            with patch.object(module, 'fetch_url', return_value={'status': 200, 'text': cases[2][0], 'headers': {}, 'error': None}):
                result = module.check_robots_txt('https://example.invalid')
            report = module.generate_report('https://example.invalid', 'synthetic', {'robots_txt': result}, 80, [])
            self.assertIn('Неоднозначные правила robots.txt', report)
            self.assertNotIn('боты (GPTBot, PerplexityBot, ClaudeBot) не заблокированы', report)


if __name__ == '__main__':
    unittest.main()
