#!/usr/bin/env python3
"""
SEO/GEO Auditor — Professional Website Audit Script (v2.0)
Performs deep technical SEO and GEO analysis with scoring system.
Sources: Google Search Essentials, Yandex Webmaster, Semrush, Ahrefs, Moz, Rank Math, Yoast SEO.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import json
import os
import sys
from collections import Counter
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
}

AI_BOTS = ['GPTBot', 'PerplexityBot', 'ClaudeBot', 'OAI-SearchBot', 'Google-Extended', 'Applebot-Extended']
SEARCH_BOTS = ['Googlebot', 'YandexBot', 'Bingbot']

# --- Scoring weights ---
SCORE_CRITICAL = 15
SCORE_HIGH = 10
SCORE_MEDIUM = 5
SCORE_LOW = 2

# ============================================================
# DATA FETCHING
# ============================================================

def fetch_url(url, timeout=15):
    """Fetch URL content with error handling."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return {'status': resp.status_code, 'text': resp.text, 'headers': dict(resp.headers),
                'url_final': resp.url, 'redirects': [r.url for r in resp.history], 'error': None}
    except requests.exceptions.RequestException as e:
        return {'status': None, 'text': '', 'headers': {}, 'url_final': url, 'redirects': [], 'error': str(e)}


def get_base_url(url):
    """Extract base URL (scheme + host)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

# ============================================================
# TECHNICAL SEO CHECKS
# ============================================================

def check_https(url):
    """Check if URL uses HTTPS."""
    return url.startswith('https://')


def check_robots_txt(base_url):
    """Analyze robots.txt for search and AI bot access."""
    result = fetch_url(base_url + '/robots.txt', timeout=10)
    if result['error'] or result['status'] != 200:
        return {'found': False, 'content': '', 'ai_bots_blocked': [], 'search_bots_blocked': [],
                'sitemap_urls': [], 'error': result.get('error', f"Status {result['status']}")}

    content = result['text']
    lines = content.lower().split('\n')

    ai_blocked = []
    search_blocked = []
    sitemaps = []
    current_agent = '*'

    for line in content.split('\n'):
        line_stripped = line.strip()
        if line_stripped.lower().startswith('user-agent:'):
            current_agent = line_stripped.split(':', 1)[1].strip()
        elif line_stripped.lower().startswith('disallow: /') and line_stripped.lower().strip() == 'disallow: /':
            for bot in AI_BOTS:
                if current_agent == '*' or current_agent.lower() == bot.lower():
                    ai_blocked.append(bot)
            for bot in SEARCH_BOTS:
                if current_agent == '*' or current_agent.lower() == bot.lower():
                    search_blocked.append(bot)
        elif line_stripped.lower().startswith('sitemap:'):
            sitemaps.append(line_stripped.split(':', 1)[1].strip())

    # More precise check per bot
    ai_blocked_precise = []
    for bot in AI_BOTS:
        bot_lower = bot.lower()
        in_bot_section = False
        for line in content.split('\n'):
            ls = line.strip().lower()
            if ls.startswith('user-agent:'):
                agent = ls.split(':', 1)[1].strip()
                in_bot_section = (agent == bot_lower or agent == '*')
            elif in_bot_section and ls == 'disallow: /':
                ai_blocked_precise.append(bot)
                break

    return {'found': True, 'content': content[:2000], 'ai_bots_blocked': list(set(ai_blocked_precise)),
            'search_bots_blocked': list(set(search_blocked)), 'sitemap_urls': sitemaps, 'error': None}


def check_sitemap(base_url):
    """Check sitemap.xml accessibility."""
    result = fetch_url(base_url + '/sitemap.xml', timeout=10)
    if result['error'] or result['status'] != 200:
        return {'found': False, 'error': result.get('error', f"Status {result['status']}")}
    return {'found': True, 'size': len(result['text']), 'error': None}


def check_llms_txt(base_url):
    """Check for llms.txt file (AI-specific instructions)."""
    result = fetch_url(base_url + '/llms.txt', timeout=10)
    if result['error'] or result['status'] != 200:
        return {'found': False}
    return {'found': True, 'content_preview': result['text'][:500]}


def analyze_redirects(url):
    """Check for redirect chains."""
    result = fetch_url(url)
    chain = result.get('redirects', [])
    return {'chain_length': len(chain), 'chain': chain, 'final_url': result.get('url_final', url)}

# ============================================================
# ON-PAGE SEO CHECKS
# ============================================================

def analyze_meta_tags(soup):
    """Extract and analyze all important meta tags."""
    results = {}

    # Title
    title_tag = soup.find('title')
    title = title_tag.string.strip() if title_tag and title_tag.string else None
    results['title'] = title
    results['title_length'] = len(title) if title else 0

    # Meta Description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    desc = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else None
    results['meta_description'] = desc
    results['meta_description_length'] = len(desc) if desc else 0

    # Viewport
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    results['viewport'] = viewport['content'] if viewport and viewport.get('content') else None

    # Canonical
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    results['canonical'] = canonical['href'] if canonical and canonical.get('href') else None

    # Hreflang
    hreflangs = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
    results['hreflang'] = [{'lang': h.get('hreflang'), 'href': h.get('href')} for h in hreflangs]

    # Open Graph
    og_tags = {}
    for meta in soup.find_all('meta', attrs={'property': re.compile(r'^og:')}):
        og_tags[meta.get('property')] = meta.get('content', '')
    results['open_graph'] = og_tags

    # Twitter Cards
    twitter_tags = {}
    for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
        twitter_tags[meta.get('name')] = meta.get('content', '')
    results['twitter_cards'] = twitter_tags

    # HTML lang
    html_tag = soup.find('html')
    results['html_lang'] = html_tag.get('lang') if html_tag else None

    # Favicon
    favicon = soup.find('link', attrs={'rel': re.compile(r'icon', re.I)})
    results['favicon'] = favicon['href'] if favicon and favicon.get('href') else None

    # Meta Robots
    meta_robots = soup.find('meta', attrs={'name': 'robots'})
    results['meta_robots'] = meta_robots['content'] if meta_robots and meta_robots.get('content') else None

    return results


def analyze_headings(soup):
    """Analyze heading structure (H1-H6)."""
    headings = {}
    for i in range(1, 7):
        tags = soup.find_all(f'h{i}')
        if tags:
            headings[f'h{i}'] = [tag.get_text(strip=True) for tag in tags]
    return headings


def analyze_images(soup):
    """Analyze image optimization."""
    images = soup.find_all('img')
    total = len(images)
    with_alt = sum(1 for img in images if img.get('alt') and img['alt'].strip())
    with_dimensions = sum(1 for img in images if img.get('width') and img.get('height'))
    with_lazy = sum(1 for img in images if img.get('loading') == 'lazy')
    return {
        'total': total,
        'with_alt': with_alt,
        'without_alt': total - with_alt,
        'with_dimensions': with_dimensions,
        'with_lazy_loading': with_lazy,
        'alt_ratio': round(with_alt / total * 100) if total > 0 else 100
    }


def analyze_links(soup, base_url):
    """Analyze internal and external links."""
    all_links = soup.find_all('a', href=True)
    internal = []
    external = []
    broken_candidates = []

    parsed_base = urlparse(base_url)
    for a in all_links:
        href = a['href'].strip()
        if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:') or href.startswith('javascript:'):
            continue
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.netloc == parsed_base.netloc:
            internal.append(full_url)
        else:
            external.append(full_url)

    return {
        'total': len(all_links),
        'internal_count': len(internal),
        'external_count': len(external),
        'internal_unique': len(set(internal)),
        'external_unique': len(set(external))
    }


def analyze_content(soup):
    """Analyze content quality signals."""
    # Remove scripts and styles
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)
    words = text.split()
    word_count = len(words)

    # Check for FAQ sections
    faq_indicators = ['faq', 'вопрос', 'ответ', 'часто задаваемые', 'frequently asked']
    has_faq = any(ind in text.lower() for ind in faq_indicators)

    # Check for TL;DR / Summary
    summary_indicators = ['tl;dr', 'tldr', 'key takeaway', 'краткое содержание', 'резюме', 'ключевые выводы', 'в двух словах']
    has_summary = any(ind in text.lower() for ind in summary_indicators)

    # Check for dates (freshness signal)
    date_patterns = [
        r'\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
        r'обновлено|updated|last updated|дата обновления'
    ]
    has_date = any(re.search(p, text, re.IGNORECASE) for p in date_patterns)

    return {
        'word_count': word_count,
        'has_faq_section': has_faq,
        'has_summary_tldr': has_summary,
        'has_freshness_date': has_date
    }


def analyze_schema_org(soup):
    """Extract and categorize Schema.org structured data."""
    schemas = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            if script.string:
                data = json.loads(script.string)
                schemas.append(data)
        except json.JSONDecodeError:
            continue

    # Categorize found types
    found_types = set()
    def extract_types(obj):
        if isinstance(obj, dict):
            if '@type' in obj:
                t = obj['@type']
                if isinstance(t, list):
                    found_types.update(t)
                else:
                    found_types.add(t)
            for v in obj.values():
                extract_types(v)
        elif isinstance(obj, list):
            for item in obj:
                extract_types(item)

    for s in schemas:
        extract_types(s)

    return {
        'found': len(schemas) > 0,
        'count': len(schemas),
        'types': list(found_types),
        'raw': schemas[:3]  # Limit to first 3 for report size
    }


def analyze_eeat(soup, meta_tags):
    """Analyze E-E-A-T signals."""
    text = soup.get_text(separator=' ', strip=True).lower()
    signals = {
        'author_page': False,
        'about_page': False,
        'contact_page': False,
        'privacy_policy': False,
        'external_citations': 0,
        'social_links': False
    }

    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        link_text = a.get_text(strip=True).lower()
        # About page
        if any(kw in href or kw in link_text for kw in ['about', 'о нас', 'о компании', 'об авторе']):
            signals['about_page'] = True
        # Contact page
        if any(kw in href or kw in link_text for kw in ['contact', 'контакт', 'связаться', 'обратная связь']):
            signals['contact_page'] = True
        # Privacy policy
        if any(kw in href or kw in link_text for kw in ['privacy', 'конфиденциальност', 'политика']):
            signals['privacy_policy'] = True
        # Social links
        if any(soc in href for soc in ['linkedin.com', 'facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 't.me', 'vk.com']):
            signals['social_links'] = True

    # Author patterns
    author_patterns = [r'автор[:\s]', r'author[:\s]', r'written by', r'by\s+[A-Z]']
    for p in author_patterns:
        if re.search(p, text, re.IGNORECASE):
            signals['author_page'] = True
            break

    # External citations (links to authoritative domains)
    authority_domains = ['wikipedia.org', 'doi.org', '.gov', '.edu', 'scholar.google', 'researchgate.net',
                         'statista.com', 'mckinsey.com', 'hbr.org', 'forbes.com']
    for a in soup.find_all('a', href=True):
        if any(d in a['href'] for d in authority_domains):
            signals['external_citations'] += 1

    return signals

# ============================================================
# SCORING ENGINE
# ============================================================

def calculate_score(findings):
    """Calculate overall health score (0-100) based on findings."""
    score = 100
    issues = []

    # --- CRITICAL (15 pts each) ---
    if not findings.get('https'):
        score -= SCORE_CRITICAL
        issues.append(('КРИТИЧНО', 'Сайт не использует HTTPS'))

    context = findings.get('audit_context', {})
    # robots.txt is optional; a failed fetch is not proof of a crawl block.

    if context.get('public_indexing_intended') is True and findings.get('robots_txt', {}).get('search_bots_blocked'):
        score -= SCORE_CRITICAL
        bots = ', '.join(findings['robots_txt']['search_bots_blocked'])
        issues.append(('КРИТИЧНО', f'Поисковые боты заблокированы в robots.txt: {bots}'))

    meta = findings.get('meta_tags', {})
    if not meta.get('title'):
        score -= SCORE_CRITICAL
        issues.append(('КРИТИЧНО', 'Отсутствует тег <title>'))

    headings = findings.get('headings', {})
    h1_list = headings.get('h1', [])
    if len(h1_list) == 0:
        score -= SCORE_CRITICAL
        issues.append(('КРИТИЧНО', 'Отсутствует заголовок H1'))
    elif len(h1_list) > 1:
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', f'Найдено {len(h1_list)} заголовков H1 (должен быть один)'))

    # --- HIGH (10 pts each) ---
    if not meta.get('meta_description'):
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', 'Отсутствует мета-описание (meta description)'))
    elif meta.get('meta_description_length', 0) > 160:
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', f'Мета-описание слишком длинное ({meta["meta_description_length"]} симв., рекомендуется до 160)'))

    if meta.get('title_length', 0) > 60:
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', f'Title слишком длинный ({meta["title_length"]} симв., рекомендуется до 60)'))

    if not meta.get('viewport'):
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', 'Отсутствует тег viewport (проблемы с мобильной адаптивностью)'))

    if not meta.get('canonical'):
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', 'Отсутствует тег rel="canonical"'))

    schema = findings.get('schema', {})
    if not schema.get('found'):
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', 'Структурированные данные Schema.org (JSON-LD) не найдены'))

    if not findings.get('sitemap', {}).get('found'):
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', 'Файл sitemap.xml не найден или недоступен'))

    # Missing llms.txt and intentional AI-bot policy are not ranking defects.
    blocked = set(findings.get('robots_txt', {}).get('ai_bots_blocked', []))
    intended = set(context.get('required_ai_bots', []))
    if blocked & intended:
        score -= SCORE_HIGH
        issues.append(('ВЫСОКИЙ', 'Заблокированы боты выбранного владельцем канала: ' + ', '.join(sorted(blocked & intended))))

    # --- MEDIUM (5 pts each) ---
    if not meta.get('open_graph'):
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', 'Отсутствуют Open Graph мета-теги (og:title, og:description, og:image)'))

    if not meta.get('twitter_cards'):
        score -= SCORE_LOW
        issues.append(('НИЗКИЙ', 'Отсутствуют Twitter Card мета-теги'))

    if not meta.get('html_lang'):
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', 'Не указан атрибут lang у тега <html>'))

    if not meta.get('favicon'):
        score -= SCORE_LOW
        issues.append(('НИЗКИЙ', 'Не найден favicon'))

    images = findings.get('images', {})
    if images.get('total', 0) > 0 and images.get('alt_ratio', 100) < 80:
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', f'Только {images["alt_ratio"]}% изображений имеют атрибут alt ({images["without_alt"]} без alt)'))

    content = findings.get('content', {})
    if content.get('word_count', 0) < 300:
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', f'Мало текстового контента ({content["word_count"]} слов). Рекомендуется минимум 300 для лендингов, 1000+ для статей'))

    # FAQ absence is not a defect without a page-specific user need.

    if not content.get('has_summary_tldr') and content.get('word_count', 0) > 1000:
        score -= SCORE_LOW
        issues.append(('НИЗКИЙ', 'Нет краткого резюме (TL;DR / Key Takeaways) для длинного контента'))

    if not content.get('has_freshness_date'):
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', 'Не найдены сигналы свежести контента (дата публикации/обновления)'))

    eeat = findings.get('eeat', {})
    if not eeat.get('about_page'):
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', 'Не найдена ссылка на страницу "О нас" / "About"'))

    if not eeat.get('author_page'):
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', 'Не найдена информация об авторе контента'))

    if not eeat.get('privacy_policy'):
        score -= SCORE_LOW
        issues.append(('НИЗКИЙ', 'Не найдена ссылка на Политику конфиденциальности'))

    links = findings.get('links', {})
    if links.get('internal_unique', 0) < 3:
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', f'Мало внутренних ссылок ({links.get("internal_unique", 0)}). Рекомендуется улучшить перелинковку'))

    # Redirect chain
    redirects = findings.get('redirects', {})
    if redirects.get('chain_length', 0) > 1:
        score -= SCORE_MEDIUM
        issues.append(('СРЕДНИЙ', f'Обнаружена цепочка редиректов ({redirects["chain_length"]} шагов)'))

    score = max(0, score)
    return score, issues

# ============================================================
# REPORT GENERATION
# ============================================================

def get_score_emoji(score):
    if score >= 80: return '🟢'
    if score >= 60: return '🟡'
    if score >= 40: return '🟠'
    return '🔴'

def get_score_label(score):
    if score >= 80: return 'Отлично'
    if score >= 60: return 'Хорошо'
    if score >= 40: return 'Требует внимания'
    return 'Критическое состояние'


def generate_report(url, site_type, findings, score, issues):
    """Generate a professional audit report."""
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    meta = findings.get('meta_tags', {})
    schema = findings.get('schema', {})
    images = findings.get('images', {})
    links = findings.get('links', {})
    content = findings.get('content', {})
    eeat = findings.get('eeat', {})
    robots = findings.get('robots_txt', {})
    llms = findings.get('llms_txt', {})

    emoji = get_score_emoji(score)
    label = get_score_label(score)

    r = []
    r.append(f"# SEO/GEO Аудит: {url}")
    r.append(f"**Дата аудита:** {now}")
    r.append(f"**Тип сайта:** {site_type}")
    r.append("")
    r.append("---")
    r.append("")

    # Executive Summary
    r.append("## Executive Summary")
    r.append("")
    r.append(f"### Предварительный автоматический балл: {emoji} **{score}/100** — {label}")
    r.append("")

    # Issue counts
    critical_count = sum(1 for p, _ in issues if p == 'КРИТИЧНО')
    high_count = sum(1 for p, _ in issues if p == 'ВЫСОКИЙ')
    medium_count = sum(1 for p, _ in issues if p == 'СРЕДНИЙ')
    low_count = sum(1 for p, _ in issues if p == 'НИЗКИЙ')

    r.append("| Приоритет | Количество |")
    r.append("|:---|:---:|")
    r.append(f"| 🔴 Критично | {critical_count} |")
    r.append(f"| 🟠 Высокий | {high_count} |")
    r.append(f"| 🟡 Средний | {medium_count} |")
    r.append(f"| ⚪ Низкий | {low_count} |")
    r.append("")

    # Quick stats
    r.append("### Ключевые метрики")
    r.append("")
    r.append("| Метрика | Значение |")
    r.append("|:---|:---|")
    r.append(f"| HTTPS | {'✅ Да' if findings.get('https') else '❌ Нет'} |")
    r.append(f"| robots.txt | {'✅ Найден' if robots.get('found') else '❌ Не найден'} |")
    r.append(f"| sitemap.xml | {'✅ Найден' if findings.get('sitemap', {}).get('found') else '❌ Не найден'} |")
    r.append(f"| llms.txt | {'✅ Найден' if llms.get('found') else '❌ Не найден'} |")
    r.append(f"| Schema.org | {'✅ ' + ', '.join(schema.get('types', [])) if schema.get('found') else '❌ Не найдена'} |")
    r.append(f"| Title | {meta.get('title', '❌ Отсутствует')[:60] if meta.get('title') else '❌ Отсутствует'} |")
    r.append(f"| H1 | {findings.get('headings', {}).get('h1', ['❌ Отсутствует'])[0][:60] if findings.get('headings', {}).get('h1') else '❌ Отсутствует'} |")
    r.append(f"| Слов на странице | {content.get('word_count', 'N/A')} |")
    r.append(f"| Изображений (с alt / всего) | {images.get('with_alt', 0)} / {images.get('total', 0)} |")
    r.append(f"| Внутренних ссылок | {links.get('internal_unique', 0)} |")
    r.append(f"| Внешних ссылок | {links.get('external_unique', 0)} |")
    r.append("")

    r.append("---")
    r.append("")

    # Detailed Findings
    r.append("## 1. Техническое SEO")
    r.append("")
    r.append("### 1.1. Индексация и доступность")
    r.append("")
    r.append(f"**HTTPS:** {'✅ Сайт работает по защищенному протоколу.' if findings.get('https') else '❌ Сайт не использует HTTPS. Это критическая проблема безопасности и ранжирования.'}")
    r.append("")
    r.append(f"**robots.txt:** {'✅ Файл найден.' if robots.get('found') else '❌ Файл не найден или недоступен.'}")
    if robots.get('found'):
        if robots.get('ai_bots_blocked'):
            r.append(f"  - ⚠️ **AI-боты заблокированы:** {', '.join(robots['ai_bots_blocked'])}. Сверить с намерением владельца и функцией каждого бота; ограничения обучения и поискового доступа различаются.")
        else:
            r.append("  - ✅ AI-боты (GPTBot, PerplexityBot, ClaudeBot) не заблокированы.")
        if robots.get('search_bots_blocked'):
            r.append(f"  - 🔴 **Поисковые боты заблокированы:** {', '.join(robots['search_bots_blocked'])}. Критическая ошибка!")
        else:
            r.append("  - ✅ Поисковые боты (Googlebot, YandexBot) не заблокированы.")
    r.append("")
    r.append(f"**sitemap.xml:** {'✅ Найден.' if findings.get('sitemap', {}).get('found') else '❌ Не найден. Рекомендуется создать и зарегистрировать в Google Search Console и Яндекс.Вебмастере.'}")
    r.append("")
    canonical_val = meta.get('canonical', '')
    if canonical_val:
        r.append(f"**Canonical:** ✅ `{canonical_val}`")
    else:
        r.append('**Canonical:** ❌ Тег rel="canonical" отсутствует. Это может привести к проблемам с дублированием контента.')
    r.append("")
    meta_robots_val = meta.get('meta_robots')
    if meta_robots_val:
        r.append(f"**Meta Robots:** `{meta_robots_val}`")
    else:
        r.append("**Meta Robots:** ✅ Не задан; фактическую индексацию проверить отдельно")
    r.append("")

    # Redirects
    redirects = findings.get('redirects', {})
    if redirects.get('chain_length', 0) > 0:
        r.append(f"**Редиректы:** ⚠️ Обнаружена цепочка из {redirects['chain_length']} редиректов. Рекомендуется сократить до одного шага.")
    else:
        r.append("**Редиректы:** ✅ Цепочки редиректов не обнаружены.")
    r.append("")

    r.append("### 1.2. Мобильная адаптивность")
    r.append("")
    r.append(f"**Viewport:** {'✅ Настроен: `' + meta.get('viewport', '') + '`' if meta.get('viewport') else '❌ Тег viewport отсутствует. Сайт может некорректно отображаться на мобильных устройствах.'}")
    r.append("")

    r.append("### 1.3. Структурированные данные (Schema.org)")
    r.append("")
    if schema.get('found'):
        r.append(f"✅ Найдено {schema['count']} блок(ов) JSON-LD. Типы: **{', '.join(schema['types'])}**.")
        r.append("Проверить соответствие типов видимому содержимому и текущей поддержке; не добавлять все типы на каждую страницу.")
    else:
        r.append("Разметка JSON-LD не обнаружена. Проверить применимость типа; отсутствие не доказывает потерю AI-видимости.")
    r.append("")

    r.append("---")
    r.append("")

    # On-Page SEO
    r.append("## 2. Внутренняя оптимизация (On-Page SEO)")
    r.append("")
    r.append("### 2.1. Мета-теги")
    r.append("")
    r.append("| Элемент | Статус | Значение |")
    r.append("|:---|:---:|:---|")
    title_status = '✅' if meta.get('title') and 30 <= meta.get('title_length', 0) <= 60 else ('⚠️' if meta.get('title') else '❌')
    r.append(f"| Title ({meta.get('title_length', 0)} симв.) | {title_status} | {(meta.get('title', 'N/A') or 'N/A')[:60]} |")
    desc_status = '✅' if meta.get('meta_description') and 120 <= meta.get('meta_description_length', 0) <= 160 else ('⚠️' if meta.get('meta_description') else '❌')
    r.append(f"| Meta Description ({meta.get('meta_description_length', 0)} симв.) | {desc_status} | {(meta.get('meta_description', 'N/A') or 'N/A')[:80]}... |")
    r.append(f"| Open Graph | {'✅' if meta.get('open_graph') else '❌'} | {', '.join(meta.get('open_graph', {}).keys()) or 'Не найдены'} |")
    r.append(f"| Twitter Cards | {'✅' if meta.get('twitter_cards') else '❌'} | {', '.join(meta.get('twitter_cards', {}).keys()) or 'Не найдены'} |")
    r.append(f"| HTML lang | {'✅' if meta.get('html_lang') else '❌'} | {meta.get('html_lang', 'Не указан')} |")
    r.append(f"| Favicon | {'✅' if meta.get('favicon') else '❌'} | {'Найден' if meta.get('favicon') else 'Не найден'} |")
    r.append("")

    r.append("### 2.2. Заголовки")
    r.append("")
    headings = findings.get('headings', {})
    if headings:
        for tag, texts in headings.items():
            r.append(f"**{tag.upper()}** ({len(texts)}):")
            for t in texts[:5]:
                r.append(f"  - {t[:80]}")
    else:
        r.append("❌ Заголовки не найдены.")
    r.append("")

    r.append("### 2.3. Изображения")
    r.append("")
    r.append(f"Всего изображений: **{images.get('total', 0)}**. С alt-текстом: **{images.get('with_alt', 0)}** ({images.get('alt_ratio', 0)}%). С размерами (width/height): **{images.get('with_dimensions', 0)}**. С lazy loading: **{images.get('with_lazy_loading', 0)}**.")
    r.append("")

    r.append("### 2.4. Ссылки")
    r.append("")
    r.append(f"Внутренних ссылок: **{links.get('internal_unique', 0)}**. Внешних ссылок: **{links.get('external_unique', 0)}**.")
    r.append("")

    r.append("---")
    r.append("")

    # GEO Section
    r.append("## 3. GEO — Готовность к AI-поиску")
    r.append("")
    r.append(f"**llms.txt:** {'✅ Файл найден. AI-поисковики могут получить структурированные инструкции о вашем сайте.' if llms.get('found') else '❌ Файл llms.txt не найден. Файл необязателен; подтверждённого универсального эффекта для поиска нет.'}")
    r.append("")
    r.append(f"**Блок FAQ:** {'✅ Обнаружены элементы FAQ на странице.' if content.get('has_faq_section') else '❌ Блок FAQ не найден. Оценить необходимость по вопросам аудитории; отсутствие не является автоматическим дефектом.'}")
    r.append("")
    r.append(f"**Краткое резюме (TL;DR):** {'✅ Найдены элементы резюме/ключевых выводов.' if content.get('has_summary_tldr') else '❌ Не найдено. Для длинного контента рекомендуется добавить блок «Ключевые выводы» в начале статьи.'}")
    r.append("")
    r.append(f"**Сигналы свежести:** {'✅ Обнаружены даты публикации/обновления.' if content.get('has_freshness_date') else '❌ Не найдены даты. AI отдает приоритет свежему контенту. Добавьте видимую дату «Обновлено: ...».'}")
    r.append("")

    r.append("---")
    r.append("")

    # E-E-A-T Section
    r.append("## 4. E-E-A-T (Опыт, Экспертность, Авторитетность, Достоверность)")
    r.append("")
    r.append("| Сигнал | Статус |")
    r.append("|:---|:---:|")
    r.append(f"| Информация об авторе | {'✅' if eeat.get('author_page') else '❌'} |")
    r.append(f"| Страница «О нас» / «О компании» | {'✅' if eeat.get('about_page') else '❌'} |")
    r.append(f"| Страница контактов | {'✅' if eeat.get('contact_page') else '❌'} |")
    r.append(f"| Политика конфиденциальности | {'✅' if eeat.get('privacy_policy') else '❌'} |")
    r.append(f"| Ссылки на соцсети | {'✅' if eeat.get('social_links') else '❌'} |")
    r.append(f"| Ссылки на авторитетные источники | {'✅ ' + str(eeat.get('external_citations', 0)) + ' шт.' if eeat.get('external_citations', 0) > 0 else '❌ 0'} |")
    r.append("")

    r.append("---")
    r.append("")

    # Priority Matrix
    r.append("## 5. Матрица приоритетов: Что исправить в первую очередь")
    r.append("")
    if issues:
        r.append("| # | Приоритет | Проблема |")
        r.append("|:---:|:---|:---|")
        for i, (priority, desc) in enumerate(issues, 1):
            icon = {'КРИТИЧНО': '🔴', 'ВЫСОКИЙ': '🟠', 'СРЕДНИЙ': '🟡', 'НИЗКИЙ': '⚪'}.get(priority, '⚪')
            r.append(f"| {i} | {icon} {priority} | {desc} |")
    else:
        r.append("✅ Критических проблем не обнаружено. Сайт в отличном состоянии!")
    r.append("")

    r.append("---")
    r.append("")

    # References
    r.append("## Источники и методология")
    r.append("")
    r.append("Источники методологии; актуальность проверить на дату аудита:")
    r.append("")
    r.append("1. [Google Search Essentials](https://developers.google.com/search/docs/essentials) — Технические требования и лучшие практики Google.")
    r.append("2. [Google: Succeeding in AI Search](https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search) — Официальные рекомендации Google по AI-поиску (май 2025).")
    r.append("3. [Semrush: How to Perform a Complete SEO Audit in 17 Steps](https://www.semrush.com/blog/seo-audit/) — Методология аудита Semrush (январь 2026).")
    r.append("4. [Search Engine Land: Mastering GEO in 2026](https://searchengineland.com/mastering-generative-engine-optimization-in-2026-full-guide-469142) — Фреймворк GEO-оптимизации.")
    r.append("5. [Rank Math: How to Get Mentioned in AI Search](https://rankmath.com/blog/get-mentioned-in-ai-search/) — Стратегии попадания в AI-ответы.")
    r.append("6. [Yoast SEO: Rethinking SEO in the Age of AI](https://yoast.com/rethinking-seo-in-the-age-of-ai/) — Переосмысление SEO в эпоху AI.")
    r.append("7. [Яндекс.Вебмастер: Рекомендации](https://yandex.ru/support/webmaster/recommendations/intro.html) — Требования Яндекса к сайтам.")
    r.append("")

    return '\n'.join(r)


# ============================================================
# MAIN
# ============================================================

def main(url, site_type):
    """Run the full audit pipeline."""
    print(f"🔍 Запуск SEO/GEO аудита для: {url}")
    print(f"   Тип сайта: {site_type}")
    print()

    base_url = get_base_url(url)
    findings = {}

    # 1. HTTPS
    findings['https'] = check_https(url)
    print(f"  [1/9] HTTPS: {'✅' if findings['https'] else '❌'}")

    # 2. robots.txt
    findings['robots_txt'] = check_robots_txt(base_url)
    print(f"  [2/9] robots.txt: {'✅ Найден' if findings['robots_txt']['found'] else '❌ Не найден'}")

    # 3. sitemap.xml
    findings['sitemap'] = check_sitemap(base_url)
    print(f"  [3/9] sitemap.xml: {'✅ Найден' if findings['sitemap']['found'] else '❌ Не найден'}")

    # 4. llms.txt
    findings['llms_txt'] = check_llms_txt(base_url)
    print(f"  [4/9] llms.txt: {'✅ Найден' if findings['llms_txt']['found'] else '❌ Не найден'}")

    # 5. Redirects
    findings['redirects'] = analyze_redirects(url)
    print(f"  [5/9] Редиректы: {findings['redirects']['chain_length']} шагов")

    # 6. Fetch page
    page = fetch_url(url)
    if page['error']:
        print(f"  ❌ Ошибка загрузки страницы: {page['error']}")
        findings['meta_tags'] = {}
        findings['headings'] = {}
        findings['images'] = {'total': 0, 'with_alt': 0, 'without_alt': 0, 'with_dimensions': 0, 'with_lazy_loading': 0, 'alt_ratio': 0}
        findings['links'] = {'total': 0, 'internal_count': 0, 'external_count': 0, 'internal_unique': 0, 'external_unique': 0}
        findings['content'] = {'word_count': 0, 'has_faq_section': False, 'has_summary_tldr': False, 'has_freshness_date': False}
        findings['schema'] = {'found': False, 'count': 0, 'types': [], 'raw': []}
        findings['eeat'] = {}
    else:
        soup = BeautifulSoup(page['text'], 'html.parser')

        # 6. Meta tags
        findings['meta_tags'] = analyze_meta_tags(soup)
        print(f"  [6/9] Мета-теги: Title={'✅' if findings['meta_tags'].get('title') else '❌'}, Desc={'✅' if findings['meta_tags'].get('meta_description') else '❌'}")

        # 7. Headings, Images, Links
        findings['headings'] = analyze_headings(soup)
        findings['images'] = analyze_images(soup)
        findings['links'] = analyze_links(soup, base_url)
        print(f"  [7/9] Контент: H1={'✅' if findings['headings'].get('h1') else '❌'}, Img={findings['images']['total']}, Links={findings['links']['total']}")

        # 8. Content & Schema
        soup_content = BeautifulSoup(page['text'], 'html.parser')
        findings['content'] = analyze_content(soup_content)
        findings['schema'] = analyze_schema_org(soup)
        print(f"  [8/9] Schema: {'✅ ' + ', '.join(findings['schema']['types']) if findings['schema']['found'] else '❌ Не найдена'}")

        # 9. E-E-A-T
        findings['eeat'] = analyze_eeat(soup, findings['meta_tags'])
        print(f"  [9/9] E-E-A-T: About={'✅' if findings['eeat'].get('about_page') else '❌'}, Author={'✅' if findings['eeat'].get('author_page') else '❌'}")

    print()

    # Calculate score
    score, issues = calculate_score(findings)
    print(f"🏆 Общий балл: {get_score_emoji(score)} {score}/100 — {get_score_label(score)}")
    print(f"   Найдено проблем: {len(issues)}")
    print()

    # Generate report
    report = generate_report(url, site_type, findings, score, issues)
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', url)[:80]
    output_dir = os.environ.get("SEO_GEO_OUTPUT_DIR", os.getcwd())
    report_path = os.path.join(output_dir, f"audit_report_{safe_name}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 Отчет сохранен: {report_path}")

    return report_path


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SEO/GEO Auditor — Professional Website Audit')
    parser.add_argument('--url', required=True, help='URL сайта для аудита')
    parser.add_argument('--site_type', required=True, choices=['landing', 'e-commerce', 'portal', 'blog', 'corporate'],
                        help='Тип сайта: landing, e-commerce, portal, blog, corporate')
    args = parser.parse_args()

    main(args.url, args.site_type)
