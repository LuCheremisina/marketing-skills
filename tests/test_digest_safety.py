import unittest, sys, types, tempfile, json, os, importlib.util, io, contextlib
from pathlib import Path
from unittest.mock import patch, Mock
R=Path(__file__).resolve().parents[1]/'skills'
D=R/'che-daily-ai-news-digest/scripts'
sys.path.insert(0,str(D))
sys.modules['feedparser']=types.ModuleType('feedparser')
o=types.ModuleType('openai');o.OpenAI=Mock(side_effect=AssertionError('No paid API'));sys.modules['openai']=o
import collect_and_send as c
import send_digest as s
text='1. Synthetic research release\nИсточник: Fixture | https://news.fixture.test/one\n2. Synthetic product release\nИсточник: Fixture | https://news.fixture.test/two\n'
html='<!doctype html><html><div class="news-card"></div><div class="news-card"></div></html>'
class Safety(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'bundle.json'
  context={'date':'2026-11-16','footer_url':'','footer_label':''}
  self.path.write_text(json.dumps({'digest':text,'html':c.generate_html_digest(text,render_context=context),'render_context':context,'titles':['one','two'],'entries':[]}))
  self.gate=patch.object(c,'MIN_NEWS',2);self.gate.start()
 def tearDown(self):self.gate.stop();self.temp.cleanup()
 def test_prepare_even_legacy_dry_run_zero_cannot_deliver(self):
  entries=[{'title':'one','link':'https://news.fixture.test/one'},{'title':'two','link':'https://news.fixture.test/two'}]
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
 def test_empty_duplicate_invalid_recipients(self):
  for value in ['', '0','123,123']:
   with self.assertRaises(Exception):s.recipients(value)
 def test_industry_defaults_no_llm_and_requires_external_profile(self):
  spec=importlib.util.spec_from_file_location('industry',R/'che-industry-news-digest/scripts/collect_digest.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  cfg={'sources':[{'url':'https://news.fixture.test/rss'}]};p=Path(self.temp.name)/'profile.json';p.write_text(json.dumps(cfg))
  with patch.object(sys,'argv',['collect_digest.py','--config',str(p)]),patch.object(m,'fetch_rss_entries',return_value=[{}]),patch.object(m,'cluster_entries',return_value=[{}]),patch.object(m,'format_digest_raw',return_value='draft'),patch.object(m,'process_with_llm',side_effect=AssertionError('No OpenAI')):
   m.main()
  with self.assertRaises(ValueError):m.load_config(R/'che-industry-news-digest/references/config.example.json')
 def test_escape_untrusted_fields_and_preserve_safe_url(self):
  from html.parser import HTMLParser
  data=('1. <b>synthetic title</b>\n<b>description</b>\n'
        'Источник: <b>source</b> | https://news.fixture.test/?a=1&b=2\n'
        'Категория: <b>category</b> | Для кого: <b>audience</b>\n'
        'Что это значит для бизнеса: <b>insight</b>\n'
        '2. Another synthetic title\nИсточник: Fixture | https://news.fixture.test/two\n'
        '📊 Тренды дня:\n— <b>trend</b>\n')
  context={'date':'2026-11-16','footer_url':'https://news.fixture.test/?a=1&b=2','footer_label':'<b>footer</b>'}
  rendered=c.generate_html_digest(data,render_context=context)
  class Parser(HTMLParser):
   def __init__(self):super().__init__();self.bad=[];self.links=[]
   def handle_starttag(self,tag,attrs):
    if tag=='b':self.bad.append(tag)
    if tag=='a':self.links.append(dict(attrs))
  parsed=Parser();parsed.feed(rendered);self.assertEqual(parsed.bad,[])
  for field in ['synthetic title','description','source','category','audience','insight','trend','footer']:
   self.assertIn('&lt;b&gt;'+field+'&lt;/b&gt;',rendered)
  self.assertEqual(parsed.links[0]['href'],'https://news.fixture.test/?a=1&b=2')
 def test_reject_unsafe_url_and_unverified_bundle(self):
  for url in ['javascript:alert(1)','https://fixture.test/" onclick="x','https://u:p@example.invalid/','https://fixture.test/%zz','https://fixture.test:99999/']:
   with self.subTest(url=url):self.assertFalse(c.safe_http_url(url))
  bundle=json.loads(self.path.read_text())
  for invalid in [dict(bundle,html=bundle['html']+'<b>tampered</b>'),{k:v for k,v in bundle.items() if k!='render_context'}]:
   self.path.write_text(json.dumps(invalid));transport=Mock()
   with self.assertRaises(ValueError):s.deliver(self.path,[123],True,transport,'TEST')
   transport.assert_not_called()
 def test_each_card_requires_one_source(self):
  bad=('1. First synthetic title\nИсточник: X | https://news.fixture.test/a\n'
       'Источник: X | https://news.fixture.test/b\n2. Second synthetic title\n')
  self.assertTrue(c.validate_generated_digest(bad,c.generate_html_digest(bad)))
if __name__=='__main__':unittest.main()
