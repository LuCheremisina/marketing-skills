#!/usr/bin/env python3
import json, csv, os, re, math

CONFIG_FILE = 'config.json'
WORDSTAT_FILE = 'wordstat_data.json'
WEBMASTER_FILE = 'webmaster_data.csv'
WEBMASTER_JSON_FILE = 'webmaster_data.json'
METRIKA_FILE = 'metrika_data.json'
OUTPUT_FILE = 'final_correlation.json'


def norm(s):
    s = str(s).lower().replace('ё', 'е')
    s = re.sub(r'[^a-zа-я0-9\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def get_words(s):
    return set(norm(s).split())


def classify_position(pos):
    """Zero is an explicitly observed absence; None means no matched row."""
    if pos is None: return 'Нет данных'
    if pos <= 0: return 'Не видим'
    if pos <= 3: return 'ТОП-3'
    if pos <= 10: return 'ТОП-10'
    if pos <= 50: return 'ТОП-50'
    return 'Слабая видимость'


def first_value(row, names):
    for name in names:
        if name in row:
            return row[name]
    raise ValueError('missing field: ' + '/'.join(names))


def numeric(value, label):
    if isinstance(value, bool) or value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f'{label} is missing')
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label} is not numeric') from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError(f'{label} must be a finite non-negative number')
    return result


def load_webmaster():
    csv_exists = os.path.exists(WEBMASTER_FILE)
    json_exists = os.path.exists(WEBMASTER_JSON_FILE)
    if csv_exists == json_exists:
        raise ValueError('provide exactly one of webmaster_data.csv or webmaster_data.json')
    if csv_exists:
        with open(WEBMASTER_FILE, encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
    else:
        with open(WEBMASTER_JSON_FILE, encoding='utf-8') as handle:
            payload = json.load(handle)
        rows = payload.get('queries') if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError('webmaster_data.json must contain a queries array')
    if not rows:
        raise ValueError('Webmaster data is empty; provide an export with metrics')
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f'Webmaster row {index + 1} must be an object')
        query = first_value(row, ('query', 'Query', 'Запрос'))
        if not isinstance(query, str) or not get_words(query):
            raise ValueError(f'Webmaster row {index + 1} has an empty query')
        result.append({
            'query': query,
            'shows': numeric(first_value(row, ('shows', 'impressions', 'Impressions', 'Shows', 'Показы')), 'shows'),
            'clicks': numeric(first_value(row, ('clicks', 'Clicks', 'Клики')), 'clicks'),
            'position': numeric(first_value(row, ('position', 'avg_position', 'Avg. position', 'Ср. позиция показа')), 'position'),
        })
    return result


def main():
    print('=== Анализ корреляции ===')
    for path in (WORDSTAT_FILE, METRIKA_FILE):
        if not os.path.exists(path):
            raise ValueError(f'{path} не найден. Выполните предыдущие этапы.')
    with open(WORDSTAT_FILE, encoding='utf-8') as handle:
        ws_queries = json.load(handle).get('top_100', [])
    with open(METRIKA_FILE, encoding='utf-8') as handle:
        pages = json.load(handle).get('pages_organic', [])
    wm_queries = load_webmaster()
    print(f'Загружено: Wordstat ({len(ws_queries)}), Вебмастер ({len(wm_queries)}), Метрика ({len(pages)} страниц)')
    correlation = []
    for ws in ws_queries:
        ws_words = get_words(ws['phrase'])
        if not ws_words:
            raise ValueError('Wordstat phrase must contain letters or digits')
        related = [wm for wm in wm_queries if ws_words.issubset(get_words(wm['query']))]
        best_pos = min((q['position'] for q in related if q['position'] > 0), default=0) if related else None
        correlation.append({
            'phrase': ws['phrase'], 'demand_count': ws['count'], 'wm_related_count': len(related),
            'best_position': best_pos,
            'total_shows': sum(q['shows'] for q in related) if related else None,
            'total_clicks': sum(q['clicks'] for q in related) if related else None,
            'status': classify_position(best_pos),
        })
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as handle:
        json.dump(correlation, handle, ensure_ascii=False, indent=2)
    print(f'\n✅ Анализ завершён → {OUTPUT_FILE}')
    for status in ('ТОП-3', 'ТОП-10', 'ТОП-50', 'Слабая видимость', 'Не видим', 'Нет данных'):
        print(f'  {status}: {sum(1 for item in correlation if item["status"] == status)}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f'Ошибка: {exc}') from exc
