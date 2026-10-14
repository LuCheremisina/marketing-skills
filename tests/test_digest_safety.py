import unittest, sys, types, tempfile, json, os, importlib.util, io, contextlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
R=Path(__file__).resolve().parents[1]/'skills'
D=R/'che-daily-ai-news-digest/scripts'
sys.path.insert(0,str(D))
sys.modules['feedparser']=types.ModuleType('feedparser')
o=types.ModuleType('openai');o.OpenAI=Mock(side_effect=AssertionError('No paid API'));sys.modules['openai']=o
import collect_and_send as c
import send_digest as s
text='1. Synthetic research release\nИсточник: Fixture | https://www.anthropic.com/news/offline-one\n2. Synthetic product release\nИсточник: Fixture | https://www.anthropic.com/news/offline-two\n'
html=c.generate_html_digest(text)
class Safety(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'bundle.json'
  self.path.write_text(json.dumps({'digest':text,'html':html,'titles':['one','two'],'entries':[{'title':title,'link':url,'pub_date':datetime.now(timezone.utc).isoformat()} for title,url in [('one','https://www.anthropic.com/news/offline-one'),('two','https://www.anthropic.com/news/offline-two')]]}))
  self.gate=patch.object(c,'MIN_NEWS',2);self.gate.start()
 def tearDown(self):self.gate.stop();self.temp.cleanup()
 def test_prepare_even_legacy_dry_run_zero_cannot_deliver(self):
  entries=json.loads(self.path.read_text())['entries']
  for entry in entries:entry['pub_date_dt']=datetime.now(timezone.utc)
  with patch.dict(os.environ,{'DRY_RUN':'0','DIGEST_DATA_DIR':self.temp.name}),patch.object(c,'RUN_HISTORY_FILE',Path(self.temp.name)/'runs.jsonl'),patch.object(c,'load_history',return_value={'sent_hashes':[],'sent_titles':[]}),patch.object(c,'fetch_rss_entries',return_value=entries),patch.object(c,'full_dedup_pipeline',return_value=entries),patch.object(c,'apply_post_filter',return_value=entries),patch.object(c,'run_enrichment_pipeline',return_value=(entries,[])),patch.object(c,'process_with_llm',return_value=text),patch.object(c,'generate_html_digest',return_value=html),patch.object(c,'extract_used_entries',return_value=entries),patch.object(c,'save_history') as save,patch('subprocess.Popen',side_effect=AssertionError('No background')),patch.dict(sys.modules, {'requests': types.SimpleNamespace(post=Mock(side_effect=AssertionError('No delivery')))}):
   c.main();save.assert_not_called();self.assertTrue((Path(self.temp.name)/'prepared-digest.json').exists())
 def test_no_confirmation_no_transport(self):
  transport=Mock()
  with self.assertRaises(ValueError):s.deliver(self.path,[123],transport=transport,token='TEST')
  transport.assert_not_called()
 def test_bad_qa_no_transport(self):
  self.path.write_text(json.dumps({'digest':text,'html':'bad'}));transport=Mock()
  with self.assertRaises(ValueError):s.deliver(self.path,[123],True,transport,'TEST')
  transport.assert_not_called()
 def test_exact_recipients_partial_retry_and_history(self):
  good=Mock();good.json.return_value={'ok':True};transport=Mock(side_effect=[good,RuntimeError('TEST_SECRET_URL')])
  with patch.object(c,'load_history',return_value={}),patch.object(c,'save_history') as save:
   with contextlib.redirect_stdout(io.StringIO()) as captured: result=s.deliver(self.path,[123,456],True,transport,'TEST')
   self.assertNotIn('TEST_SECRET_URL',captured.getvalue());self.assertEqual(result['failed'],1);save.assert_not_called()
   retry=Mock(return_value=good);result=s.deliver(self.path,[123,456],True,retry,'TEST');self.assertEqual(retry.call_count,1);self.assertEqual(retry.call_args.kwargs['data']['chat_id'],456);save.assert_called_once()
   repeat=Mock();self.assertEqual(s.deliver(self.path,[123,456],True,repeat,'TEST')['status'],'already_sent');repeat.assert_not_called()
 def test_stale_bundle_blocks_before_transport(self):
  bundle=json.loads(self.path.read_text());bundle['entries'][0]['pub_date']=(datetime.now(timezone.utc)-timedelta(hours=40)).isoformat();self.path.write_text(json.dumps(bundle));transport=Mock()
  with self.assertRaises(ValueError):s.deliver(self.path,[123],True,transport,'TEST')
  transport.assert_not_called()
 def test_empty_duplicate_invalid_recipients(self):
  for value in ['', '0','123,123']:
   with self.assertRaises(Exception):s.recipients(value)
 def test_industry_defaults_no_llm_and_requires_external_profile(self):
  spec=importlib.util.spec_from_file_location('industry',R/'che-industry-news-digest/scripts/collect_digest.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  cfg={'sources':[{'url':'https://news.fixture.test/rss'}]};p=Path(self.temp.name)/'profile.json';p.write_text(json.dumps(cfg))
  with patch.object(sys,'argv',['collect_digest.py','--config',str(p)]),patch.object(m,'fetch_rss_entries',return_value=[{}]),patch.object(m,'cluster_entries',return_value=[{}]),patch.object(m,'format_digest_raw',return_value='draft'),patch.object(m,'process_with_llm',side_effect=AssertionError('No OpenAI')):
   m.main()
  with self.assertRaises(ValueError):m.load_config(R/'che-industry-news-digest/references/config.example.json')
if __name__=='__main__':unittest.main()
