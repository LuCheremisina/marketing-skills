"""Offline digest checks. Stub optional providers; never send, fetch RSS, or call a model."""
import sys,types,os,importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
HERE=Path(__file__).resolve().parent
class DigestTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.env=patch.dict(os.environ,{'DRY_RUN':'1','DIGEST_DATA_DIR':self.temp.name,'MIN_NEWS':'2','MAX_NEWS':'10'})
  self.env.start();sys.path.insert(0,str(HERE))
  stub=types.ModuleType('openai');stub.OpenAI=Mock(side_effect=AssertionError('External model must not be called'))
  self.modules=patch.dict(sys.modules,{'openai':stub,'feedparser':types.ModuleType('feedparser')});self.modules.start()
  spec=importlib.util.spec_from_file_location('offline_digest',HERE/'collect_and_send.py');self.digest=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.digest)
  self.text='1. Synthetic research release\nИсточник: Fixture | https://news.fixture.test/one\n2. Synthetic product release\nИсточник: Fixture | https://news.fixture.test/two\n'
  self.html='<!doctype html><html><div class="news-card"></div><div class="news-card"></div></html>'
 def tearDown(self):self.modules.stop();self.env.stop();self.temp.cleanup()
 def test_runtime_state_is_outside_skill_and_dry_run_needs_no_delivery_token(self):
  self.assertTrue(self.digest.DRY_RUN)
  self.assertEqual(self.digest.SUBSCRIBERS_FILE.parent,Path(self.temp.name))
  self.assertEqual(self.digest.RUN_HISTORY_FILE.parent,Path(self.temp.name))
 def test_missing_direct_source_and_invalid_html_block_delivery(self):
  self.assertEqual(self.digest.validate_generated_digest(self.text,self.html),[])
  self.assertTrue(self.digest.validate_generated_digest(self.text.replace('Источник: Fixture | https://news.fixture.test/two',''),self.html))
  self.assertTrue(self.digest.validate_generated_digest(self.text,self.html.replace('</html>','')))
 def test_event_dedup_keeps_one_authoritative_source(self):
  entries=[{'title':'Synthetic launch of new search assistant','source':'Fixture one','link':'https://news.fixture.test/one'}, {'title':'Synthetic launch of new search assistant','source':'Fixture two','link':'https://news.fixture.test/two'}]
  self.assertEqual(len(self.digest.dedup_within_batch(entries)),1)
 def test_delivery_error_does_not_log_secret_embedded_in_request_url(self):
  import io,contextlib
  d=self.digest;d.TELEGRAM_BOT_TOKEN='SYNTHETIC_FAKE_TOKEN'
  captured=io.StringIO()
  with patch.object(d.requests,'post',side_effect=RuntimeError('request URL contains SYNTHETIC_FAKE_TOKEN')),contextlib.redirect_stdout(captured):
   self.assertFalse(d.send_html_digest_to_chat(0,self.html,'fixture'))
  self.assertNotIn('SYNTHETIC_FAKE_TOKEN',captured.getvalue())
  self.assertIn('RuntimeError',captured.getvalue())
 def test_full_dry_run_does_not_send_or_update_sent_history(self):
  d=self.digest
  entries=[{'title':'Synthetic item one','source':'Fixture','link':'https://news.fixture.test/one'},{'title':'Synthetic item two','source':'Fixture','link':'https://news.fixture.test/two'}]
  with patch.object(d,'fetch_rss_entries',return_value=entries),patch.object(d,'full_dedup_pipeline',return_value=entries),patch.object(d,'apply_post_filter',return_value=entries),patch.object(d,'run_enrichment_pipeline',return_value=(entries,[])),patch.object(d,'process_with_llm',return_value=self.text),patch.object(d,'generate_html_digest',return_value=self.html),patch.object(d,'ensure_bot_running') as bot,patch.object(d,'send_telegram_message') as send,patch.object(d,'save_history') as history:
   d.main();bot.assert_not_called();send.assert_not_called();history.assert_not_called()
  import json
  records=[json.loads(x) for x in d.RUN_HISTORY_FILE.read_text().splitlines()]
  self.assertEqual(records[-1]['status'],'dry_run')
if __name__=='__main__':unittest.main()
