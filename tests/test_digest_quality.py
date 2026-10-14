"""Offline regressions: publication evidence, event identity, and delivery QA."""
import copy
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parents[1] / 'skills/che-daily-ai-news-digest/scripts'
sys.path.insert(0, str(HERE))
with patch.dict(sys.modules, {'feedparser': types.ModuleType('feedparser'),
                             'openai': types.SimpleNamespace(OpenAI=Mock(side_effect=AssertionError('No model')))}):
    spec = importlib.util.spec_from_file_location('quality_collector', HERE / 'collect_and_send.py')
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)

class DigestQuality(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.entries = [{'title': f'Synthetic research announcement {i}',
                         'link': f'https://www.anthropic.com/news/fixture-{i}',
                         'source': 'Offline fixture',
                         'pub_date': (self.now - timedelta(hours=1)).isoformat()}
                        for i in range(5)]
        self.text = '\n'.join(f"{i}. {e['title']}\nИсточник: Fixture | {e['link']}" for i, e in enumerate(self.entries, 1))
        self.html = c.generate_html_digest(self.text)

    def test_rss_excludes_unknown_updated_only_and_future_dates(self):
        def item(**kw):
            return types.SimpleNamespace(title='A synthetic research announcement',
                                         link='https://www.anthropic.com/news/fixture', summary='', **kw)
        current = (self.now - timedelta(hours=1)).utctimetuple()
        records = [item(), item(updated_parsed=current), item(published_parsed=current),
                   item(published_parsed=(self.now + timedelta(hours=1)).utctimetuple()),
                   item(published_parsed=(self.now - timedelta(hours=40)).utctimetuple()),
                   item(published_parsed=(2026, 99, 1, 0, 0, 0, 0, 0, 0)),
                   item(published_parsed=current)]
        with patch.object(c, 'RSS_FEEDS', [{'url':'https://feed.fixture.test','name':'Fixture','lang':'en'}]), \
             patch.object(c.feedparser, 'parse', return_value=types.SimpleNamespace(entries=records), create=True):
            self.assertEqual(len(c.fetch_rss_entries()), 2)

    def test_same_title_different_articles_are_not_deleted(self):
        records = copy.deepcopy(self.entries[:2]); records[1]['title'] = records[0]['title']
        self.assertEqual(len(c.dedup_within_batch(records)), 2)
        for e in records: e['hash'] = c.news_hash(e['title'], e['link'])
        history = {'sent_hashes': [], 'sent_titles': [records[0]['title']], 'sent_entries': [records[0]]}
        self.assertEqual(c.full_dedup_pipeline(records[1:], history), records[1:])

    def test_same_article_tracking_variation_is_a_duplicate(self):
        records = copy.deepcopy(self.entries[:2])
        records[1]['link'] = records[0]['link'] + '?utm_source=rss#section'
        records[1]['title'] = 'Different translated headline for same article'
        self.assertEqual(len(c.dedup_within_batch(records)), 1)

    def test_only_verified_cross_source_event_identity_can_merge(self):
        records = copy.deepcopy(self.entries[:2])
        for e in records: e['event_id'] = 'synthetic-release-42'
        self.assertEqual(len(c.dedup_within_batch(records)), 2)
        for e in records: e['event_verified'] = True
        with patch.object(c, 'SOURCE_WEIGHTS', {'Offline fixture': 0.5, 'Primary fixture': 1.0}):
            records[1]['source'] = 'Primary fixture'
            self.assertEqual(c.dedup_within_batch(records), records[1:])

    def test_article_identity_preserves_case_and_meaningful_query(self):
        first = self.entries[0]
        for url in [first['link'].upper(), first['link'] + '?version=2']:
            other = dict(first, link=url)
            self.assertFalse(c.same_event(first, other))

    def test_exact_previous_article_is_removed_but_title_only_history_is_retained(self):
        entry = dict(self.entries[0]); entry['hash'] = c.news_hash(entry['title'], entry['link'])
        history = {'sent_entries':[entry], 'sent_titles':[], 'sent_hashes':[]}
        self.assertEqual(c.full_dedup_pipeline([entry],history), [])
        self.assertEqual(c.full_dedup_pipeline([entry],{'sent_titles':[entry['title']]}), [entry])

    def test_complete_evidence_passes(self):
        self.assertEqual(c.validate_generated_digest(self.text, self.html, self.entries, now=self.now), [])

    def test_missing_dates_unknown_sources_and_stale_entries_block(self):
        for field, value in [('pub_date', None), ('pub_date','bad-date'),
                             ('pub_date', self.now.replace(tzinfo=None).isoformat()),
                             ('pub_date',(self.now - timedelta(hours=40)).isoformat()),
                             ('pub_date',(self.now + timedelta(hours=1)).isoformat()),
                             ('link','https://www.anthropic.com/news/invented')]:
            with self.subTest(field=field, value=value):
                entries = copy.deepcopy(self.entries); entries[0][field] = value
                self.assertTrue(c.validate_generated_digest(self.text,self.html,entries,now=self.now))
        self.assertTrue(c.validate_generated_digest(self.text, self.html))

    def test_test_private_and_invalid_sources_block(self):
        for url in ['https://news.fixture.test/item','https://example.com/item','http://localhost/item',
                    'http://127.0.0.1/item','https://192.168.0.2/item','https://user:pass@93.184.216.34/item',
                    'https://www.anthropic.com:invalid/item']:
            with self.subTest(url=url):
                text = self.text.replace(self.entries[0]['link'],url)
                entries = copy.deepcopy(self.entries); entries[0]['link'] = url
                self.assertTrue(c.validate_generated_digest(text,c.generate_html_digest(text),entries,now=self.now))

    def test_malformed_ledger_returns_actionable_issue(self):
        self.assertTrue(c.validate_generated_digest(self.text,self.html,{'link':'bad'}))
        self.assertTrue(c.validate_generated_digest(self.text,self.html,[None]))

    def test_sources_are_one_per_item_and_html_matches(self):
        missing = self.text.replace('Источник: Fixture | ' + self.entries[0]['link'], '')
        # Still five total sources, but one news item has zero and another has two.
        shifted = missing + '\nИсточник: Fixture | ' + self.entries[0]['link']
        self.assertTrue(c.validate_generated_digest(shifted,c.generate_html_digest(shifted),self.entries,now=self.now))
        altered = self.html.replace(self.entries[0]['link'], 'https://www.anthropic.com/news/wrong')
        self.assertTrue(c.validate_generated_digest(self.text,altered,self.entries,now=self.now))

if __name__ == '__main__': unittest.main()
