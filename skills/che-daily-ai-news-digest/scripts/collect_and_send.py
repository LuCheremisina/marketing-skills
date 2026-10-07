#!/usr/bin/env python3
"""
Daily AI News Digest v5 — сбор новостей из мира ИИ, верификация и отправка в Telegram.

Пайплайн v5:
  RSS → дедупликация → ПОСТ-ФИЛЬТР (военно-политические темы) → ENRICHMENT LAYER
  → SCORING → LLM → POST-PROCESSING → HTML-дайджест → Telegram (HTML-файл)

Доработки v5:
  1. Усиленная дедупликация внутри пачки: 3 критерия (фуззи 0.55 + Jaccard 0.40 + сущностное совпадение)
     При дубле сохраняется более авторитетный источник
  2. Послабляющий критерий: если уникальных новостей < 10, отправляется столько, сколько есть
  3. Пост-фильтр военно-политических тем (до LLM) — ключевые слова + LLM-проверка
  4. Автозапуск bot_subscribe.py при старте (если не запущен)
  5. Генерация красивого HTML-дайджеста и отправка как документа в Telegram

Многоуровневая дедупликация:
  Уровень 1: Точный хэш (SHA-256 от title+link) — отсекает полные дубли
  Уровень 2: Fuzzy-matching заголовков (SequenceMatcher ≥ 0.65) — отсекает перефразировки
  Уровень 3: Ключевые слова заголовков (Jaccard ≥ 0.5) — отсекает одну тему из разных СМИ
  Уровень 4: LLM-контекст предыдущей сводки — LLM знает, что уже отправлялось

Enrichment Layer (v3):
  - Scoring: freshness × 0.3 + mention × 0.3 + authority × 0.2 + business_impact × 0.2
  - Категоризация: Модели / Продукты / Исследования / Регулирование / Влияние на бизнес
  - Целевая аудитория: предприниматель / маркетолог / разработчик
  - Бизнес-инсайт: «Что это значит для бизнеса»
  - Тренды: 2-3 сигнала из батча новостей

Система подписок (v4):
  - Рассылка всем активным подписчикам из data/subscribers.json
  - Управление подписками через bot_subscribe.py (автозапуск при старте)

Запуск выполняется платформой после предоставления Telegram-доступа.
"""

from __future__ import annotations

import os
import sys
import json
import hashlib
import re
import time
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import feedparser
import requests
from openai import OpenAI

from skill_timezone import resolve_skill_timezone, timezone_label

# ─── Конфигурация ───────────────────────────────────────────────────────────

# Токен бота — ТОЛЬКО из переменной окружения. Хардкод запрещён.
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN and not DRY_RUN:
    print("[ERROR] Платформа не предоставила Telegram-доступ для доставки.")
    sys.exit(1)

# Опциональный резервный получатель. Идентификатор не хранится в пакете.
TELEGRAM_FALLBACK_CHAT_ID = os.environ.get("TELEGRAM_FALLBACK_CHAT_ID", "").strip()
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
DIGEST_FOOTER_URL = os.environ.get("DIGEST_FOOTER_URL", "").strip()
DIGEST_FOOTER_LABEL = os.environ.get("DIGEST_FOOTER_LABEL", "configured site").strip()

HISTORY_FILE = os.environ.get(
    "NEWS_HISTORY_FILE",
    str(Path(os.environ.get("DIGEST_DATA_DIR", str(Path.home() / ".local" / "share" / "che-daily-ai-news-digest"))) / "sent_news_history.json"),
)

# Файл подписчиков (управляется bot_subscribe.py)
SUBSCRIBERS_FILE = Path(os.environ.get("DIGEST_DATA_DIR", str(Path.home() / ".local" / "share" / "che-daily-ai-news-digest"))) / "subscribers.json"

# Путь к bot_subscribe.py для автозапуска
BOT_SCRIPT = Path(__file__).parent / "bot_subscribe.py"

# Файл истории запусков (JSONL — одна запись на строку)
RUN_HISTORY_FILE = Path(os.environ.get("DIGEST_DATA_DIR", str(Path.home() / ".local" / "share" / "che-daily-ai-news-digest"))) / "run_history.jsonl"

# Текущая версия агента
AGENT_VERSION = "v6"

MAX_NEWS = int(os.environ.get("MAX_NEWS", "10"))
MIN_NEWS = int(os.environ.get("MIN_NEWS", "5"))

# Пороги дедупликации
FUZZY_THRESHOLD = 0.65       # SequenceMatcher ratio для заголовков (история)
JACCARD_THRESHOLD = 0.50     # Jaccard similarity для ключевых слов заголовков (история)

# Пороги дедупликации ВНУТРИ пачки (строже, чем для истории)
BATCH_FUZZY_THRESHOLD = 0.55    # Более мягкий fuzzy для кросс-источниковых дублей
BATCH_JACCARD_THRESHOLD = 0.40  # Более мягкий Jaccard для кросс-источниковых дублей

# Ключевые сущности — если 2+ совпадают, новости считаются дублями одной темы
KEY_ENTITIES = [
    "openai", "google", "microsoft", "meta", "apple", "amazon", "anthropic",
    "deepmind", "gemini", "gpt", "claude", "llama", "mistral", "sora",
    "copilot", "chatgpt", "dall-e", "stable diffusion", "midjourney",
    "hugging face", "nvidia", "tesla", "perplexity", "groq",
]

# Digest timestamps use SKILL_TIMEZONE (IANA name). Default UTC — do not impose Novosibirsk.
SKILL_TZ = resolve_skill_timezone()

# ─── Авторитет источников (для scoring) ────────────────────────────────────

SOURCE_WEIGHTS = {
    "TechCrunch AI": 1.0,
    "MIT Tech Review": 1.0,
    "OpenAI Blog": 1.0,
    "Google AI Blog": 1.0,
    "The Verge AI": 0.9,
    "VentureBeat AI": 0.85,
    "Wired AI": 0.85,
    "The Decoder": 0.8,
    "Ars Technica AI": 0.8,
    "Hugging Face Blog": 0.8,
    "AI News": 0.75,
    "MarkTechPost": 0.75,
    "Synced Review": 0.75,
    "Engadget AI": 0.75,
    "AI Magazine": 0.7,
    "Habr AI": 0.7,
    "3DNews": 0.6,
}

# ─── RSS-источники (AI / ИИ) ────────────────────────────────────────────────

RSS_FEEDS = [
    # Специализированные AI-издания
    {"url": "https://www.artificialintelligence-news.com/feed/", "name": "AI News", "lang": "en"},
    {"url": "https://the-decoder.com/feed/", "name": "The Decoder", "lang": "en"},
    {"url": "https://venturebeat.com/category/ai/feed/", "name": "VentureBeat AI", "lang": "en"},
    {"url": "https://www.marktechpost.com/feed/", "name": "MarkTechPost", "lang": "en"},
    {"url": "https://syncedreview.com/feed/", "name": "Synced Review", "lang": "en"},
    {"url": "https://aimagazine.com/rss/articles", "name": "AI Magazine", "lang": "en"},
    # Мировые СМИ — рубрика AI
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "name": "Ars Technica AI", "lang": "en"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "name": "The Verge AI", "lang": "en"},
    {"url": "https://www.wired.com/feed/tag/ai/latest/rss", "name": "Wired AI", "lang": "en"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "name": "TechCrunch AI", "lang": "en"},
    {"url": "https://www.technologyreview.com/feed/", "name": "MIT Tech Review", "lang": "en"},
    {"url": "https://www.engadget.com/tag/ai/rss.xml", "name": "Engadget AI", "lang": "en"},
    # Исследования и открытые модели
    {"url": "https://blog.google/technology/ai/rss/", "name": "Google AI Blog", "lang": "en"},
    {"url": "https://openai.com/blog/rss.xml", "name": "OpenAI Blog", "lang": "en"},
    {"url": "https://huggingface.co/blog/feed.xml", "name": "Hugging Face Blog", "lang": "en"},
    # Русскоязычные
    {"url": "https://habr.com/ru/rss/hub/artificial_intelligence/all/?fl=ru", "name": "Habr AI", "lang": "ru"},
    {"url": "https://3dnews.ru/news/rss/", "name": "3DNews", "lang": "ru"},
]

