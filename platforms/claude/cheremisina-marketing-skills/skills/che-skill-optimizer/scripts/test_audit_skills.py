import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from audit_skills import audit

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'synthetic-skill'
        self.root.mkdir()
    def tearDown(self):
        self.tmp.cleanup()
    def write(self, body='', description='description: >-\n  Audits structured packages.\n\n  Applies when reviewing skills.'):
        (self.root / 'SKILL.md').write_text('---\nname: synthetic-skill\n' + description + '\n---\n# Example\n' + body)
    def codes(self):
        return {f['code'] for f in audit(self.root)['findings']}
    def test_multiline_description_and_blank_lines(self):
        self.write()
        self.assertEqual(audit(self.root)['status'], 'static-pass')
    def test_broken_link(self):
        self.write('[Resource](references/missing.md)')
        self.assertIn('missing-local-resource', self.codes())
    def test_link_escape(self):
        self.write('[Resource](../outside.md)')
        self.assertIn('resource-path-escape', self.codes())
    def test_duplicate_yaml(self):
        self.write(description='description: one\ndescription: two')
        self.assertIn('invalid-yaml', self.codes())
    def test_xml(self):
        self.write(description='description: "Audit <xml>"')
        self.assertIn('xml-description', self.codes())
    def test_no_sensitive_match_in_report(self):
        secret = 'ghp_' + 'Z' * 25
        self.write(secret)
        report = audit(self.root)
        self.assertIn('credential', self.codes())
        self.assertNotIn(secret, json.dumps(report))
    def test_reference_toc(self):
        self.write('[Reference](references/guide.md)')
        (self.root / 'references').mkdir()
        (self.root / 'references/guide.md').write_text('line\n' * 101)
        self.assertIn('reference-toc-recommendation', self.codes())
    def test_reference_crosslink_also_direct_is_allowed(self):
        self.write('[A](references/a.md)\n[B](references/b.md)')
        (self.root / 'references').mkdir()
        (self.root / 'references/a.md').write_text('[B](b.md#details)')
        (self.root / 'references/b.md').write_text('# Details')
        self.assertNotIn('nested-reference-navigation', self.codes())
        self.assertNotIn('missing-local-resource', self.codes())
    def test_reference_only_reachable_indirectly_is_advisory(self):
        self.write('[A](references/a.md)')
        (self.root / 'references').mkdir()
        (self.root / 'references/a.md').write_text('[B](b.md)')
        (self.root / 'references/b.md').write_text('# Details')
        self.assertIn('nested-reference-navigation', self.codes())
        self.assertNotIn('missing-local-resource', self.codes())
    def test_nested_directory_direct_resource_is_allowed(self):
        self.write('[A](references/a.md)\n[B](references/nested/b.md)')
        (self.root / 'references/nested').mkdir(parents=True)
        (self.root / 'references/a.md').write_text('[B](nested/b.md)')
        (self.root / 'references/nested/b.md').write_text('# Details')
        self.assertNotIn('nested-reference-navigation', self.codes())
    def test_symlink_not_followed(self):
        self.write()
        (self.root / 'outside.txt').symlink_to('/etc/passwd')
        self.assertIn('symlink-resource', self.codes())
    def test_arbitrary_cwd_and_json(self):
        self.write()
        script = Path(__file__).resolve().with_name('audit_skills.py')
        result = subprocess.run([sys.executable, str(script), str(self.root), '--json', str(Path(self.tmp.name) / 'report.json')], cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((Path(self.tmp.name) / 'report.json').read_text())['summary']['skills'], 1)
    def test_missing_input(self):
        script = Path(__file__).resolve().with_name('audit_skills.py')
        result = subprocess.run([sys.executable, str(script), str(self.root / 'missing')], cwd='/', capture_output=True)
        self.assertEqual(result.returncode, 2)
    def test_report_cannot_overwrite_package(self):
        self.write()
        original = (self.root / 'SKILL.md').read_bytes()
        script = Path(__file__).resolve().with_name('audit_skills.py')
        result = subprocess.run([sys.executable, str(script), str(self.root), '--json', str(self.root / 'SKILL.md')], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.root / 'SKILL.md').read_bytes(), original)
    def test_utf8_metrics(self):
        self.write('Тест')
        report = audit(self.root)
        self.assertGreater(report['metrics']['entrypoint_utf8_bytes'], report['metrics']['entrypoint_characters'])
    def test_invalid_yaml(self):
        self.write(description='description: [broken')
        self.assertIn('invalid-yaml', self.codes())

if __name__ == '__main__':
    unittest.main()
