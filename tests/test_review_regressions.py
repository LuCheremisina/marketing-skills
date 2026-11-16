"""Focused regressions from the offline marketing-skills review."""
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
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


def draft_payload(query):
    colors = {k: f'#{i:06x}' for i, k in enumerate(('background', 'paper', 'text', 'paragraph', 'muted', 'accent', 'dark', 'light'), 1)}
    color_text = ';'.join(colors.values())
    links = ''.join(
        f'<tr data-role="article-card" em="block"><td><a href="https://example.invalid/item-{i}?{query}&amp;utm_source=unisender&amp;utm_medium=email&amp;utm_campaign=synthetic_digest&amp;utm_content=article_0{i}">Материал</a></td></tr>'
        for i in range(1, 4)
    )
    preheader = 'Спокойное напоминание о проверке исходных данных перед подготовкой нового письма.'
    return {'subject': 'Синтетическое письмо', 'preheader': preheader, 'utm_campaign': 'synthetic_digest',
            'expected_articles': 3, 'html': f'<!doctype html><html><body style="font-family:Arial;max-width:600px;{color_text}">{preheader}<p>Лист Отправитель</p><table><tr em="group"><td><table>{links}</table></td></tr></table></body></html>',
            'brand_profile': {'brand_name': 'Лист', 'sender_name': 'Отправитель', 'font_family': 'Arial', 'colors': colors}}


class ReviewRegressions(unittest.TestCase):
    def test_secret_prompt_and_transactions(self):
        for base in BASES:
            folder = base / 'che-direct-analytics-skill/scripts'
            setup = load(folder / 'setup.py', 'review_setup')
            for entered, expected in [('', 'synthetic-secret'), ('replacement', 'replacement')]:
                with self.subTest(base=base, entered=entered), patch('getpass.getpass', return_value=entered) as prompt:
                    self.assertEqual(setup.prompt('secret', 'synthetic-secret', True), expected)
                    self.assertNotIn('synthetic-secret', prompt.call_args.args[0])
            with patch('builtins.input', return_value='') as prompt:
                self.assertEqual(setup.prompt('label', 'normal'), 'normal')
                self.assertIn('normal', prompt.call_args.args[0])
            db = load(folder / 'db.py', 'review_db')
            with patch.dict(sys.modules, {'setup': setup, 'db': db}):
                analyze = load(folder / 'analyze.py', 'review_analyze')
            row = {'CampaignName': 'test', 'Impressions': 100, 'Clicks': 10, 'Cost': 10,
                   'MetrikaRevenue': 20, 'attribution_level': 'exact'}
            for transactions, expected_cr in [(None, None), (0, 0.0), (2, 20.0)]:
                with self.subTest(base=base, transactions=transactions):
                    result = analyze.aggregate([{**row, 'MetrikaTransactions': transactions}], 'campaign')[0]
                    self.assertEqual(result['MetrikaTransactions'], transactions)
                    self.assertEqual(result['MetrikaCR'], expected_cr)
            result = analyze.total_row([{**row, 'MetrikaTransactions': 2}, {**row, 'MetrikaTransactions': None}])
            for key in ('MetrikaTransactions', 'MetrikaCR', 'MetrikaCPA', 'AOV'):
                self.assertIsNone(result[key])

    def test_link_privacy_and_known_draft_id(self):
        for base in BASES:
            folder = base / 'che-unisender-email-pipeline/scripts'
            builder = load(folder / 'build_tracking_urls.py', 'review_builder')
            draft = load(folder / 'validate_email_draft.py', 'review_draft')
            folder_script = folder / 'manage_pipeline_state.py'
            state = load(folder_script, 'review_state')
            for query in ('qa%40example.invalid=1', 'qa%40example.invalid=', 'qa%40example.invalid',
                          'email=', 'x=ok;PHONE=123', 'q=qa%40example.invalid'):
                with self.subTest(base=base, query=query):
                    for track in (True, False):
                        with self.assertRaises(ValueError):
                            builder.build({'placements': [{'id': 'article_1', 'url': 'https://example.invalid/item?' + query, 'track': track}]}, 'synthetic_digest')
                    result = draft.validate(draft_payload(query))
                    self.assertEqual(result['status'], 'blocked', result)
                    self.assertNotIn('qa@example.invalid', str(result))
            self.assertEqual(draft.validate(draft_payload('search=topic'))['status'], 'passed')
            for attr in ('href="https://example.invalid/item?qa%40example.invalid=1" ', 'data-tracking="operational" '):
                payload = draft_payload('search=topic')
                html = payload['html'].replace('<a href=', '<a ' + attr + 'href=', 1)
                if attr.startswith('data-tracking'):
                    html = html.replace('href="https://example.invalid/item-1?', 'data-tracking="content" href="https://example.invalid/item-1?', 1)
                self.assertEqual(draft.validate({**payload, 'html': html})['status'], 'blocked')
            for track in (True, False):
                result = builder.build({'placements': [{'id': 'article_1', 'url': 'https://example.invalid/item?search=topic&optional=', 'track': track}]}, 'synthetic_digest')
                self.assertIn('optional=', result['placements'][0]['url'])
            old = [{'draft_key': 'sample', 'status': 'created', 'message_id': 'SYNTHETIC_ID'}]
            for missing in ('', None, 'unknown', 'missing', '  ', 0, False):
                result = state.merge_lists(old, [{'draft_key': 'sample', 'message_id': missing}], 'draft_key')
                self.assertEqual(result[0]['message_id'], 'SYNTHETIC_ID')
            with self.assertRaises(ValueError):
                state.merge_lists(old, [{'draft_key': 'sample', 'message_id': 'OTHER'}], 'draft_key')
            self.assertEqual(state.merge_lists([{'draft_key': 'sample'}], [{'draft_key': 'sample', 'message_id': 'NEW'}], 'draft_key')[0]['message_id'], 'NEW')
            numeric = [{'draft_key': 'sample', 'status': 'created', 'message_id': 12345}]
            self.assertEqual(state.merge_lists(numeric, [{'draft_key': 'sample', 'message_id': 0}], 'draft_key')[0]['message_id'], 12345)
            self.assertEqual(state.merge_lists([{'draft_key': 'sample'}], [{'draft_key': 'sample', 'message_id': 12345}], 'draft_key')[0]['message_id'], 12345)
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                original = {'schema_version': 1, 'project_key': 'synthetic', 'state_revision': 1,
                            'updated_at': '2026-11-15T00:00:00+00:00', 'coverage': {},
                            **{key: [] for key in state.LIST_KEYS}, 'draft_registry': old}
                (folder / 'state.json').write_text(json.dumps(original))
                for missing in (0, False):
                    delta = {'project_key': 'synthetic', 'updated_at': '2026-11-16T00:00:00+00:00',
                             'draft_registry': [{'draft_key': 'sample', 'status': 'created', 'message_id': missing}]}
                    (folder / 'delta.json').write_text(json.dumps(delta))
                    result = subprocess.run([sys.executable, str(folder_script), 'merge', str(folder / 'state.json'),
                                             str(folder / 'delta.json'), '--output', str(folder / 'out.json')],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads((folder / 'out.json').read_text())['draft_registry'][0]['message_id'], 'SYNTHETIC_ID')


if __name__ == '__main__':
    unittest.main()