# ─── Стоп-слова для Jaccard (не несут смысловой нагрузки) ──────────────────

STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "further", "then", "once", "and", "but", "or",
    "nor", "not", "so", "yet", "both", "either", "neither", "each", "every",
    "all", "any", "few", "more", "most", "other", "some", "such", "no",
    "only", "own", "same", "than", "too", "very", "just", "how", "what",
    "which", "who", "whom", "this", "that", "these", "those", "it", "its",
    "new", "says", "said", "about", "up", "now", "also", "get", "gets",
    "got", "like", "make", "makes", "use", "uses", "using", "used",
    # Русские стоп-слова
    "и", "в", "на", "с", "по", "для", "из", "к", "о", "от", "за", "не",
    "что", "как", "это", "все", "но", "он", "она", "они", "его", "её",
    "их", "мы", "вы", "был", "была", "были", "будет", "уже", "ещё",
    "при", "до", "после", "между", "через", "над", "под", "без",
})

# ─── Ключевые слова для пост-фильтра военно-политических тем ───────────────

BANNED_KEYWORDS = [
    # Военная тематика
    "pentagon", "military", "defense", "defence", "weapon", "warfare", "army",
    "navy", "air force", "missile", "bomb", "drone strike", "battlefield",
    "national security", "intelligence agency", "cia", "nsa", "dod",
    "department of defense", "armed forces", "combat", "surveillance drone",
    "war", "nato", "troops", "soldier", "spy",
    # Политика
    "congress", "senate", "white house", "president", "election", "democrat",
    "republican", "legislation", "bill passed", "executive order",
    "geopolitics", "sanctions", "tariff", "trade war", "diplomat",
    # M&A и инвестиции
    "funding round", "series a", "series b", "series c", "ipo",
    "acquisition", "merger", "acquires", "acquired by", "valuation",
    "raises", "billion", "venture capital", "investor", "investment round",
    # Русские эквиваленты
    "пентагон", "военн", "оборон", "армия", "нато", "разведк", "шпионаж",
    "ракет", "оружие", "боевой", "минобороны", "спецслужб",
    "финансирование", "раунд", "инвестиц", "слияние", "поглощение",
    "оценка компании", "ipo", "выход на биржу",
]


# ─── Доработка 2: Автозапуск bot_subscribe.py ──────────────────────────────


def ensure_bot_running():
    """
    Убедиться, что bot_subscribe.py запущен.
    Если процесс не найден — запустить в фоне.
    """
    try:
        # Проверяем, запущен ли процесс
        result = subprocess.run(
            ["pgrep", "-f", "bot_subscribe.py"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            pid = result.stdout.strip()
            print(f"[INFO] bot_subscribe.py уже запущен (PID: {pid})")
            return

        # Запускаем бота в фоне
        log_path = Path(__file__).parent.parent / "data" / "bot_subscribe.log"
        with open(log_path, "a") as log_file:
            proc = subprocess.Popen(
                [sys.executable, str(BOT_SCRIPT)],
                stdout=log_file,
                stderr=log_file,
                env=os.environ.copy(),
                start_new_session=True,
            )
        print(f"[INFO] bot_subscribe.py запущен в фоне (PID: {proc.pid})")
        time.sleep(2)  # Даём боту время на инициализацию
    except Exception as e:
        print(f"[WARN] Не удалось проверить/запустить bot_subscribe.py: {e}")


# ─── Утилиты ────────────────────────────────────────────────────────────────


def news_hash(title: str, link: str) -> str:
    """Создать уникальный хэш новости по заголовку и ссылке."""
    raw = f"{title.strip().lower()}|{link.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_title(title: str) -> str:
    """Нормализовать заголовок для сравнения: lowercase, убрать пунктуацию."""
    t = title.strip().lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_keywords(title: str) -> set:
    """Извлечь значимые ключевые слова из заголовка."""
    normalized = normalize_title(title)
    words = set(normalized.split())
    return words - STOP_WORDS


def fuzzy_match(title_a: str, title_b: str) -> float:
    """Fuzzy-сравнение двух заголовков (SequenceMatcher)."""
    return SequenceMatcher(None, normalize_title(title_a), normalize_title(title_b)).ratio()


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity между двумя множествами."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ─── История (расширенная) ─────────────────────────────────────────────────


def load_history() -> dict:
    """Загрузить историю отправленных новостей (расширенный формат)."""
    path = Path(HISTORY_FILE)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Миграция: если старый формат (только sent_hashes), конвертируем
                if "sent_entries" not in data:
                    data["sent_entries"] = []
                    data["sent_titles"] = []
                    data["previous_digest_titles"] = []
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "sent_hashes": [],
        "sent_entries": [],       # [{title, link, hash, source, date}]
        "sent_titles": [],        # нормализованные заголовки для fuzzy-matching
        "previous_digest_titles": [],  # заголовки из последней сводки (для LLM-контекста)
        "last_update": None,
    }


def save_history(history: dict):
    """Сохранить историю отправленных новостей."""
    path = Path(HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Ограничение размера истории
    max_entries = 2000
    if len(history.get("sent_hashes", [])) > max_entries:
        history["sent_hashes"] = history["sent_hashes"][-max_entries:]
    if len(history.get("sent_entries", [])) > max_entries:
        history["sent_entries"] = history["sent_entries"][-max_entries:]
    if len(history.get("sent_titles", [])) > max_entries:
        history["sent_titles"] = history["sent_titles"][-max_entries:]
    history["last_update"] = datetime.now(SKILL_TZ).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ─── Сбор новостей ──────────────────────────────────────────────────────────


def fetch_rss_entries() -> list:
    """Собрать записи из всех RSS-лент за последние 24 часа (fallback 36ч)."""
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_36h = datetime.now(timezone.utc) - timedelta(hours=36)
    entries_24h = []
    entries_36h = []

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:15]:
                pub_date = None
                for date_field in ("published_parsed", "updated_parsed"):
                    parsed = getattr(entry, date_field, None)
                    if parsed:
                        pub_date = datetime(*parsed[:6], tzinfo=timezone.utc)
                        break

                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                summary = getattr(entry, "summary", "").strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:500]

                if not (title and link):
                    continue

                entry_data = {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": feed_info["name"],
                    "lang": feed_info["lang"],
                    "pub_date": pub_date.isoformat() if pub_date else None,
                    "pub_date_dt": pub_date,  # datetime объект для scoring
                    "hash": news_hash(title, link),
                    # Поля Enrichment Layer (заполняются позже)
                    "score": 0.0,
                    "freshness_score": 0.0,
                    "mention_score": 0.0,
                    "authority_score": 0.0,
                    "business_impact_score": 0.0,
                    "category": "",
                    "target_audience": [],
                    "business_insight": "",
                    "trend_signal": False,
                }

                if pub_date:
                    if pub_date >= cutoff_24h:
                        entries_24h.append(entry_data)
                        entries_36h.append(entry_data)
                    elif pub_date >= cutoff_36h:
                        entries_36h.append(entry_data)
                else:
                    entries_24h.append(entry_data)
                    entries_36h.append(entry_data)

        except Exception as e:
            print(f"[WARN] Ошибка при парсинге {feed_info['name']}: {e}")

    # Если за 24ч мало новостей, расширяем до 36ч
    if len(entries_24h) >= 15:
        print(f"[INFO] Используем окно 24ч: {len(entries_24h)} записей")
        return entries_24h
    else:
        print(f"[INFO] Мало записей за 24ч ({len(entries_24h)}), расширяем до 36ч: {len(entries_36h)} записей")
        return entries_36h


# ─── Доработка 1: Пост-фильтр военно-политических тем ─────────────────────


def keyword_filter_banned(entries: list) -> list:
    """
    Быстрый пост-фильтр по ключевым словам.
    Отсекает новости с явными военно-политическими и инвестиционными маркерами
    ещё до LLM-обработки.
    """
    result = []
    removed = 0
    for entry in entries:
        text_to_check = (entry["title"] + " " + entry["summary"]).lower()
        is_banned = False
        for kw in BANNED_KEYWORDS:
            if kw.lower() in text_to_check:
                is_banned = True
                break
        if not is_banned:
            result.append(entry)
        else:
            removed += 1

    if removed:
        print(f"  [PostFilter] Ключевые слова: отсеяно {removed} военно-политических/инвестиционных новостей")
    return result


