#!/usr/bin/env python3
"""
bot_subscribe.py — Telegram-бот для управления подписками на AI-дайджест.

The configured Telegram bot accepts commands from users and manages
the subscriber list used by collect_and_send.py. Set TELEGRAM_BOT_USERNAME
if you want the welcome text to mention the bot handle.

Запуск выполняется платформой после предоставления Telegram-доступа.

Команды бота:
    /start  — подписаться на ежедневный дайджест
    /stop   — отписаться от дайджеста
    /status — проверить статус подписки
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

import requests

from skill_timezone import resolve_skill_timezone, timezone_label

# ─── Конфигурация ───────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("[ERROR] Платформа не предоставила Telegram-доступ для доставки.")
    sys.exit(1)
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").lstrip("@")

# Файл хранения подписчиков
SKILL_DIR = Path(__file__).parent.parent
SUBSCRIBERS_FILE = Path(os.environ.get("DIGEST_DATA_DIR", str(Path.home() / ".local" / "share" / "daily-ai-news-digest"))) / "subscribers.json"

# Subscriber timestamps use SKILL_TIMEZONE (IANA name). Default UTC.
SKILL_TZ = resolve_skill_timezone()

# Базовый URL Telegram Bot API
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Хранилище подписчиков ──────────────────────────────────────────────────


def load_subscribers() -> dict:
    """Загрузить список подписчиков из JSON-файла."""
    SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_subscribers(subscribers: dict):
    """Сохранить список подписчиков в JSON-файл."""
    SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=2)


def add_subscriber(chat_id: int, user_info: dict) -> bool:
    """Добавить подписчика. Возвращает True если добавлен новый, False если уже был."""
    subscribers = load_subscribers()
    key = str(chat_id)
    if key in subscribers:
        return False
    subscribers[key] = {
        "chat_id": chat_id,
        "username": user_info.get("username", ""),
        "first_name": user_info.get("first_name", ""),
        "last_name": user_info.get("last_name", ""),
        "subscribed_at": datetime.now(SKILL_TZ).isoformat(),
        "active": True,
    }
    save_subscribers(subscribers)
    log.info("Новый подписчик добавлен; персональные данные в лог не выводятся")
    return True


def remove_subscriber(chat_id: int) -> bool:
    """Деактивировать подписчика. Возвращает True если был активен."""
    subscribers = load_subscribers()
    key = str(chat_id)
    if key not in subscribers or not subscribers[key].get("active"):
        return False
    subscribers[key]["active"] = False
    subscribers[key]["unsubscribed_at"] = datetime.now(SKILL_TZ).isoformat()
    save_subscribers(subscribers)
    log.info("Подписка отменена")
    return True


def is_subscribed(chat_id: int) -> bool:
    """Проверить, активна ли подписка."""
    subscribers = load_subscribers()
    entry = subscribers.get(str(chat_id))
    return bool(entry and entry.get("active"))


def get_active_subscribers() -> list:
    """Получить список активных chat_id для рассылки."""
    subscribers = load_subscribers()
    return [
        int(key)
        for key, data in subscribers.items()
        if data.get("active")
    ]


# ─── Telegram API ───────────────────────────────────────────────────────────


def send_message(chat_id: int, text: str, parse_mode: str = None) -> bool:
    """Отправить сообщение пользователю."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=15)
        result = resp.json()
        if not result.get("ok"):
            log.warning(f"Ошибка отправки в {chat_id}: {result.get('description')}")
            return False
        return True
    except Exception as e:
        log.error(f"Ошибка запроса к Telegram: {type(e).__name__}")
        return False


def get_updates(offset: int = 0, timeout: int = 30) -> list:
    """Получить обновления через long polling."""
    try:
        resp = requests.get(
            f"{API_URL}/getUpdates",
            params={"offset": offset, "timeout": timeout, "allowed_updates": ["message"]},
            timeout=timeout + 5,
        )
        result = resp.json()
        if result.get("ok"):
            return result.get("result", [])
    except requests.exceptions.Timeout:
        pass  # Нормальная ситуация при long polling
    except Exception as e:
        log.error(f"Ошибка getUpdates: {type(e).__name__}")
        time.sleep(5)
    return []


# ─── Обработчики команд ─────────────────────────────────────────────────────


