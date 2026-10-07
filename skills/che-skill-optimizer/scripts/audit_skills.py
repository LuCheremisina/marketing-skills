#!/usr/bin/env python3
"""Read-only static Agent Skills audit. Reports never contain matched private text."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
try:
    import yaml
except ImportError:
    print('Missing dependency: PyYAML 6+. Install in an approved environment.', file=sys.stderr)
    raise SystemExit(2)

LINK = re.compile(r'\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)')
PRIVATE_PATTERNS = {
    'personal-path': re.compile(r'(?:/Users/|/home/)[A-Za-z0-9_.-]+/'),
    'credential': re.compile(r'\b(?:ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9]{24,})\b'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'email-address': re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I),
}
PUBLIC_LINKS = ('https://cheremisina.ru', 'https://cheremisina.online', 'https://github.com/LuCheremisina/marketing-skills')


def local_targets(text, parent):
    """Resolve real Markdown resources relative to the document, not cwd."""
    link_text = re.sub(r'```.*?```', '', text, flags=re.S)
    for match in LINK.finditer(link_text):
        target = match.group(1).strip('<>')
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        target = target.split('#')[0].split('?')[0]
        if target:
            yield (parent / target).resolve()


def audit(package):
    package = Path(package).resolve()
    findings = []
    def add(level, code, path='SKILL.md', line=None):
        item = {'severity': level, 'code': code, 'file': str(path)}
        if line is not None:
            item['line'] = line
        findings.append(item)
    entry = package / 'SKILL.md'
    if entry.is_symlink():
        add('error', 'symlink-entrypoint')
        return {'id': package.name, 'findings': findings, 'status': 'error'}
    try:
        raw = entry.read_bytes()
        source = raw.decode('utf-8')
    except (OSError, UnicodeError):
        add('error', 'unreadable-entrypoint')
        return {'id': package.name, 'findings': findings, 'status': 'error'}
    normalized = source.replace('\r\n', '\n')
    front = re.match(r'\A---\n(.*?)\n---(?:\n|$)', normalized, re.S)
    metadata = {}
    body = normalized
    if not front:
        add('error', 'missing-frontmatter')
    else:
        try:
            class UniqueLoader(yaml.SafeLoader):
                pass
            def unique_mapping(loader, node, deep=False):
                loader.flatten_mapping(node)
                result = {}
                for key_node, value_node in node.value:
                    key = loader.construct_object(key_node, deep=deep)
                    if key in result:
                        raise ValueError('Duplicate YAML key')
                    result[key] = loader.construct_object(value_node, deep=deep)
                return result
            UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
            metadata = yaml.load(front.group(1), Loader=UniqueLoader)
            if not isinstance(metadata, dict):
                raise ValueError('Not a mapping')
        except (yaml.YAMLError, ValueError, TypeError):
            add('error', 'invalid-yaml')
            metadata = {}
        body = normalized[front.end():]
    name = metadata.get('name', '')
    description = metadata.get('description', '')
    if not isinstance(name, str) or len(name) > 64 or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        add('error', 'invalid-name')
    elif name != package.name:
        add('error', 'directory-name-mismatch')
    if isinstance(name, str) and any(word in name for word in ('anthropic', 'claude')):
        add('error', 'reserved-name')
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        add('error', 'invalid-description')
    elif re.search(r'<[^>]*>', description):
        add('error', 'xml-description')
    if isinstance(description, str) and re.search(r'\b(?:I can|You can|Я могу|Ты можешь|Вы можете)\b', description, re.I):
        add('warning', 'description-person-review')
    if len(body.splitlines()) >= 500:
        add('warning', 'entrypoint-length-recommendation')
    author_owned = isinstance(name, str) and name.startswith('che-')
    if author_owned:
        for link in PUBLIC_LINKS:
            if link not in source:
                add('error', 'missing-author-link')
        if 'Любовь Черемисина' not in source:
            add('error', 'missing-methodologist')
    direct_resources = set(local_targets(body, package))
    has_scripts = False
    resource_bytes = 0
    for file in sorted(package.rglob('*')):
        relative = file.relative_to(package)
        if file.is_symlink():
            add('error', 'symlink-resource', relative)
            continue
        if not file.is_file():
            continue
        try:
            file_raw = file.read_bytes()
        except OSError:
            add('error', 'unreadable-resource', relative)
            continue
        if file != entry:
            resource_bytes += len(file_raw)
        if relative.parts[0] == 'scripts' and file.suffix in ('.py', '.sh', '.js', '.ts'):
            has_scripts = True
        try:
            text = file_raw.decode('utf-8')
        except UnicodeError:
            add('warning', 'binary-resource-review', relative)
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for code, pattern in PRIVATE_PATTERNS.items():
                if pattern.search(line):
                    add('warning' if code == 'email-address' else 'error', code, relative, line_no)
        if file.suffix != '.md':
            continue
        if relative.parts[0] == 'references' and len(text.splitlines()) > 100:
            if not re.search(r'(?im)^#{1,3}\s+(?:contents|table of contents|оглавление|содержание)\s*$', text):
                add('warning', 'reference-toc-recommendation', relative)
        # One-hop navigation is satisfied if the target is also linked directly
        # by SKILL.md; references may cross-link those resources freely.
        for resolved in local_targets(text, file.parent):
            try:
                resolved.relative_to(package)
            except ValueError:
                add('error', 'resource-path-escape', relative)
                continue
            if not resolved.exists():
                add('error', 'missing-local-resource', relative)
            elif file != entry and '/references/' in resolved.as_posix() and resolved not in direct_resources:
                add('warning', 'nested-reference-navigation', relative)
    if has_scripts and not re.search(r'(?i)dependenc|зависимост|требуется|python|node|bash', source):
        add('warning', 'script-dependencies-review')
    if re.search(r'\bMCP\b', body) and not re.search(r'(?i)недоступ|соединени|подключени|available|unavailable|connection', body):
        add('warning', 'mcp-missing-connection-review')
    return {
        'id': package.name,
        'metadata_name': name,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'metrics': {'entrypoint_utf8_bytes': len(raw), 'entrypoint_characters': len(source),
                    'body_lines': len(body.splitlines()), 'metadata_characters': len(front.group(1)) if front else 0,
                    'resource_bytes': resource_bytes},
        'findings': findings,
        'status': 'error' if any(f['severity'] == 'error' for f in findings) else 'review' if findings else 'static-pass',
        'not_verified': ['semantic-deduplication', 'complete-privacy', 'behavior', 'platform-runtime', 'upstream-currency', 'paid-token-savings'],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--json', type=Path, help='Write JSON report; findings omit matched content.')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error('root must be an existing directory')
    packages = [root] if (root / 'SKILL.md').exists() else sorted({p.parent for p in root.rglob('SKILL.md')})
    if not packages:
        parser.error('no SKILL.md found')
    if args.json:
        output = args.json.resolve()
        for package in packages:
            try:
                output.relative_to(package.resolve())
            except ValueError:
                continue
            parser.error('JSON output must be outside every audited package')
    results = [audit(p) for p in packages]
    report = {'schema_version': 1, 'scope': 'read-only-static', 'skills': results,
              'summary': {'skills': len(results), 'errors': sum(f['severity'] == 'error' for r in results for f in r['findings']),
                          'warnings': sum(f['severity'] == 'warning' for r in results for f in r['findings'])}}
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.json:
        args.json.write_text(encoded, encoding='utf-8')
        print(json.dumps(report['summary'], ensure_ascii=False))
    else:
        print(encoded, end='')
    return 1 if report['summary']['errors'] else 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except OSError:
        print('Cannot read input or write report; check paths and permissions.', file=sys.stderr)
        sys.exit(2)