def llm_filter_banned(entries: list) -> list:
    """
    Дополнительный LLM-пост-фильтр для тонких случаев.
    Проверяет новости, которые прошли keyword-фильтр, но могут содержать
    скрытую военно-политическую или инвестиционную тематику.
    Работает батчем — один запрос на все новости.
    """
    if not entries:
        return entries

    client = OpenAI()

    entries_text = ""
    for i, e in enumerate(entries, 1):
        entries_text += f"{i}. [{e['source']}] {e['title']}\n   {e['summary'][:200]}\n\n"

    prompt = f"""Ты — строгий редактор AI-новостей. Проверь каждую новость из списка.

ЗАДАЧА: Для каждой новости определи, нужно ли её ИСКЛЮЧИТЬ из AI-дайджеста.

ИСКЛЮЧАТЬ (вернуть "exclude": true) если новость:
- О военном применении AI (Пентагон, армия, оборона, разведка, военные контракты, оружие)
- О политике (выборы, конгресс, законопроекты, санкции, геополитика)
- Об инвестициях (раунды финансирования, оценки компаний, IPO, M&A, слияния)
- О государственных контрактах с военными ведомствами
- Косвенно связана с военными/разведывательными организациями как основная тема

ОСТАВЛЯТЬ (вернуть "exclude": false) если новость:
- О новых AI-моделях, исследованиях, продуктах
- О применении AI в бизнесе, медицине, образовании, творчестве
- О регулировании AI (законы о конфиденциальности, авторские права, безопасность AI)
- О технических достижениях, бенчмарках, открытых моделях

Верни ТОЛЬКО валидный JSON-массив без комментариев:
[{{"idx": 1, "exclude": false, "reason": "AI-модель"}}, ...]

СПИСОК НОВОСТЕЙ:
{entries_text}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            decisions = json.loads(json_match.group(0))
            excluded_indices = set()
            excluded_reasons = []
            for d in decisions:
                idx = d.get("idx", 0) - 1
                if d.get("exclude") and 0 <= idx < len(entries):
                    excluded_indices.add(idx)
                    excluded_reasons.append(f"  #{idx+1} '{entries[idx]['title'][:60]}' → {d.get('reason', '')}")

            result = [e for i, e in enumerate(entries) if i not in excluded_indices]
            if excluded_indices:
                print(f"  [PostFilter LLM] Исключено {len(excluded_indices)} новостей:")
                for r in excluded_reasons:
                    print(r)
            return result
        else:
            print("[WARN] LLM-фильтр: не удалось извлечь JSON, пропускаем")
            return entries
    except Exception as e:
        print(f"[WARN] Ошибка LLM-фильтра: {e}. Пропускаем.")
        return entries


def apply_post_filter(entries: list) -> list:
    """
    Полный пост-фильтр: сначала keyword-фильтр, затем LLM-проверка.
    """
    print(f"[INFO] Пост-фильтр военно-политических тем: {len(entries)} новостей на входе")
    entries = keyword_filter_banned(entries)
    entries = llm_filter_banned(entries)
    print(f"[INFO] После пост-фильтра: {len(entries)} новостей")
    return entries


# ─── Многоуровневая дедупликация ──────────────────────────────────────────


def dedup_level1_hash(entries: list, history: dict) -> list:
    """Уровень 1: Точный хэш — отсекает полные дубликаты."""
    sent_hashes = set(history.get("sent_hashes", []))
    result = [e for e in entries if e["hash"] not in sent_hashes]
    removed = len(entries) - len(result)
    if removed:
        print(f"  [Dedup L1] Хэш: отсеяно {removed} полных дубликатов")
    return result


def dedup_level2_fuzzy(entries: list, history: dict) -> list:
    """Уровень 2: Fuzzy-matching заголовков — отсекает перефразировки."""
    sent_titles = history.get("sent_titles", [])
    if not sent_titles:
        return entries

    result = []
    removed = 0
    for entry in entries:
        is_dup = False
        norm_title = normalize_title(entry["title"])
        for old_title in sent_titles[-500:]:  # Проверяем последние 500
            if fuzzy_match(norm_title, old_title) >= FUZZY_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            result.append(entry)
        else:
            removed += 1

    if removed:
        print(f"  [Dedup L2] Fuzzy: отсеяно {removed} перефразировок")
    return result


def dedup_level3_jaccard(entries: list, history: dict) -> list:
    """Уровень 3: Jaccard ключевых слов — отсекает одну тему из разных СМИ."""
    sent_titles = history.get("sent_titles", [])
    if not sent_titles:
        return entries

    # Предвычисляем keywords для истории
    history_keywords = [title_keywords(t) for t in sent_titles[-500:]]

    result = []
    removed = 0
    for entry in entries:
        is_dup = False
        entry_kw = title_keywords(entry["title"])
        if len(entry_kw) < 2:
            result.append(entry)
            continue
        for old_kw in history_keywords:
            if jaccard_similarity(entry_kw, old_kw) >= JACCARD_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            result.append(entry)
        else:
            removed += 1

    if removed:
        print(f"  [Dedup L3] Jaccard: отсеяно {removed} тематических дубликатов")
    return result


def _entity_overlap(title_a: str, title_b: str) -> int:
    """Подсчитать количество совпадающих ключевых сущностей в двух заголовках."""
    a_lower = title_a.lower()
    b_lower = title_b.lower()
    count = 0
    for entity in KEY_ENTITIES:
        if entity in a_lower and entity in b_lower:
            count += 1
    return count


def dedup_within_batch(entries: list) -> list:
    """
    Усиленная дедупликация внутри текущей пачки (одна тема из разных СМИ).

    Три критерия — новость считается дублём если выполняется ХОТЯ БЫ ОДИН:
      1. Fuzzy-matching заголовков >= BATCH_FUZZY_THRESHOLD (0.55)
      2. Jaccard ключевых слов >= BATCH_JACCARD_THRESHOLD (0.40)
      3. 2+ совпадающих ключевых сущностей (OpenAI, Sora, Copilot и т.д.)
         И при этом Jaccard >= 0.25 (чтобы не отсекать разные новости об одной компании)

    При дубле сохраняется новость с более высоким authority_score источника.
    """
    if not entries:
        return entries

    result = []
    removed = 0
    for entry in entries:
        is_dup = False
        entry_kw = title_keywords(entry["title"])
        norm_title = normalize_title(entry["title"])
        entry_authority = SOURCE_WEIGHTS.get(entry["source"], 0.65)

        for idx, existing in enumerate(result):
            existing_kw = title_keywords(existing["title"])
            existing_norm = normalize_title(existing["title"])

            # Критерий 1: fuzzy (снижен порог)
            if fuzzy_match(norm_title, existing_norm) >= BATCH_FUZZY_THRESHOLD:
                is_dup = True
                # Заменяем на более авторитетный источник
                if entry_authority > SOURCE_WEIGHTS.get(existing["source"], 0.65):
                    result[idx] = entry
                break

            # Критерий 2: Jaccard ключевых слов (снижен порог)
            if len(entry_kw) >= 2 and len(existing_kw) >= 2:
                if jaccard_similarity(entry_kw, existing_kw) >= BATCH_JACCARD_THRESHOLD:
                    is_dup = True
                    if entry_authority > SOURCE_WEIGHTS.get(existing["source"], 0.65):
                        result[idx] = entry
                    break

            # Критерий 3: сущностное совпадение (2+ сущностей + слабый Jaccard)
            if len(entry_kw) >= 2 and len(existing_kw) >= 2:
                entity_hits = _entity_overlap(entry["title"], existing["title"])
                if entity_hits >= 2 and jaccard_similarity(entry_kw, existing_kw) >= 0.25:
                    is_dup = True
                    if entry_authority > SOURCE_WEIGHTS.get(existing["source"], 0.65):
                        result[idx] = entry
                    break

        if not is_dup:
            result.append(entry)
        else:
            removed += 1

    if removed:
        print(f"  [Dedup Batch] Внутри пачки: отсеяно {removed} кросс-источниковых дублей")
    return result


def full_dedup_pipeline(entries: list, history: dict) -> list:
    """Полный пайплайн дедупликации (4 уровня)."""
    print(f"[INFO] Дедупликация: {len(entries)} записей на входе")

    entries = dedup_level1_hash(entries, history)
    entries = dedup_level2_fuzzy(entries, history)
    entries = dedup_level3_jaccard(entries, history)
    entries = dedup_within_batch(entries)

    print(f"[INFO] После дедупликации: {len(entries)} уникальных записей")
    return entries


# ─── ENRICHMENT LAYER ──────────────────────────────────────────────────────


def calculate_scores(entries: list) -> list:
    """
    Рассчитать scoring для каждой новости.

    Формула: score = freshness*0.3 + mention*0.3 + authority*0.2 + business_impact*0.2
    business_impact_score заполняется позже через LLM (enrich_with_llm).
    """
    now_utc = datetime.now(timezone.utc)

    # Шаг 1: freshness_score и authority_score (без LLM)
    for entry in entries:
        # Freshness
        pub_dt = entry.get("pub_date_dt")
        if pub_dt:
            age_hours = (now_utc - pub_dt).total_seconds() / 3600
            if age_hours < 6:
                entry["freshness_score"] = 1.0
            elif age_hours < 12:
                entry["freshness_score"] = 0.8
            elif age_hours < 24:
                entry["freshness_score"] = 0.6
            else:
                entry["freshness_score"] = 0.4
        else:
            entry["freshness_score"] = 0.5  # Нет даты — средний балл

        # Authority
        entry["authority_score"] = SOURCE_WEIGHTS.get(entry["source"], 0.65)

    # Шаг 2: mention_score — считаем похожие новости внутри батча
    for i, entry in enumerate(entries):
        entry_kw = title_keywords(entry["title"])
        norm_title = normalize_title(entry["title"])
        count_similar = 0

        for j, other in enumerate(entries):
            if i == j:
                continue
            other_kw = title_keywords(other["title"])
            other_norm = normalize_title(other["title"])
            if (fuzzy_match(norm_title, other_norm) >= 0.5 or
                    (len(entry_kw) >= 2 and len(other_kw) >= 2 and
                     jaccard_similarity(entry_kw, other_kw) >= 0.35)):
                count_similar += 1

        entry["mention_score"] = min(1.0, count_similar / 5)

    print(f"[INFO] Scoring (без business_impact): рассчитан для {len(entries)} записей")
    return entries


def enrich_with_llm(entries: list) -> list:
    """
    Обогатить новости через LLM (один батч-запрос):
    - business_impact_score (0-1)
    - category (Модели / Продукты / Исследования / Регулирование / Влияние на бизнес)
    - target_audience (предприниматель / маркетолог / разработчик)
    - business_insight (1-2 предложения)
    """
    if not entries:
        return entries

    client = OpenAI()

    # Формируем батч-запрос
    entries_text = ""
    for i, e in enumerate(entries[:40], 1):  # Ограничиваем батч до 40 новостей
        entries_text += (
            f"{i}. [{e['source']}] {e['title']}\n"
            f"   {e['summary'][:200]}\n\n"
        )

    prompt = f"""Ты — аналитик AI-рынка. Для каждой новости из списка верни JSON-массив объектов.

