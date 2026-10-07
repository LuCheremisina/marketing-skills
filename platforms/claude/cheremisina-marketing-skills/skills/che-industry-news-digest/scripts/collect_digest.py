#!/usr/bin/env python3
"""
Industry News Digest — сбор и дайджест новостей за N дней для любой ниши.

1. Загружает профиль бизнеса из config.json (ниша, бренды, источники, язык)
2. Собирает новости из RSS-лент за последние N дней
3. Кластеризует похожие новости из разных источников
4. Ранжирует по числу источников/упоминаний + буст за приоритетные бренды/товары
5. Верифицирует через LLM (фейк-чек, перевод) — либо fallback без LLM
6. Печатает готовый дайджест в stdout
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import feedparser

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.environ.get("DIGEST_CONFIG", os.path.join(os.getcwd(), "digest-config.json"))

# ─── Конфигурация ───────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        print(
            f"[ERROR] Конфиг не найден: {path}\n"
            f"Это первый запуск — проведи интервью с пользователем (см. SKILL.md) "
            f"и сохрани профиль в выбранный проектный digest-config.json, затем запусти скрипт снова.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ─── Утилиты ────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())

def title_similarity(t1: str, t2: str) -> float:
    words1 = set(normalize(t1).split())
    words2 = set(normalize(t2).split())
    if not words1 or not words2:
        return 0.0
    jaccard = len(words1 & words2) / len(words1 | words2)
    seq = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
    return max(jaccard, seq * 0.8)

def catalog_boost(text: str, priority_keywords: list[str], priority_brands: list[str]) -> float:
    """Буст новости за совпадение с приоритетными товарами/брендами клиента."""
    text_lower = text.lower()
    boost = 0.0
    if any(kw.lower() in text_lower for kw in priority_keywords):
        boost += 3.0
    if any(b.lower() in text_lower for b in priority_brands):
        boost += 1.5
    return boost

def matches_filter(text: str, filter_str: str) -> bool:
    return not filter_str or filter_str.lower() in text.lower()

# ─── Сбор новостей ──────────────────────────────────────────────────────────

def fetch_rss_entries(sources: list[dict], days_back: int, filter_str: str,
                       priority_keywords: list[str], priority_brands: list[str]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    entries, ok_sources, fail_sources = [], [], []

    for feed_info in sources:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries[:30]:
                pub_date = None
                for date_field in ("published_parsed", "updated_parsed"):
                    parsed = getattr(entry, date_field, None)
                    if parsed:
                        try:
                            pub_date = datetime(*parsed[:6], tzinfo=timezone.utc)
                        except Exception:
                            pass
                        break
                if pub_date and pub_date < cutoff:
                    continue

                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                summary = re.sub(r"<[^>]+>", "", getattr(entry, "summary", "").strip())[:600]
                if not title or not link:
                    continue
                if not matches_filter(title + " " + summary, filter_str):
                    continue

                entries.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": feed_info["name"],
                    "pub_date": pub_date.isoformat() if pub_date else None,
                    "boost": catalog_boost(title + " " + summary, priority_keywords, priority_brands),
                })
                count += 1
            if count > 0:
                ok_sources.append(f"{feed_info['name']} ({count})")
        except Exception:
            fail_sources.append(feed_info["name"])

    print(f"[INFO] Источники OK: {', '.join(ok_sources)}", file=sys.stderr)
    if fail_sources:
        print(f"[WARN] Недоступны: {', '.join(fail_sources)}", file=sys.stderr)
    print(f"[INFO] Всего собрано: {len(entries)} новостей за {days_back} дней", file=sys.stderr)
    return entries

# ─── Кластеризация ──────────────────────────────────────────────────────────

def cluster_entries(entries: list[dict], threshold: float) -> list[dict]:
    clusters = []
    for entry in entries:
        placed = False
        for cluster in clusters:
            if title_similarity(entry["title"], cluster["representative"]["title"]) >= threshold:
                cluster["all_entries"].append(entry)
                cluster["mentions"] += 1
                cluster["boost"] = max(cluster["boost"], entry["boost"])
                if entry["source"] not in cluster["sources"]:
                    cluster["sources"].append(entry["source"])
                placed = True
                break
        if not placed:
            clusters.append({
                "representative": entry, "mentions": 1, "sources": [entry["source"]],
                "all_entries": [entry], "boost": entry["boost"],
            })

    for c in clusters:
        base = len(c["sources"]) * 2 + c["mentions"]
        c["score"] = base * (1 + c["boost"] / 10)
    clusters.sort(key=lambda c: c["score"], reverse=True)

    print(f"[INFO] Кластеризация: {len(entries)} новостей → {len(clusters)} тем", file=sys.stderr)
    return clusters

# ─── LLM-обработка ─────────────────────────────────────────────────────────

def process_with_llm(clusters: list[dict], config: dict, max_news: int, days_back: int) -> str | None:
    try:
        from openai import OpenAI
    except ImportError:
        print("[WARN] openai не установлен. Вывод без LLM.", file=sys.stderr)
        return None
    if not clusters:
        return None

    client = OpenAI()
    top_clusters = clusters[:25]
    business = config.get("business_name", "клиент")
    niche = config.get("niche", "ниша")
    language = config.get("language", "русский")
    icon = config.get("icon", "📰")

    entries_text = ""
    for i, cluster in enumerate(top_clusters, 1):
        rep = cluster["representative"]
        flag = " [★ ПРИОРИТЕТ КАТАЛОГА]" if cluster["boost"] >= 3 else (" [· приоритетный бренд]" if cluster["boost"] > 0 else "")
        entries_text += (
            f"{i}. [СКОР: {cluster['score']:.1f} | УПОМИНАНИЙ: {cluster['mentions']} | "
            f"ИСТОЧНИКИ: {', '.join(cluster['sources'])}]{flag}\n"
            f"   Заголовок: {rep['title']}\n   Ссылка: {rep['link']}\n"
            f"   Описание: {rep['summary'][:400]}\n   Дата: {rep['pub_date'] or 'не определена'}\n\n"
        )

    today = datetime.now().strftime("%d.%m.%Y")
    total_sources = len({e["source"] for c in top_clusters for e in c["all_entries"]})

    prompt = f"""Ты — редактор новостного дайджеста для бизнеса «{business}» (ниша: {niche}).

