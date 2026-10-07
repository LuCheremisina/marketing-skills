# Инструкция по запуску

## 1. Конфиг проекта

Скопировать шаблон и заполнить:
```bash
cp "$SKILL_ROOT/inputs/config.txt.example" "$PROJECT_DIR/inputs/config.txt"
```

Заполнить поля:
```
SITE_URL=https://yoursite.com
AUTHOR_NAME=Имя Автора
AUTHOR_ROLE=Роль автора
AUTHOR_EXPERTISE=Краткая экспертиза (1-2 предложения)
CTA_URL=https://yoursite.com/contact
BLOG_PREFIX=/blog/
```

## 2. Входные файлы в `inputs/`

| Файл | Обязательность |
|---|---|
| `config.txt` | Обязательно |
| `brand_voice.txt` | Обязательно (tone of voice бренда) |
| `site_links.txt` | Обязательно (список URL сайта для внутренних ссылок) |
| `seo_requirements.txt` | Обязательно |
| `transcript.txt` ИЛИ `source_links.txt` | Одно из двух |

**`brand_voice.txt`** — описание tone of voice, ценностей бренда, авторского стиля. Может быть любым форматом: список тезисов, гайдлайн, примеры текстов.

**`site_links.txt`** — список URL сайта, по одному на строку. Используется для Internal Linking.

## 3. Style Reference

`references/style_reference.html` содержит CSS сайта. По умолчанию — шаблон.
Для реального сайта передайте CSS как внешний runtime style override.
Оригинал шаблона в установленном навыке не изменять.

## 4. Wordstat

Этап 2 (Semantic Analysis) использует sibling skill `che-wordstat-keyword-research`
и Yandex Wordstat MCP. Отдельный API-ключ в `.env` не нужен. Если MCP
недоступен — пометить частотности как «требует верификации», не выдумывать цифры.

## 5. Запуск

Открыть `references/01_orchestrator.md` и выполнить пайплайн по этапам 0–17.