Для каждой новости определи:
1. "business_impact": число от 0 до 1 (влияние на бизнес: влияет на выручку, снижает издержки, меняет рынок)
2. "category": одна из: "Модели", "Продукты", "Исследования", "Регулирование", "Влияние на бизнес"
3. "audience": массив из подмножества ["предприниматель", "маркетолог", "разработчик"]
4. "insight": 1-2 предложения на русском — что это значит для бизнеса

Верни ТОЛЬКО валидный JSON-массив без комментариев. Пример:
[
  {{"idx": 1, "business_impact": 0.8, "category": "Модели", "audience": ["разработчик", "предприниматель"], "insight": "Новая модель снизит стоимость генерации контента на 40%."}},
  ...
]

СПИСОК НОВОСТЕЙ:
{entries_text}

Верни массив из {min(len(entries), 40)} объектов, по одному на каждую новость."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()

        # Извлекаем JSON из ответа
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            enrichments = json.loads(json_match.group(0))
            for item in enrichments:
                idx = item.get("idx", 0) - 1
                if 0 <= idx < len(entries):
                    entries[idx]["business_impact_score"] = float(item.get("business_impact", 0.5))
                    entries[idx]["category"] = item.get("category", "")
                    entries[idx]["target_audience"] = item.get("audience", [])
                    entries[idx]["business_insight"] = item.get("insight", "")
            print(f"[INFO] LLM enrichment: обогащено {len(enrichments)} новостей")
        else:
            print("[WARN] LLM enrichment: не удалось извлечь JSON, используем дефолты")
            _apply_default_enrichment(entries)

    except Exception as e:
        print(f"[WARN] Ошибка LLM enrichment: {e}. Используем дефолты.")
        _apply_default_enrichment(entries)

    # Финальный расчёт итогового score
    for entry in entries:
        entry["score"] = (
            entry["freshness_score"] * 0.3 +
            entry["mention_score"] * 0.3 +
            entry["authority_score"] * 0.2 +
            entry["business_impact_score"] * 0.2
        )

    return entries


def _apply_default_enrichment(entries: list):
    """Применить дефолтные значения enrichment при ошибке LLM."""
    for entry in entries:
        if not entry.get("business_impact_score"):
            entry["business_impact_score"] = 0.5
        if not entry.get("category"):
            entry["category"] = "Продукты"
        if not entry.get("target_audience"):
            entry["target_audience"] = ["предприниматель", "разработчик"]
        if not entry.get("business_insight"):
            entry["business_insight"] = ""


def detect_trends(entries: list) -> list:
    """
    Выявить 2-3 тренда из батча новостей через LLM.
    Возвращает список {"trend": str, "confidence": float}.
    """
    if not entries:
        return []

    client = OpenAI()

    # Собираем заголовки и категории для анализа
    news_summary = ""
    for i, e in enumerate(entries[:30], 1):
        cat = e.get("category", "")
        news_summary += f"{i}. [{cat}] {e['title']}\n"

    prompt = f"""Ты — аналитик AI-трендов. Проанализируй список новостей и выяви 2-3 ключевых тренда.

Верни ТОЛЬКО валидный JSON-массив без комментариев:
[
  {{"trend": "Название тренда на русском", "confidence": 0.8}},
  ...
]

Confidence — уверенность от 0 до 1 (насколько явно тренд прослеживается в новостях).

СПИСОК НОВОСТЕЙ:
{news_summary}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            trends = json.loads(json_match.group(0))
            print(f"[INFO] Тренды выявлены: {[t.get('trend') for t in trends]}")
            return trends
    except Exception as e:
        print(f"[WARN] Ошибка detect_trends: {e}")

    return []


def run_enrichment_pipeline(entries: list) -> tuple:
    """
    Полный Enrichment Layer:
    1. calculate_scores (без LLM)
    2. enrich_with_llm (batch: business_impact, category, audience, insight)
    3. Сортировка по score
    4. detect_trends

    Возвращает (top_entries, trends).
    """
    print("[INFO] Запуск Enrichment Layer...")

    # Шаг 1: Базовый scoring
    entries = calculate_scores(entries)

    # Шаг 2: LLM enrichment (один батч-запрос)
    entries = enrich_with_llm(entries)

    # Шаг 3: Сортировка по итоговому score
    entries.sort(key=lambda x: x["score"], reverse=True)
    print(f"[INFO] После scoring: топ-3 источника = {[e['source'] for e in entries[:3]]}")

    # Шаг 4: Тренды (отдельный LLM-запрос)
    trends = detect_trends(entries[:20])

    # Передаём в LLM только TOP-20
    top_entries = entries[:20]
    print(f"[INFO] В LLM передаётся {len(top_entries)} записей (TOP-20 по score)")

    return top_entries, trends


# ─── LLM-обработка ─────────────────────────────────────────────────────────


def process_with_llm(entries: list, history: dict, trends: list = None) -> str | None:
    """
    Отправить обогащённые новости в LLM для:
    1. Отбора строго 10 самых обсуждаемых в сети
    2. Исключения инвестиций, политики, военной тематики, M&A (усиленный промпт)
    3. Фейк-чека
    4. Перевода на русский
    5. Форматирования в Telegram-сводку с новыми полями
    6. Проверки на повторы с предыдущей сводкой (Уровень 4)
    """
    if not entries:
        return None

    client = OpenAI()

    entries_text = ""
    for i, e in enumerate(entries[:20], 1):
        audience_str = ", ".join(e.get("target_audience", [])) or "все"
        insight = e.get("business_insight", "")
        entries_text += (
            f"{i}. [{e['source']}] {e['title']}\n"
            f"   Ссылка: {e['link']}\n"
            f"   Описание: {e['summary'][:300]}\n"
            f"   Дата: {e['pub_date'] or 'неизвестна'}\n"
            f"   Score: {e['score']:.2f} | Категория: {e.get('category', '')} | "
            f"Аудитория: {audience_str}\n"
            f"   Бизнес-инсайт: {insight}\n\n"
        )

    today = datetime.now(SKILL_TZ).strftime("%d.%m.%Y")

    # Контекст предыдущей сводки для LLM (Уровень 4 дедупликации)
    prev_titles = history.get("previous_digest_titles", [])
    prev_context = ""
    if prev_titles:
        prev_list = "\n".join(f"- {t}" for t in prev_titles[-10:])
        prev_context = f"""

