"""Context-sensitive scoring regression; no network or crawl dependency needed."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ContextualSEOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / 'skills/che-seo-geo-auditor/scripts/audit_website.py'
        tree = ast.parse(source.read_text())
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'calculate_score']
        scope = dict(SCORE_CRITICAL=15, SCORE_HIGH=10, SCORE_MEDIUM=5, SCORE_LOW=2)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), scope)
        cls.score = staticmethod(scope['calculate_score'])

    def fixture(self):
        return {
            'https': True,
            'robots_txt': {'found': True, 'search_bots_blocked': [], 'ai_bots_blocked': []},
            'llms_txt': {'found': True},
            'content': {'word_count': 500, 'has_faq_section': True},
            'links': {'internal_unique': 8},
            'headings': {'h1': ['Synthetic page']},
            'meta_tags': {'title': 'Synthetic title', 'meta_description': 'Synthetic description',
                          'viewport': 'width=device-width', 'canonical': 'https://example.com/',
                          'open_graph': True, 'twitter_cards': True, 'html_lang': 'en', 'favicon': True},
            'schema': {'found': True},
            'sitemap': {'found': True},
            'eeat': {'about_page': True, 'author_page': True, 'privacy_policy': True},
        }

    def test_missing_faq_and_llms_do_not_reduce_score(self):
        good = self.fixture()
        absent = deepcopy(good)
        absent['llms_txt']['found'] = False
        absent['content']['has_faq_section'] = False
        self.assertEqual(self.score(good), self.score(absent))

    def test_intentional_ai_restriction_is_not_unconditional_penalty(self):
        good = self.fixture()
        policy = deepcopy(good)
        policy['robots_txt']['ai_bots_blocked'] = ['GPTBot', 'OAI-SearchBot']
        self.assertEqual(self.score(good), self.score(policy))
        policy['audit_context'] = {'required_ai_bots': ['OAI-SearchBot']}
        self.assertEqual(self.score(good)[0] - 10, self.score(policy)[0])

    def test_search_restriction_requires_explicit_public_intent(self):
        good = self.fixture()
        policy = deepcopy(good)
        policy['robots_txt']['search_bots_blocked'] = ['Googlebot']
        self.assertEqual(self.score(good), self.score(policy))
        policy['audit_context'] = {'public_indexing_intended': True}
        self.assertEqual(self.score(good)[0] - 15, self.score(policy)[0])

    def test_absent_optional_robots_file_is_not_critical(self):
        good = self.fixture()
        absent = deepcopy(good)
        absent['robots_txt']['found'] = False
        self.assertEqual(self.score(good), self.score(absent))

if __name__ == '__main__':
    unittest.main()
