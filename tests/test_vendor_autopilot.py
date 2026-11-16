"""Offline plan-gate checks using only temporary fixture files."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'vendor/skills/autopilot/tools/ap.py'

def load():
    spec=importlib.util.spec_from_file_location('autopilot_plan_gate',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class AutopilotPlanGate(unittest.TestCase):
    def test_missing_manifest_and_ticket_files_fail(self):
        module=load()
        with tempfile.TemporaryDirectory() as d,patch.object(module,'A',d):
            folder=Path(d)/'run';folder.mkdir();state={'dir':'run','tickets':[]}
            failures=module.check_plan(state)
            self.assertTrue(any('manifest.md' in x for x in failures))
            self.assertTrue(any('тасков' in x for x in failures))
            (folder/'manifest.md').write_text('| ID | name | status | why | where |\n')
            self.assertTrue(any('нет распознанных требований' in x for x in module.check_plan(state)))

    def test_missing_ticket_files_do_not_reuse_stale_state(self):
        module=load()
        with tempfile.TemporaryDirectory() as d,patch.object(module,'A',d):
            folder=Path(d)/'run';folder.mkdir();(folder/'manifest.md').write_text('| R01 | Example | in-ticket | reason | T01 |\n')
            state={'dir':'run','tickets':[{'id':'01','requirements':['R01'],'zone':['src/'],'wave':1,'blockedBy':[]}]}
            self.assertTrue(any('нет файлов тасков' in x for x in module.check_plan(state)))

    def test_linked_requirements_and_tickets_pass(self):
        module=load()
        with tempfile.TemporaryDirectory() as d,patch.object(module,'A',d):
            folder=Path(d)/'run';(folder/'tickets').mkdir(parents=True)
            (folder/'manifest.md').write_text('| R01 | Example | in-spec | reason | — |\n')
            (folder/'tickets/01-test.md').write_text('# 01 - test\n**Требования:** R01\n**Зона:** `src/`\n**Волна:** 1\n')
            self.assertEqual(module.check_plan({'dir':'run','tickets':[]}),[])

if __name__=='__main__':unittest.main()