ЗАДАЧА: отбери ровно {max_news} самых значимых тем из списка ниже и составь дайджест на языке: {language}.

ПРАВИЛА ОТБОРА (по приоритету):
1. Темы с флагом [★ ПРИОРИТЕТ КАТАЛОГА] или [· приоритетный бренд] — в приоритете, это касается товаров/тем клиента.
2. Чем выше скор и больше источников — тем выше значимость темы.
3. Только релевантная для ниши «{niche}» тематика.
4. Фейк-чек: только подтверждённые факты. Слухи без источника и рекламные материалы — отсеивать.
5. Разнообразие: не более 2 новостей от одного бренда/темы.

Каждая новость обязательно содержит прямую ссылку на первоисточник.

ФОРМАТ ОТВЕТА (только готовый дайджест, без пояснений):

{icon} ДАЙДЖЕСТ — {niche.upper()} | {today}
Период: последние {days_back} дней | Источников: {total_sources}

1. ЗАГОЛОВОК (краткий, информативный)
Краткое описание на 2-3 предложения, экспертный тон, без воды и маркетинговых клише.
🔥 N источников: Источник1, Источник2...
🔗 URL

[продолжить для всех {max_news} новостей]

━━━━━━━━━━━━━━━━━━━━━━
Только проверенные факты | Приоритет: каталог {business}

СПИСОК ТЕМ:
{entries_text}

Ответ — только готовый текст дайджеста."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini", messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=4000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Ошибка LLM: {e}", file=sys.stderr)
        return None

# ─── Fallback: дайджест без LLM ─────────────────────────────────────────────

def format_digest_raw(clusters: list[dict], config: dict, max_news: int, days_back: int) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    niche = config.get("niche", "ниша")
    icon = config.get("icon", "📰")
    business = config.get("business_name", "клиент")
    total_sources = len({e["source"] for c in clusters[:max_news] for e in c["all_entries"]})

    lines = [
        f"{icon} ДАЙДЖЕСТ — {niche.upper()} | {today}",
        f"Период: последние {days_back} дней | Источников: {total_sources} | ⚠️ Без LLM-обработки\n",
    ]
    for i, cluster in enumerate(clusters[:max_news], 1):
        rep = cluster["representative"]
        lines.append(f"{i}. {rep['title']}")
        if rep["summary"]:
            lines.append(rep["summary"][:300])
        lines.append(f"🔥 {cluster['mentions']} источников: {', '.join(cluster['sources'][:5])}")
        lines.append(f"🔗 {rep['link']}\n")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"Только проверенные факты | Приоритет: каталог {business}")
    return "\n".join(lines)

# ─── Основной процесс ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Industry News Digest")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="Путь к config.json")
    parser.add_argument("--days", type=int, default=None, help="Глубина в днях (override config)")
    parser.add_argument("--top", type=int, default=None, help="Кол-во новостей (override config)")
    parser.add_argument("--filter", type=str, default="", help="Фильтр по бренду/модели")
    parser.add_argument("--no-llm", action="store_true", help="Отключить LLM, вывести сырой топ")
    args = parser.parse_args()

    config = load_config(args.config)
    days_back = args.days or config.get("days_back", 7)
    top_n = args.top or config.get("top_n", 10)
    threshold = config.get("cluster_threshold", 0.35)
    sources = config.get("sources", [])
    priority_keywords = config.get("priority_keywords", [])
    priority_brands = config.get("priority_brands", [])

    if not sources:
        print("[ERROR] В config.json нет источников (sources). Заполни профиль через SKILL.md.", file=sys.stderr)
        return

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {config.get('business_name', 'Digest')} запущен", file=sys.stderr)
    if args.filter:
        print(f"[INFO] Фильтр: «{args.filter}»", file=sys.stderr)

    all_entries = fetch_rss_entries(sources, days_back, args.filter, priority_keywords, priority_brands)
    if not all_entries:
        print("⚠️ Новостей не найдено. Проверьте доступность RSS-источников.")
        return

    clusters = cluster_entries(all_entries, threshold)
    if not clusters:
        print("⚠️ Не удалось сформировать кластеры.")
        return

    if args.no_llm:
        digest = format_digest_raw(clusters, config, top_n, days_back)
    else:
        print("[INFO] Обработка через LLM...", file=sys.stderr)
        digest = process_with_llm(clusters, config, top_n, days_back)
        if not digest:
            print("[WARN] LLM недоступен, вывод без верификации.", file=sys.stderr)
            digest = format_digest_raw(clusters, config, top_n, days_back)

    print("\n" + digest)

if __name__ == "__main__":
    main()
