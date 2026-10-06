"""Offline integration: source-separated engine -> management report, without API calls."""
from pathlib import Path
from datetime import date,timedelta
import tempfile,os,json,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_report as report

class AdapterTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
  self.env=patch.dict(os.environ,{'DIRECT_ANALYTICS_DATA_DIR':str(self.base)});self.env.start()
  self.engine=report.load_engine(Path(__file__).resolve().parents[2]/'direct-analytics-skill')
  # Modules can be reused in a test session, so bind the external synthetic config root explicitly.
  self.engine['setup'].BASE_DIR=self.base
  (self.base/'synthetic').mkdir();(self.base/'synthetic/config.json').write_text(json.dumps({'GUARDRAILS':{},'REPORT_TIMEZONE':'UTC','ATTRIBUTION_MODE':'parallel'}))
  self.day=date(2020,2,1)
  with self.engine['db'].CacheDB('synthetic') as cache:
   for n in range(30):
    day=(self.day-timedelta(days=n)).isoformat()
    row={'Date':day,'CampaignId':'1','CampaignName':'Synthetic campaign','Cost':100,'Clicks':10,'Impressions':100,'MetrikaRevenue':500,'MetrikaTransactions':2,'attribution_level':'exact'}
    unpaired={**row,'CampaignId':'2','Cost':100,'MetrikaRevenue':None,'MetrikaTransactions':None,'attribution_level':'unpaired_direct'}
    for source,scope in [('direct','campaign'),('metrika','sessions'),('metrika','ecommerce')]:cache.save_fact(source,scope,day,[row] if source=='direct' else [],{'complete':True})
    cache.save_fact('reconciliation','campaign',day,[row,unpaired],{'complete':True,'summary':{'unattributed_metrika_revenue':300}})
 def tearDown(self):self.env.stop();self.temp.cleanup()
 def test_cross_source_ratios_use_matched_cost_only_and_unattributed_separate(self):
  data=report.build_dataset(self.engine,'synthetic',self.day,'daily',None,0)
  totals=data['periods']['target']['totals']
  self.assertEqual(totals['Cost'],200);self.assertEqual(totals['ROAS'],500)
  self.assertEqual(data['match_summary']['unattributed_metrika_revenue'],9000)
  self.assertEqual(data['data_status'],'complete')
  self.assertEqual(data['forecast'].get('revenue_30d'),None)
  markdown=report.render_report(data)
  self.assertIn('Direct÷Метка',markdown);self.assertNotIn('25.0%',markdown)
 def test_missing_source_day_is_limited_without_fake_zero(self):
  with self.engine['db'].CacheDB('synthetic') as cache:cache.save_fact('metrika','sessions',self.day.isoformat(),[],{'complete':False,'error':'synthetic unavailable'})
  data=report.build_dataset(self.engine,'synthetic',self.day,'daily',None,0)
  self.assertEqual(data['data_status'],'limited')
  self.assertIn(self.day.isoformat(),data['checks']['data_complete']['missing_dates']['target'])
 def test_cli_defaults_no_external_model_and_produces_files_from_arbitrary_cwd(self):
  self.assertTrue(report.parse_args([]).no_llm)
  exit_code=report.main(['--engine-dir',str(Path(__file__).resolve().parents[2]/'direct-analytics-skill'),'--project','synthetic','--date',self.day.isoformat(),'--no_collect','--output_dir',str(self.base/'output')])
  self.assertEqual(exit_code,0)
  payload=json.loads((self.base/'output/reports/report_2020-02-01_daily.json').read_text())
  self.assertEqual(payload['llm_status'],'disabled')

if __name__=='__main__':unittest.main()
