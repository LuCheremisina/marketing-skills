#!/usr/bin/env python3
import json, csv, os, re

CONFIG_FILE = 'config.json'
WORDSTAT_FILE = 'wordstat_data.json'
WEBMASTER_FILE = 'webmaster_data.csv'
METRIKA_FILE = 'metrika_data.json'
OUTPUT_FILE = 'final_correlation.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Ошибка: {CONFIG_FILE} не найден."); exit(1)
    with open(CONFIG_FILE) as f: return json.load(f)

def norm(s):
    s = str(s).lower()
    s = re.sub(r'[^a-zа-я0-9\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def get_words(s): return set(norm(s).split())

def classify_position(pos):
    """Гранулярная шкала видимости. pos=0 означает 'не видим'."""
    if pos <= 0:      return 'Не видим'
    if pos <= 3:      return 'ТОП-3'
    if pos <= 10:     return 'ТОП-10'
    if pos <= 50:     return 'ТОП-50'
    return 'Слабая видимость'  # позиция 51+

def main():
    print("=== Анализ корреляции ===")

    for f in [WORDSTAT_FILE, WEBMASTER_FILE, METRIKA_FILE]:
        if not os.path.exists(f):
            print(f"Ошибка: {f} не найден. Выполните предыдущие этапы."); exit(1)

    with open(WORDSTAT_FILE) as f:
        ws_queries = json.load(f).get('top_100', [])

    with open(METRIKA_FILE) as f:
        pages = json.load(f).get('pages_organic', [])

    wm_queries = []
    try:
        with open(WEBMASTER_FILE, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                query = row.get('Запрос', row.get('Query', ''))
                shows = float(row.get('Показы', row.get('Shows', 0)) or 0)
                clicks = float(row.get('Клики', row.get('Clicks', 0)) or 0)
                pos = float(row.get('Ср. позиция показа', row.get('Avg. position', 0)) or 0)
                if query:
                    wm_queries.append({'query': query, 'shows': shows,
                                       'clicks': clicks, 'position': pos})
    except Exception as e:
        print(f"Ошибка чтения {WEBMASTER_FILE}: {e}"); exit(1)

    print(f"Загружено: Wordstat ({len(ws_queries)}), Вебмастер ({len(wm_queries)}), Метрика ({len(pages)} страниц)")

    correlation = []
    for ws in ws_queries:
        ws_words = get_words(ws['phrase'])
        related = [wm for wm in wm_queries if ws_words.issubset(get_words(wm['query']))]

        best_pos = min((q['position'] for q in related if q['position'] > 0), default=0)
        total_shows = sum(q['shows'] for q in related)
        total_clicks = sum(q['clicks'] for q in related)

        correlation.append({
            "phrase": ws['phrase'],
            "demand_count": ws['count'],
            "wm_related_count": len(related),
            "best_position": best_pos,
            "total_shows": total_shows,
            "total_clicks": total_clicks,
            "status": classify_position(best_pos)
        })

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(correlation, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Анализ завершён → {OUTPUT_FILE}")

    for s in ['ТОП-3', 'ТОП-10', 'ТОП-50', 'Слабая видимость', 'Не видим']:
        n = sum(1 for c in correlation if c['status'] == s)
        print(f"  {s}: {n}")

if __name__ == "__main__":
    main()