ВАЖНО — ПРЕДЫДУЩАЯ СВОДКА СОДЕРЖАЛА ЭТИ ТЕМЫ (НЕ ПОВТОРЯТЬ!):
{prev_list}

Если в списке ниже есть новости на те же темы (даже если из другого источника или с другим заголовком) — НЕ включай их. Выбирай ТОЛЬКО действительно НОВЫЕ темы, которых не было в предыдущей сводке.
"""

    available_count = len(entries[:20])
    target_count = min(available_count, MAX_NEWS)
    count_instruction = (
        f"СТРОГО {target_count} новостей — ровно столько, сколько есть уникальных (не больше, не меньше)"
        if available_count < MAX_NEWS
        else "СТРОГО 10 новостей — ровно 10, не больше и не меньше"
    )
    split_instruction = f"Первые {min(5, target_count)} — из разных источников (наиболее резонансные)"

    prompt = f"""Ты — профессиональный редактор новостной сводки по искусственному интеллекту.

ЗАДАЧА: Из списка новостей ниже отбери {count_instruction} самых обсуждаемых новостей из мира AI за последние 24 часа. {split_instruction}.
{prev_context}ПРАВИЛА ОТБОРА:
1. ТЕМАТИКА: новости про искусственный интеллект — новые модели, исследования, продукты, обновления, применение AI в бизнесе/медицине/образовании, открытые модели, бенчмарки, прорывы.
2. СТРОГО ИСКЛЮЧИТЬ (НЕЛЬЗЯ включать ни при каких условиях):
   — Военная тематика: Пентагон, армия, оборона, разведка, ЦРУ, АНБ, военные контракты, оружие, боевые системы, национальная безопасность в военном контексте
   — Государственные контракты с военными ведомствами (даже если там упоминается AI)
   — Политика: выборы, конгресс, законопроекты политического характера, санкции, геополитика
   — Инвестиции: раунды финансирования, оценки стоимости компаний, IPO, слияния и поглощения (M&A)
   — Если новость связана с правительством/государством — включай ТОЛЬКО если она о регулировании AI (законы о конфиденциальности, авторские права, безопасность AI), но НЕ о военных или политических вопросах
3. ФЕЙК-ЧЕК: включай ТОЛЬКО новости, подтверждённые надёжными источниками. Отсеивай слухи без подтверждения, кликбейт, рекламные материалы.
4. ПРИОРИТЕТ: учитывай поле Score при отборе — новости с более высоким Score важнее. Крупные релизы моделей, важные исследования, значимые обновления продуктов.
5. КОЛИЧЕСТВО КРИТИЧНО: включи ровно {target_count} новостей — не больше и не меньше. Если подходящих уникальных новостей меньше {target_count} — включи столько, сколько есть. НИКОГДА не добавляй заглушки, пояснения, комментарии или повторы вместо реальных новостей.
6. ЗАПРЕЩЕНО: добавлять пункты с пометками «(Новость уже включена...)», «(В списке больше нет...)», «(Нет подходящих...)» или любыми другими объяснениями вместо реальной новости. Если новостей не хватает — просто заверши список на последней реальной новости.
7. Каждая новость ОБЯЗАТЕЛЬНО должна содержать прямую ссылку на ОДИН первоисточник (только один источник на новость).
8. НЕ ПОВТОРЯТЬ темы из предыдущей сводки. Одна тема = одна новость, даже если её освещают несколько СМИ.
9. НЕ ПЕРЕПИСЫВАТЬ бизнес-инсайт — используй его как есть (поле «Бизнес-инсайт» из входных данных).
10. Используй поле «Категория» и «Аудитория» из входных данных.

ФОРМАТ ОТВЕТА:
- Используй ТОЛЬКО обычный текст, без markdown-разметки
- Заголовок сводки: 🤖 УТРЕННЯЯ СВОДКА — МИР ИСКУССТВЕННОГО ИНТЕЛЛЕКТА | {today}
- Каждая новость нумеруется (1., 2., ...)
- Формат каждой новости:
  Номер. ЗАГОЛОВОК НА РУССКОМ (краткий, информативный)
  Подробное описание на 2-3 предложения на русском языке. Экспертный тон, развёрнутый стиль.
  Источник: Название | Ссылка
  Категория: [категория] | Для кого: [аудитория]
  Что это значит для бизнеса: [бизнес-инсайт]
- В конце: разделитель и подпись «Подготовлено ai-агентом | Только проверенные факты» plus optional customer footer URL if configured

СПИСОК НОВОСТЕЙ ДЛЯ АНАЛИЗА:
{entries_text}

Ответ должен быть ТОЛЬКО готовым текстом сводки, без комментариев."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=5000,
        )
        digest = response.choices[0].message.content.strip()

        # POST-PROCESSING 1: удалить пункты-заглушки (LLM иногда добавляет их вместо реальных новостей)
        digest = sanitize_digest(digest)

        # POST-PROCESSING 2: добавить блок трендов в конец (перед подписью)
        if trends:
            digest = _inject_trends_block(digest, trends)

        return digest
    except Exception as e:
        print(f"[ERROR] Ошибка LLM: {e}")
        return None


def sanitize_digest(digest: str) -> str:
    """
    Удалить пункты-заглушки из сводки.

    LLM иногда возвращает пункты вида:
      10. Заголовок\n(Новость уже включена в пункт 1, поэтому не дублируется...)
      10. Заголовок\n(В списке больше подходящих уникальных новостей нет.)
    Такие пункты нужно полностью удалить, а нумерацию оставшихся — исправить.
    """
    # Паттерны-заглушки в описании новости (первая строка после заголовка)
    PLACEHOLDER_PATTERNS = [
        r"\(Новость уже включена",
        r"\(В списке больше",
        r"\(Нет подходящих",
        r"\(Подходящих новостей",
        r"\(Все подходящие",
        r"\(Уникальных новостей",
        r"\(Дублируется",
        r"поэтому не дублируется",
        r"вместо неё включена следующая",
        r"больше подходящих уникальных новостей",
    ]

    lines = digest.split("\n")
    result_blocks = []  # Список блоков (каждый блок — список строк одной новости)
    current_block = []
    in_news_block = False

    for line in lines:
        num_match = re.match(r"^(\d+)\.\s+.+$", line.strip())
        if num_match:
            # Начало нового пункта — сохраняем предыдущий блок
            if current_block:
                result_blocks.append(current_block)
            current_block = [line]
            in_news_block = True
        else:
            current_block.append(line)

    if current_block:
        result_blocks.append(current_block)

    # Фильтруем блоки-заглушки
    clean_blocks = []
    for block in result_blocks:
        # Проверяем первые 3 строки блока на наличие паттернов-заглушек
        block_text = " ".join(block[:4])
        is_placeholder = any(
            re.search(pattern, block_text, re.IGNORECASE)
            for pattern in PLACEHOLDER_PATTERNS
        )
        if not is_placeholder:
            clean_blocks.append(block)
        else:
            # Определяем заголовок удалённого пункта для лога
            title_line = block[0] if block else "?"
            print(f"  [Sanitize] Удалён пункт-заглушка: {title_line[:80]}")

    if len(clean_blocks) < len(result_blocks):
        removed = len(result_blocks) - len(clean_blocks)
        print(f"[INFO] Sanitize: удалено {removed} пунктов-заглушек из сводки")

        # Перенумеровываем оставшиеся пункты-новости
        news_counter = 0
        renumbered_blocks = []
        for block in clean_blocks:
            first_line = block[0].strip()
            if re.match(r"^\d+\.\s+", first_line):
                news_counter += 1
                # Заменяем номер
                new_first = re.sub(r"^\d+\.", f"{news_counter}.", first_line)
                renumbered_blocks.append([new_first] + block[1:])
            else:
                renumbered_blocks.append(block)
        clean_blocks = renumbered_blocks

    # Собираем обратно в текст
    result_lines = []
    for block in clean_blocks:
        result_lines.extend(block)

    return "\n".join(result_lines)


