"""Regression tests for article source URLs and vendor probe recovery."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASES = [ROOT/'skills', ROOT/'platforms/claude/cheremisina-marketing-skills/skills']
PROBE = ROOT/'vendor/skills/turnstile-spin/scripts/auth-probe.sh'

def load(path):
    spec=importlib.util.spec_from_file_location('article_url_review',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class OtherRegressions(unittest.TestCase):
    def test_article_urls_require_https_and_host(self):
        for base in BASES:
            script=base/'che-expert-article-workflow/scripts/validate_article.py'
            m=load(script)
            for bad in ('https:bad','https:///missing','https://[invalid','https://example.invalid:bad','https://user:pass@example.invalid','https://@example.invalid','https://bad host/path','http://example.invalid'):
                with self.subTest(base=base,bad=bad):self.assertFalse(m.is_https(bad))
            for good in ('https://example.invalid/path','https://example.invalid:443/path'):
                self.assertTrue(m.is_https(good))
            claim={'claim_id':'c1','text':'Synthetic fact','claim_kind':'external_fact','materiality':'material','status':'verified','source_type':'official','source_url':'https:bad','source_date':'2026-01-01','checked_at':'2026-01-01','locator':'p1','article_locator':'p1'}
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'claims.jsonl';p.write_text(json.dumps(claim)+'\n')
                errors=[];m.read_claims(p,errors);self.assertTrue(any('source_url' in x for x in errors))

    @unittest.skipUnless(os.name=='posix' and shutil.which('bash'), 'requires bash')
    def test_probe_reports_failed_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); fake=folder/'curl'
            fake.write_text("""#!/bin/sh
case " $* " in
 *' -X POST '*)
  if [ "$FAKE_POST_MODE" = validation ]; then printf '%s\\n%s' '{"success":false,"errors":[{"code":123}]}' '400'
  else printf '%s\\n%s' '{"success":true,"result":{"sitekey":"SYNTHETIC_SITEKEY"}}' '200'; fi ;;
 *' -X DELETE '*) printf '%s' "$FAKE_DELETE_STATUS" ;;
 *) exit 9 ;;
esac
""")
            fake.chmod(0o755)
            for mode,delete,expected in [('created','500','cleanup_failed'),('created','204','ok'),('validation','500','ok')]:
                with self.subTest(mode=mode,delete=delete):
                    env={'PATH':str(folder)+os.pathsep+str(Path(sys.executable).parent)+os.pathsep+os.defpath,
                         'TMPDIR':tmp,'CLOUDFLARE_API_TOKEN':'SYNTHETIC_TOKEN','CLOUDFLARE_ACCOUNT_ID':'SYNTHETIC_ACCOUNT',
                         'FAKE_POST_MODE':mode,'FAKE_DELETE_STATUS':delete}
                    result=subprocess.run([shutil.which('bash'),str(PROBE)],env=env,text=True,capture_output=True,timeout=20)
                    self.assertEqual(result.returncode,0,result.stderr);data=json.loads(result.stdout)
                    self.assertEqual(data['status'],expected)
                    if expected=='cleanup_failed':
                        self.assertEqual(data['sitekey'],'SYNTHETIC_SITEKEY')
                        self.assertEqual(data['http_code'],'500')
                    self.assertNotIn('SYNTHETIC_TOKEN',result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
