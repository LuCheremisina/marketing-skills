"""Offline digest checks. Stub optional providers; never send, fetch RSS, or call a model."""
import sys,types,os,importlib.util,tempfile,unittest
from pathlib import Path
from datetime import datetime, timezone
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
  self.text='1. Synthetic research release\nИсточник: Fixture | https://www.anthropic.com/news/offline-one\n2. Synthetic product release\nИсточник: Fixture | https://www.anthropic.com/news/offline-two\n'
  self.html=self.digest.generate_html_digest(self.text)
  self.entries=[{'title':'Synthetic item '+name,'source':'Fixture','link':'https://www.anthropic.com/news/offline-'+name,'pub_date':datetime.now(timezone.utc).isoformat()} for name in ['one','two']]
 def tearDown(self):self.modules.stop();self.env.stop();self.temp.cleanup()
 def test_runtime_state_is_outside_skill_and_dry_run_needs_no_delivery_token(self):
  self.assertTrue(self.digest.DRY_RUN)
  self.assertEqual(self.digest.SUBSCRIBERS_FILE.parent,Path(self.temp.name))
  self.assertEqual(self.digest.RUN_HISTORY_FILE.parent,Path(self.temp.name))
 def test_missing_direct_source_and_invalid_html_block_delivery(self):
  self.assertEqual(self.digest.validate_generated_digest(self.text,self.html,self.entries),[])
  self.assertTrue(self.digest.validate_generated_digest(self.text.replace('Источник: Fixture | https://www.anthropic.com/news/offline-two',''),self.html,self.entries))
  self.assertTrue(self.digest.validate_generated_digest(self.text,self.html.replace('</html>',''),self.entries))
 def test_title_similarity_alone_preserves_separate_events(self):
  entries=[{'title':'Synthetic launch of new search assistant','source':'Fixture one','link':'https://www.anthropic.com/news/offline-one'}, {'title':'Synthetic launch of new search assistant','source':'Fixture two','link':'https://www.anthropic.com/news/offline-two'}]
  self.assertEqual(len(self.digest.dedup_within_batch(entries)),2)
 def test_full_dry_run_does_not_send_or_update_sent_history(self):
  d=self.digest
  entries=self.entries
  with patch.object(d,'fetch_rss_entries',return_value=entries),patch.object(d,'full_dedup_pipeline',return_value=entries),patch.object(d,'apply_post_filter',return_value=entries),patch.object(d,'run_enrichment_pipeline',return_value=(entries,[])),patch.object(d,'process_with_llm',return_value=self.text),patch.object(d,'generate_html_digest',return_value=self.html),patch.object(d,'save_history') as history:
   d.main();history.assert_not_called()
  import json
  records=[json.loads(x) for x in d.RUN_HISTORY_FILE.read_text().splitlines()]
  self.assertEqual(records[-1]['status'],'dry_run')
if __name__=='__main__':unittest.main()