def _inject_trends_block(digest: str, trends: list) -> str:
    """Добавить блок трендов в конец сводки перед подписью."""
    if not trends:
        return digest

    trend_lines = []
    for t in trends:
        trend_name = t.get("trend", "")
        confidence = t.get("confidence", 0)
        if trend_name:
            # Простая интерпретация тренда
            if confidence >= 0.7:
                trend_lines.append(f"— растёт: {trend_name}")
            else:
                trend_lines.append(f"— формируется: {trend_name}")

    if not trend_lines:
        return digest

    trends_block = "\n\n📊 Тренды дня:\n" + "\n".join(trend_lines)

    # Вставляем перед подписью
    signature = "Подготовлено ai-агентом"
    if signature in digest:
        idx = digest.rfind(signature)
        # Находим начало строки с подписью
        line_start = digest.rfind("\n", 0, idx)
        if line_start == -1:
            line_start = 0
        digest = digest[:line_start] + trends_block + "\n\n" + digest[line_start:].lstrip("\n")
    else:
        digest += trends_block

    return digest


def extract_digest_titles(digest_text: str) -> list:
    """Извлечь заголовки из сформированной сводки (для сохранения в историю)."""
    titles = []
    pattern = r"^\d+\.\s+(.+)$"
    for line in digest_text.split("\n"):
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            title = match.group(1).strip()
            if len(title) > 10:
                titles.append(title)
    return titles


def validate_generated_digest(digest_text: str, html_content: str) -> list[str]:
    """Return blocking QA issues before any external delivery."""
    issues: list[str] = []
    titles = extract_digest_titles(digest_text)
    source_urls = re.findall(
        r"^Источник:\s*.+?\s*\|\s*(https?://\S+)", digest_text, flags=re.MULTILINE
    )

    if len(titles) < MIN_NEWS:
        issues.append(f"новостей {len(titles)}, минимум {MIN_NEWS}")
    if len(titles) > MAX_NEWS:
        issues.append(f"новостей {len(titles)}, максимум {MAX_NEWS}")
    if len(source_urls) != len(titles):
        issues.append(
            f"прямых ссылок на источники {len(source_urls)}, новостей {len(titles)}"
        )
    if html_content.count('class="news-card"') != len(titles):
        issues.append("число HTML-карточек не совпадает с числом новостей")
    if not html_content.lstrip().lower().startswith("<!doctype html>"):
        issues.append("HTML не содержит корректный doctype")
    if "</html>" not in html_content.lower():
        issues.append("HTML не завершён")
    if any(marker in html_content for marker in ("{{", "}}", "TODO", "example.com")):
        issues.append("HTML содержит placeholder или тестовое значение")
    return issues


def extract_used_entries(digest_text: str, entries: list) -> list:
    """Определить, какие новости вошли в сводку (по ссылкам)."""
    used = []
    for e in entries:
        if e["link"] in digest_text:
            used.append(e)
    return used


# ─── Доработка 3: Генерация HTML-дайджеста ─────────────────────────────────


