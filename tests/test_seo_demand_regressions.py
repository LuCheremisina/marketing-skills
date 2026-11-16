"""Regression tests for SEO demand data, HTML/Markdown and report paths."""
import html.parser
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASES = [ROOT / 'skills', ROOT / 'platforms/claude/cheremisina-marketing-skills/skills']

class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []; self.data = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
    def handle_data(self, value):
        self.data.append(value)

class SeoDemandTests(unittest.TestCase):
    def invoke(self, script, folder, env=None):
        return subprocess.run([sys.executable, str(script)], cwd=folder, env=env, text=True, capture_output=True)

    def test_webmaster_formats_and_unknowns(self):
        for base in BASES:
            script = base / 'che-seo-demand-analytics/scripts/analyze_correlation.py'
            with self.subTest(base=base), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp)
                (p/'wordstat_data.json').write_text(json.dumps({'top_100':[{'phrase':'ёжик сад','count':200},{'phrase':'unmatched','count':5}]},ensure_ascii=False))
                (p/'metrika_data.json').write_text(json.dumps({'pages_organic':[]}))
                csv = p/'webmaster_data.csv'
                csv.write_text('Query,Impressions,Clicks,Avg. position\nежик сад,250,10,3\n',encoding='utf-8')
                result = self.invoke(script,p); self.assertEqual(result.returncode,0,result.stderr)
                rows = json.loads((p/'final_correlation.json').read_text())
                self.assertEqual((rows[0]['total_shows'],rows[0]['status']),(250,'ТОП-3'))
                self.assertEqual((rows[1]['status'],rows[1]['best_position'],rows[1]['total_shows']),('Нет данных',None,None))
                csv.unlink()
                data = p/'webmaster_data.json'
                data.write_text(json.dumps({'queries':[{'query':'ежик сад','shows':250,'clicks':10,'position':3}]},ensure_ascii=False))
                result = self.invoke(script,p); self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads((p/'final_correlation.json').read_text()),rows)
                data.write_text(json.dumps({'queries':[{'query':'ежик сад','clicks':10,'position':3}]}))
                (p/'final_correlation.json').unlink()
                result = self.invoke(script,p); self.assertNotEqual(result.returncode,0)
                self.assertFalse((p/'final_correlation.json').exists())

    def test_report_escapes_and_rejects_unsafe_paths(self):
        for base in BASES:
            script = base / 'che-seo-demand-analytics/scripts/generate_reports.py'
            with self.subTest(base=base), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp); out = p/'OUTPUTS'; out.mkdir()
                row={'phrase':'<img id="fake">|[link](javascript:fake)','demand_count':10,'wm_related_count':0,'best_position':0,'total_shows':0,'total_clicks':0,'status':'Не видим'}
                unknown={**row,'phrase':'unmatched','best_position':None,'total_shows':None,'total_clicks':None,'status':'Нет данных'}
                (p/'final_correlation.json').write_text(json.dumps([row,unknown],ensure_ascii=False))
                (p/'config.json').write_text(json.dumps({'domain':'example.invalid','niche':'<b>fake</b>','region':'a|b'}))
                env={**os.environ,'OUTPUT_DIR':str(out)}
                result=self.invoke(script,p,env);self.assertEqual(result.returncode,0,result.stderr)
                parser=Parser();parser.feed((p/'dashboard.html').read_text())
                self.assertFalse(any(tag in {'img','b'} for tag,_ in parser.tags))
                self.assertIn(row['phrase'],''.join(parser.data))
                markdown=(p/'report.md').read_text()
                self.assertNotIn('<b>',markdown); self.assertIn('&lt;b&gt;',markdown)
                self.assertNotIn('<img',markdown); self.assertIn('&lt;img',markdown); self.assertIn(r'\|',markdown); self.assertIn(r'\[link\]',markdown)
                self.assertIn('Нет данных',markdown)
                result_dirs=list(out.iterdir());self.assertEqual(len(result_dirs),1)
                self.assertTrue((result_dirs[0]/'dashboard.html').is_file())
                for domain in ('probe/../../escape','escape\\\\other','example.invalid\x1b]0;title\x07'):
                    (p/'config.json').write_text(json.dumps({'domain':domain,'niche':'safe','region':'safe'}))
                    result=self.invoke(script,p,env);self.assertNotEqual(result.returncode,0);self.assertNotIn('\x1b',result.stdout)

    def test_preexisting_symlink_cannot_overwrite_target(self):
        for base in BASES:
            script=base/'che-seo-demand-analytics/scripts/generate_reports.py'
            with self.subTest(base=base), tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp); out=p/'OUTPUTS';out.mkdir();victim=p/'external';victim.write_text('UNCHANGED')
                (p/'config.json').write_text(json.dumps({'domain':'example.invalid','niche':'safe','region':'safe'}))
                row={'phrase':'safe','demand_count':10,'wm_related_count':0,'best_position':0,'total_shows':0,'total_clicks':0,'status':'Не видим'}
                (p/'final_correlation.json').write_text(json.dumps([row],ensure_ascii=False))
                (p/'dashboard.html').symlink_to(victim)
                result=self.invoke(script,p,{**os.environ,'OUTPUT_DIR':str(out)})
                self.assertNotEqual(result.returncode,0);self.assertEqual(victim.read_text(),'UNCHANGED')
                (p/'dashboard.html').unlink()
                result=self.invoke(script,p,{**os.environ,'OUTPUT_DIR':str(out)})
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(victim.read_text(),'UNCHANGED')

if __name__=='__main__': unittest.main()