def handle_start(chat_id: int, user: dict):
    """Обработать команду /start — подписать пользователя."""
    first_name = user.get("first_name", "")
    is_new = add_subscriber(chat_id, user)

    if is_new:
        text = (
            f"Привет, {first_name}! 👋\n\n"
            f"Вы успешно подписались на ежедневный AI-дайджест{(' от @' + BOT_USERNAME) if BOT_USERNAME else ''}.\n\n"
            f"Каждое утро в 9:00 ({timezone_label(SKILL_TZ)}) вы будете получать:\n"
            "— 10 ключевых новостей из мира AI\n"
            "— Бизнес-инсайты для каждой новости\n"
            "— Тренды дня\n\n"
            "Только проверенные факты. Никакого кликбейта.\n\n"
            "Чтобы отписаться — отправьте /stop"
        )
    else:
        text = (
            f"{first_name}, вы уже подписаны на дайджест! ✅\n\n"
            f"Следующая сводка придёт завтра в 9:00 ({timezone_label(SKILL_TZ)}).\n"
            "Чтобы отписаться — отправьте /stop"
        )

    send_message(chat_id, text)


def handle_stop(chat_id: int, user: dict):
    """Обработать команду /stop — отписать пользователя."""
    first_name = user.get("first_name", "")
    was_active = remove_subscriber(chat_id)

    if was_active:
        text = (
            f"{first_name}, вы отписались от AI-дайджеста. 👋\n\n"
            "Жаль расставаться! Если захотите вернуться — просто отправьте /start"
        )
    else:
        text = (
            "Вы не были подписаны на дайджест.\n"
            "Чтобы подписаться — отправьте /start"
        )

    send_message(chat_id, text)


def handle_status(chat_id: int, user: dict):
    """Обработать команду /status — показать статус подписки."""
    first_name = user.get("first_name", "")
    subscribers = load_subscribers()
    entry = subscribers.get(str(chat_id))

    if entry and entry.get("active"):
        subscribed_at = entry.get("subscribed_at", "")
        try:
            dt = datetime.fromisoformat(subscribed_at)
            date_str = dt.strftime("%d.%m.%Y")
        except Exception:
            date_str = subscribed_at[:10] if subscribed_at else "неизвестно"

        active_count = len(get_active_subscribers())
        text = (
            f"{first_name}, ваша подписка активна ✅\n\n"
            f"Подписаны с: {date_str}\n"
            f"Следующая сводка: завтра в 9:00 ({timezone_label(SKILL_TZ)})\n\n"
            f"Всего подписчиков: {active_count}\n\n"
            "Чтобы отписаться — /stop"
        )
    else:
        text = (
            f"{first_name}, вы не подписаны на дайджест.\n\n"
            "Чтобы подписаться — /start"
        )

    send_message(chat_id, text)


def handle_unknown(chat_id: int):
    """Ответить на неизвестную команду."""
    text = (
        "Доступные команды:\n\n"
        "/start — подписаться на ежедневный AI-дайджест\n"
        "/stop — отписаться\n"
        "/status — проверить статус подписки"
    )
    send_message(chat_id, text)


def process_update(update: dict):
    """Обработать одно обновление от Telegram."""
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    user = message.get("from", {})
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    log.info("Получено сообщение; содержимое и отправитель скрыты")

    if text.startswith("/start"):
        handle_start(chat_id, user)
    elif text.startswith("/stop"):
        handle_stop(chat_id, user)
    elif text.startswith("/status"):
        handle_status(chat_id, user)
    else:
        handle_unknown(chat_id)


# ─── Основной цикл ──────────────────────────────────────────────────────────


def main():
    log.info("Запуск Telegram-бота подписок%s...", f" @{BOT_USERNAME}" if BOT_USERNAME else "")
    log.info(f"Файл подписчиков: {SUBSCRIBERS_FILE}")

    # Проверяем соединение с Telegram
    try:
        resp = requests.get(f"{API_URL}/getMe", timeout=10)
        bot_info = resp.json()
        if bot_info.get("ok"):
            username = bot_info["result"].get("username")
            log.info(f"Бот авторизован: @{username}")
        else:
            log.error(f"Ошибка авторизации: {bot_info}")
            sys.exit(1)
    except Exception as e:
        log.error(f"Не удалось подключиться к Telegram: {type(e).__name__}")
        sys.exit(1)

    active_count = len(get_active_subscribers())
    log.info(f"Активных подписчиков: {active_count}")
    log.info("Бот запущен. Ожидание сообщений (Ctrl+C для остановки)...")

    offset = 0
    while True:
        try:
            updates = get_updates(offset=offset, timeout=30)
            for update in updates:
                process_update(update)
                offset = update["update_id"] + 1
        except KeyboardInterrupt:
            log.info("Бот остановлен.")
            break
        except Exception as e:
            log.error(f"Ошибка в основном цикле: {type(e).__name__}")
            time.sleep(5)


if __name__ == "__main__":
    main()