def generate_html_digest(digest_text: str, trends: list = None) -> str:
    """
    Генерирует красивый HTML-файл из текстовой сводки.
    Возвращает HTML-строку.
    """
    today = datetime.now(SKILL_TZ).strftime("%d.%m.%Y")
    today_full = datetime.now(SKILL_TZ).strftime("%d %B %Y").replace(
        "January", "января").replace("February", "февраля").replace(
        "March", "марта").replace("April", "апреля").replace(
        "May", "мая").replace("June", "июня").replace(
        "July", "июля").replace("August", "августа").replace(
        "September", "сентября").replace("October", "октября").replace(
        "November", "ноября").replace("December", "декабря")

    # Парсим новости из текста
    news_items = []
    lines = digest_text.split("\n")
    i = 0
    current_item = None

    while i < len(lines):
        line = lines[i].strip()

        # Новый элемент новости (начинается с цифры и точки)
        num_match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if num_match:
            if current_item:
                news_items.append(current_item)
            current_item = {
                "num": num_match.group(1),
                "title": num_match.group(2).strip(),
                "description": "",
                "source_name": "",
                "source_url": "",
                "category": "",
                "audience": "",
                "insight": "",
            }
            i += 1
            continue

        if current_item:
            # Источник
            src_match = re.match(r"^Источник:\s*(.+?)\s*\|\s*(https?://\S+)", line)
            if src_match:
                current_item["source_name"] = src_match.group(1).strip()
                current_item["source_url"] = src_match.group(2).strip()
                i += 1
                continue

            # Категория и аудитория
            cat_match = re.match(r"^Категория:\s*\[?(.+?)\]?\s*\|\s*Для кого:\s*\[?(.+?)\]?$", line)
            if cat_match:
                current_item["category"] = cat_match.group(1).strip()
                current_item["audience"] = cat_match.group(2).strip()
                i += 1
                continue

            # Бизнес-инсайт
            ins_match = re.match(r"^Что это значит для бизнеса:\s*\[?(.+?)\]?$", line)
            if ins_match:
                current_item["insight"] = ins_match.group(1).strip()
                i += 1
                continue

            # Описание (не пустая строка, не служебная)
            if line and not line.startswith("---") and not line.startswith("📊") and not line.startswith("Подготовлено"):
                if current_item["description"]:
                    current_item["description"] += " " + line
                else:
                    current_item["description"] = line

        i += 1

    if current_item:
        news_items.append(current_item)

    # Извлекаем тренды из текста (если не переданы)
    trend_lines_from_text = []
    in_trends = False
    for line in lines:
        if "📊 Тренды дня:" in line:
            in_trends = True
            continue
        if in_trends and line.strip().startswith("—"):
            trend_lines_from_text.append(line.strip())
        elif in_trends and line.strip() and not line.strip().startswith("—"):
            in_trends = False

    # Категориям — цвета
    category_colors = {
        "Модели": "#6366f1",
        "Продукты": "#0ea5e9",
        "Исследования": "#10b981",
        "Регулирование": "#f59e0b",
        "Влияние на бизнес": "#ec4899",
    }

    def get_cat_color(cat):
        for k, v in category_colors.items():
            if k.lower() in cat.lower():
                return v
        return "#64748b"

    # Генерируем карточки новостей
    news_html = ""
    for item in news_items:
        cat_color = get_cat_color(item.get("category", ""))
        source_html = ""
        if item["source_url"]:
            source_html = f'<a href="{item["source_url"]}" class="source-link" target="_blank">🔗 {item["source_name"]}</a>'
        elif item["source_name"]:
            source_html = f'<span class="source-name">{item["source_name"]}</span>'

        category_badge = ""
        if item["category"]:
            category_badge = f'<span class="badge" style="background:{cat_color}20;color:{cat_color};border:1px solid {cat_color}40">{item["category"]}</span>'

        audience_badge = ""
        if item["audience"]:
            audience_badge = f'<span class="badge badge-audience">👤 {item["audience"]}</span>'

        insight_html = ""
        if item["insight"]:
            insight_html = f'''
            <div class="insight-block">
                <span class="insight-icon">💡</span>
                <div class="insight-text"><strong>Для бизнеса:</strong> {item["insight"]}</div>
            </div>'''

        news_html += f'''
        <article class="news-card">
            <div class="news-number">{item["num"]}</div>
            <div class="news-content">
                <h2 class="news-title">{item["title"]}</h2>
                <p class="news-description">{item["description"]}</p>
                <div class="news-meta">
                    {source_html}
                    <div class="badges">
                        {category_badge}
                        {audience_badge}
                    </div>
                </div>
                {insight_html}
            </div>
        </article>'''

    # Блок трендов
    trends_html = ""
    if trend_lines_from_text:
        trends_items = "".join(f'<li>{t}</li>' for t in trend_lines_from_text)
        trends_html = f'''
    <section class="trends-section">
        <h3 class="trends-title">📊 Тренды дня</h3>
        <ul class="trends-list">
            {trends_items}
        </ul>
    </section>'''

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Дайджест | {today}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
            padding: 0;
        }}

        .page-wrapper {{
            max-width: 800px;
            margin: 0 auto;
            padding: 24px 16px 48px;
        }}

        /* ── Шапка ── */
        .header {{
            text-align: center;
            padding: 40px 24px 32px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border-radius: 20px;
            margin-bottom: 32px;
            border: none;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.08) 0%, transparent 60%);
            pointer-events: none;
        }}
        .header-emoji {{
            font-size: 48px;
            display: block;
            margin-bottom: 12px;
        }}
        .header h1 {{
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .header-date {{
            font-size: 14px;
            color: rgba(255,255,255,0.85);
            font-weight: 500;
        }}
        .header-subtitle {{
            font-size: 13px;
            color: rgba(255,255,255,0.65);
            margin-top: 6px;
        }}

        /* ── Карточки новостей ── */
        .news-card {{
            background: #ffffff;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            border: 1px solid #e2e8f0;
            display: flex;
            gap: 16px;
            transition: border-color 0.2s, box-shadow 0.2s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }}
        .news-card:hover {{
            border-color: #6366f1;
            box-shadow: 0 4px 12px rgba(99,102,241,0.1);
        }}

        .news-number {{
            flex-shrink: 0;
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 15px;
            color: white;
        }}

        .news-content {{
            flex: 1;
            min-width: 0;
        }}

        .news-title {{
            font-size: 16px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 10px;
            line-height: 1.4;
        }}

        .news-description {{
            font-size: 14px;
            color: #475569;
            margin-bottom: 14px;
            line-height: 1.65;
        }}

        .news-meta {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .source-link {{
            font-size: 13px;
            color: #6366f1;
            text-decoration: none;
            font-weight: 500;
        }}
        .source-link:hover {{ text-decoration: underline; }}
        .source-name {{
            font-size: 13px;
            color: #64748b;
        }}


        .badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .badge {{
            font-size: 11px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 20px;
            letter-spacing: 0.3px;
        }}
        .badge-audience {{
            background: #eff6ff;
            color: #3b82f6;
            border: 1px solid #bfdbfe;
        }}

        /* ── Бизнес-инсайт ── */
        .insight-block {{
            display: flex;
            gap: 10px;
            background: #f5f3ff;
            border-radius: 10px;
            padding: 12px 14px;
            border-left: 3px solid #6366f1;
            margin-top: 4px;
        }}
        .insight-icon {{
            font-size: 16px;
            flex-shrink: 0;
            margin-top: 1px;
        }}
        .insight-text {{
            font-size: 13px;
            color: #4c1d95;
            line-height: 1.55;
        }}
        .insight-text strong {{
            color: #6d28d9;
        }}

        /* ── Тренды ── */
        .trends-section {{
            background: linear-gradient(135deg, #f0f9ff, #eff6ff);
            border-radius: 16px;
            padding: 24px;
            margin: 24px 0;
            border: 1px solid #bfdbfe;
        }}
        .trends-title {{
            font-size: 16px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 14px;
        }}
        .trends-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .trends-list li {{
            font-size: 14px;
            color: #1e3a8a;
            padding-left: 4px;
        }}

        /* ── Подвал ── */
        .footer {{
            text-align: center;
            padding: 24px;
            border-top: 1px solid #e2e8f0;
            margin-top: 32px;
        }}
        .footer-text {{
            font-size: 12px;
            color: #64748b;
            line-height: 1.8;
        }}
        .footer-text a {{
            color: #6366f1;
            text-decoration: none;
        }}
        .footer-text a:hover {{ text-decoration: underline; }}

        /* ── Адаптив ── */
        @media (max-width: 480px) {{
            .news-card {{ flex-direction: column; gap: 12px; }}
            .news-number {{ width: 30px; height: 30px; font-size: 13px; }}
            .header h1 {{ font-size: 18px; }}
        }}
    </style>
</head>
<body>
    <div class="page-wrapper">

        <header class="header">
            <span class="header-emoji">🤖</span>
            <h1>УТРЕННЯЯ СВОДКА — МИР ИИ</h1>
            <div class="header-date">{today_full}</div>
            <div class="header-subtitle">{len(news_items)} ключевых новостей · Только проверенные факты</div>
        </header>

        <main>
            {news_html}
        </main>

        {trends_html}

        <footer class="footer">
            <p class="footer-text">
                Подготовлено ai-агентом · Только проверенные факты
                {f'<br>Источник: <a href="{DIGEST_FOOTER_URL}" target="_blank">{DIGEST_FOOTER_LABEL}</a>' if DIGEST_FOOTER_URL else ''}
            </p>
        </footer>

    </div>
</body>
</html>"""

    return html


def send_html_digest_to_chat(chat_id: int, html_content: str, today: str) -> bool:
    """Отправить HTML-файл дайджеста одному получателю через sendDocument."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"

    # Сохраняем HTML во временный файл
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", prefix=f"ai_digest_{today}_",
        delete=False, encoding="utf-8"
    ) as f:
        f.write(html_content)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as f:
            caption = f"🤖 AI-дайджест {today} — удобная HTML-версия для чтения"
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (f"ai_digest_{today}.html", f, "text/html")},
                timeout=30,
            )
        result = resp.json()
        if not result.get("ok"):
            err = result.get("description", "")
            print(f"[WARN] Ошибка отправки HTML в {chat_id}: {err}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка доставки HTML: {type(e).__name__}")
        return False
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─── Подписчики ─────────────────────────────────────────────────────────────


def get_active_subscribers() -> list:
    """Получить список активных chat_id из файла подписчиков."""
    if not SUBSCRIBERS_FILE.exists():
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            int(key)
            for key, info in data.items()
            if info.get("active")
        ]
    except (json.JSONDecodeError, IOError, ValueError) as e:
        print(f"[WARN] Ошибка чтения subscribers.json: {e}")
        return []


# ─── Telegram ───────────────────────────────────────────────────────────────


def _split_into_chunks(text: str, max_len: int = 4000) -> list:
    """Разбить длинный текст на части для Telegram."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > max_len:
            chunks.append(chunk)
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk:
        chunks.append(chunk)
    return chunks


def send_to_chat(chat_id: int, text: str) -> bool:
    """Отправить текстовое сообщение одному получателю (с разбивкой на части)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success = True
    for chunk in _split_into_chunks(text):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            result = resp.json()
            if not result.get("ok"):
                err = result.get("description", "")
                print(f"[WARN] Telegram error для {chat_id}: {err}")
                # Бот заблокирован пользователем — не считаем критической ошибкой
                if "bot was blocked" in err or "chat not found" in err:
                    return False
                success = False
            time.sleep(0.05)  # Соблюдаем лимит Telegram: 30 msg/sec
        except Exception as e:
            print(f"[ERROR] Ошибка доставки: {type(e).__name__}")
            success = False
    return success


def send_telegram_message(text: str, html_content: str = None) -> bool:
    """
    Разослать HTML-дайджест всем активным подписчикам.
    Отправляет ТОЛЬКО HTML-файл (текстовая сводка не отправляется).
    Если подписчиков нет — использовать только явно заданный резервный получатель.
    """
    today = datetime.now(SKILL_TZ).strftime("%d.%m.%Y")
    subscribers = get_active_subscribers()

    if not html_content:
        print("[WARN] HTML-контент не передан, отправка невозможна.")
        return False

    if subscribers:
        print(f"[INFO] Рассылка {len(subscribers)} подписчикам...")
        ok_count = 0
        fail_count = 0
        for chat_id in subscribers:
            html_ok = send_html_digest_to_chat(chat_id, html_content, today)
            if html_ok:
                ok_count += 1
            else:
                fail_count += 1
            time.sleep(0.1)
        print(f"[OK] Доставлено: {ok_count}, ошибок: {fail_count}")
        return ok_count > 0
    if not TELEGRAM_FALLBACK_CHAT_ID:
        print("[WARN] Нет активных подписчиков и не задан TELEGRAM_FALLBACK_CHAT_ID. Отправка остановлена.")
        return False
    print("[INFO] Подписчиков нет. Отправка HTML резервному получателю из окружения...")
    return send_html_digest_to_chat(int(TELEGRAM_FALLBACK_CHAT_ID), html_content, today)


