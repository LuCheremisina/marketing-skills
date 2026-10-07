#!/usr/bin/env python3
"""Build the complete authored plugin folder for the Claude directory."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'platforms' / 'claude' / 'cheremisina-marketing-skills'

def build():
    # Delete only this generated output, never source skills or local installations.
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    shutil.copytree(ROOT / 'skills', DEST / 'skills', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ['LICENSE', 'AUTHOR.md']:
        shutil.copyfile(ROOT / name, DEST / name)
    manifest = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
    manifest['name'] = 'cheremisina-marketing-skills'
    manifest['author']['name'] = 'Lyubov Cheremisina'
    manifest['icon'] = './.claude-plugin/icon.png'
    manifest['documentationUrl'] = 'https://github.com/LuCheremisina/marketing-skills/blob/main/docs/INSTALL-PLUGIN.md'
    manifest['privacyPolicyUrl'] = 'https://github.com/LuCheremisina/marketing-skills/blob/main/docs/PLUGIN-PRIVACY.md'
    manifest['termsOfServiceUrl'] = 'https://github.com/LuCheremisina/marketing-skills/blob/main/LICENSE'
    manifest['supportUrl'] = 'https://github.com/LuCheremisina/marketing-skills/issues'
    (DEST / '.claude-plugin').mkdir()
    (DEST / '.claude-plugin/plugin.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(ROOT / 'assets/claude-directory-icon.png', DEST / '.claude-plugin/icon.png')
    (DEST / 'README.md').write_text((ROOT / 'docs/CLAUDE-DIRECTORY-README.md').read_text())
    print(json.dumps({'folder': str(DEST), 'skills': len(list((DEST / 'skills').glob('*/SKILL.md'))), 'files': len([p for p in DEST.rglob('*') if p.is_file()])}))

if __name__ == '__main__':
    build()