# ─── История запусков ────────────────────────────────────────────────────────


def append_run_history(record: dict) -> None:
    """
    Добавить запись о запуске в JSONL-файл data/run_history.jsonl.
    Каждая строка — отдельный JSON-объект (формат JSONL).

    Поля записи:
      - ts: время запуска (ISO 8601, SKILL_TIMEZONE, default UTC)
      - version: версия агента
      - status: "ok" | "warn" | "error"
      - rss_collected: сколько записей собрано из RSS
      - after_dedup: после дедупликации
      - after_filter: после пост-фильтра
      - news_in_digest: новостей в сводке
      - subscribers_ok: доставлено
      - subscribers_fail: ошибок доставки
      - trends: список трендов дня
      - note: произвольный комментарий
    """
    RUN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(RUN_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[INFO] Запись в историю запусков добавлена: {RUN_HISTORY_FILE}")
    except Exception as e:
        print(f"[WARN] Не удалось записать в run_history.jsonl: {e}")


# ─── Основной процесс ──────────────────────────────────────────────


def main():
    run_ts = datetime.now(SKILL_TZ).isoformat()
    run_record: dict = {
        "ts": run_ts,
        "version": AGENT_VERSION,
        "status": "error",
        "rss_collected": 0,
        "after_dedup": 0,
        "after_filter": 0,
        "news_in_digest": 0,
        "subscribers_ok": 0,
        "subscribers_fail": 0,
        "trends": [],
        "note": "",
    }
    print(f"[{datetime.now(SKILL_TZ).strftime('%Y-%m-%d %H:%M:%S')} {timezone_label(SKILL_TZ)}] Запуск сбора AI-новостей {AGENT_VERSION}...")

    # 0. Убедиться, что bot_subscribe.py запущен. В dry-run не создавать фоновый процесс.
    if DRY_RUN:
        print("[INFO] DRY_RUN: автозапуск бота и Telegram-доставка отключены.")
    else:
        ensure_bot_running()

    # 1. Загрузка истории
    history = load_history()
    print(f"[INFO] В истории {len(history.get('sent_hashes', []))} хэшей, "
          f"{len(history.get('sent_titles', []))} заголовков")

    prev_titles = history.get("previous_digest_titles", [])
    if prev_titles:
        print(f"[INFO] Предыдущая сводка содержала {len(prev_titles)} тем")

    # 2. Сбор RSS
    print("[INFO] Сбор новостей из RSS-лент...")
    all_entries = fetch_rss_entries()
    print(f"[INFO] Собрано {len(all_entries)} записей из RSS")

    # 3. Многоуровневая дедупликация
    new_entries = full_dedup_pipeline(all_entries, history)
    run_record["after_dedup"] = len(new_entries)

    if len(new_entries) < MIN_NEWS:
        run_record["status"] = "warn"
        run_record["note"] = "Слишком мало новых новостей после дедупликации"
        append_run_history(run_record)
        print("[WARN] Слишком мало новых новостей после дедупликации. Сводка не будет отправлена.")
        return

    # 4. Пост-фильтр военно-политических тем (keyword + LLM)
    new_entries = apply_post_filter(new_entries)
    run_record["after_filter"] = len(new_entries)

    if len(new_entries) < MIN_NEWS:
        run_record["status"] = "warn"
        run_record["note"] = "Слишком мало новостей после пост-фильтра"
        append_run_history(run_record)
        print("[WARN] Слишком мало новостей после пост-фильтра. Сводка не будет отправлена.")
        return

    # 5. Enrichment Layer: scoring + LLM enrichment + trends
    top_entries, trends = run_enrichment_pipeline(new_entries)

    # 6. Обработка через LLM (отбор, фейк-чек, перевод, форматирование)
    print("[INFO] Обработка через LLM (отбор, фейк-чек, перевод, проверка повторов)...")
    digest = process_with_llm(top_entries, history, trends=trends)

    if not digest:
        run_record["status"] = "error"
        run_record["note"] = "Ошибка LLM: не удалось сформировать сводку"
        append_run_history(run_record)
        print("[ERROR] Не удалось сформировать сводку.")
        return

    print("[INFO] Сводка сформирована:")
    print("-" * 60)
    print(digest)
    print("-" * 60)

    # 7. Генерация HTML-версии
    print("[INFO] Генерация HTML-дайджеста...")
    html_content = generate_html_digest(digest, trends=trends)
    print(f"[INFO] HTML-дайджест сгенерирован ({len(html_content)} символов)")

    qa_issues = validate_generated_digest(digest, html_content)
    if qa_issues:
        run_record["status"] = "blocked"
        run_record["note"] = "QA: " + "; ".join(qa_issues)
        append_run_history(run_record)
        print(f"[BLOCKED] Дайджест не прошёл QA: {'; '.join(qa_issues)}")
        return

    # Считаем новости в сводке
    digest_titles = extract_digest_titles(digest)
    run_record["news_in_digest"] = len(digest_titles)
    run_record["trends"] = [t.get("trend", "") for t in (trends or [])]

    if DRY_RUN:
        run_record["status"] = "dry_run"
        run_record["note"] = "Сводка сформирована; Telegram-доставка и обновление истории отключены"
        append_run_history(run_record)
        print("[OK] DRY_RUN: сводка сформирована, внешняя отправка не выполнялась.")
        return

    # 8. Отправка в Telegram (HTML-файл)
    print("[INFO] Отправка в Telegram (HTML-файл)...")
    success = send_telegram_message(digest, html_content=html_content)

    if success:
        # Считаем статистику доставки
        subscribers = get_active_subscribers()
        run_record["subscribers_ok"] = len(subscribers)  # упрощённо: все активные
        run_record["status"] = "ok"

        # 9. Обновление истории (расширенная)
        used = extract_used_entries(digest, top_entries)
        entries_to_save = used if used else top_entries[:MAX_NEWS]

        # Сохраняем хэши
        hashes_to_add = [e["hash"] for e in entries_to_save]
        history.setdefault("sent_hashes", []).extend(hashes_to_add)

        # Сохраняем нормализованные заголовки (для fuzzy/Jaccard)
        titles_to_add = [normalize_title(e["title"]) for e in entries_to_save]
        history.setdefault("sent_titles", []).extend(titles_to_add)

        # Сохраняем полные записи
        entries_data = [
            {"title": e["title"], "link": e["link"], "hash": e["hash"],
             "source": e["source"], "date": e.get("pub_date")}
            for e in entries_to_save
        ]
        history.setdefault("sent_entries", []).extend(entries_data)

        # Сохраняем заголовки сводки для LLM-контекста следующего запуска
        digest_titles = extract_digest_titles(digest)
        history["previous_digest_titles"] = digest_titles
        print(f"[INFO] Извлечено {len(digest_titles)} заголовков из сводки для LLM-контекста")

        # Также добавляем ВСЕ собранные записи в хэш-историю (чтобы не предлагать повторно)
        all_hashes = [e["hash"] for e in all_entries]
        all_titles = [normalize_title(e["title"]) for e in all_entries]
        history["sent_hashes"] = list(set(history["sent_hashes"]) | set(all_hashes))
        existing_titles = set(history.get("sent_titles", []))
        for t in all_titles:
            if t not in existing_titles:
                history["sent_titles"].append(t)
                existing_titles.add(t)

        save_history(history)
        print(f"[OK] Готово! Хэшей в истории: {len(history['sent_hashes'])}, "
              f"заголовков: {len(history['sent_titles'])}")

        # 10. Запись в историю запусков
        append_run_history(run_record)
    else:
        run_record["status"] = "error"
        run_record["note"] = "Ошибка отправки в Telegram"
        append_run_history(run_record)
        print("[ERROR] Отправка не удалась.")


if __name__ == "__main__":
    main()
