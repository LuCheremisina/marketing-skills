---

## Содержание

- Входные данные (`inputs/`)
- Выходные данные
- Этап 0 — Init + Setup + Style Lock
- 0а — Setup Flow (автозапуск, если `inputs/config.txt` отсутствует)
- 0б — Brand Voice (автопоиск, если `inputs/brand_voice.txt` отсутствует)
- 0в — Проверка остальных файлов
- 0г — Style Lock
- Этап 1 — Research
- Этап 2 — Semantic Analysis
- Этап 3 — Structure
- Этап 4 — Article Writing
- Этап 5 — Fact Check
- Этап 6 — Entity SEO
- Этап 7 — Internal Linking
- Этап 8 — Link 404 Audit (финальный)
- Этап 9 — AI Citation
- Этап 10 — E-E-A-T
- Этап 11 — Knowledge Graph
- Этап 12 — GEO Optimization
- Этап 13 — FAQ + CTA
- Этап 14 — SEO Metadata
- Этап 15 — Schema.org
- Этап 16 — Cover
- Этап 17 — Publication

name: Orchestrator
description: Управляет полным 18-этапным пайплайном генерации SEO-статей.
---

# Orchestrator

## Входные данные (`inputs/`)

| Файл | Назначение |
|---|---|
| `config.txt` | SITE_URL, AUTHOR_NAME, AUTHOR_ROLE, AUTHOR_EXPERTISE, CTA_URL, BLOG_PREFIX |
| `brand_voice.txt` | Tone of voice и ценности бренда |
| `site_links.txt` | URL сайта для Internal Linking |
| `seo_requirements.txt` | SEO-требования |
| `transcript.txt` ИЛИ `source_links.txt` | Исходный материал |

## Выходные данные

- `final_article.html` — готовый HTML (Schema.org встроена, H1 в метаданных)
- `seo_metadata.md` — SEO-метаданные Markdown
- `cover_image.png` — обложка
- `geo_score_report.md` — GEO Score отчёт

---

## Этап 0 — Init + Setup + Style Lock

### 0а — Setup Flow (автозапуск, если `inputs/config.txt` отсутствует)

Проверить: существует ли `inputs/config.txt`?

**Если НЕТ** — запустить Setup Flow:

1. Получить перечисленные вводные из задания и доступных материалов. Недостающие сведения запросить одним компактным набором, только если они влияют на результат:
   - «URL вашего сайта? (напр. https://example.com)»
   - «Имя автора блога?»
   - «Роль / специализация автора (1 строка)?»
   - «Краткое описание экспертизы автора (1–2 предложения)?»
   - «URL страницы для CTA (кнопка в конце статьи)?»
   - «Префикс URL блога? (напр. /blog/ или /articles/)»

2. Создать `inputs/config.txt`:
   ```
   SITE_URL=<ответ>
   AUTHOR_NAME=<ответ>
   AUTHOR_ROLE=<ответ>
   AUTHOR_EXPERTISE=<ответ>
   CTA_URL=<ответ>
   BLOG_PREFIX=<ответ>
   ```

3. Подтвердить: «✅ Конфиг сохранён в `inputs/config.txt`. Продолжаю инициализацию.»

**Если ЕСТЬ** — прочитать значения и продолжить.

---

### 0б — Brand Voice (автопоиск, если `inputs/brand_voice.txt` отсутствует)

Проверить: существует ли `inputs/brand_voice.txt`?

**Если НЕТ** — выполнить автопоиск по проекту:

```bash
# Поиск файлов с признаками бренд-документов
find . -maxdepth 3 -type f \( -name "*.txt" -o -name "*.md" \) | \
  grep -iE "brand|voice|tone|positioning|позиционирован|бренд|голос|стиль|о себе|about|profile|context" \
  2>/dev/null | head -10
```

- Если найдены файлы → показать список пользователю: «Найдены возможные бренд-документы: [список]. Использовать один из них как brand_voice? Или вставьте текст вручную.»
- Если пользователь выбирает файл → скопировать в `inputs/brand_voice.txt`
- Если пользователь вставляет текст → сохранить в `inputs/brand_voice.txt`
- Если файлы не найдены → спросить: «Вставьте описание tone of voice и ценностей вашего бренда (можно в свободной форме):» → сохранить в `inputs/brand_voice.txt`

**Если ЕСТЬ** — прочитать и продолжить.

---

### 0в — Проверка остальных файлов

Проверить наличие:
- `inputs/site_links.txt` — если нет: «Загрузите файл со списком URL сайта (по одному на строку) или введите URL вручную через запятую»
- `inputs/seo_requirements.txt` — если нет: «Опишите SEO-требования или нажмите Enter для использования стандартных»; если Enter → создать базовый `seo_requirements.txt` с defaults:
  ```
  Focus keyword использовать естественно в релевантных заголовках и тексте; число повторов и H2 не задавать квотой. Структуру выбирать по интенту и содержанию.
  Meta description: 150–160 символов.
  Внутренние ссылки: 5–6 на статью.
  Длина статьи: 11 500–14 500 символов.
  ```
- `inputs/transcript.txt` ИЛИ `inputs/source_links.txt` — обязательно одно; если ни одного: «Предоставьте транскрипт (transcript.txt) или ссылки на источники (source_links.txt)»

### 0г — Style Lock

Прочитать `references/benchmarks.md` и `references/style_reference.html`.
CSS зафиксирован — браузер не открывать.

---

## Этап 1 — Research

Читать `references/02_research_context.md`.
Вход: `inputs/source_links.txt` ИЛИ `inputs/transcript.txt` + `inputs/brand_voice.txt`.

## Этап 2 — Semantic Analysis

Сформировать 10 ключей-кандидатов. Вызвать sibling skill `che-wordstat-keyword-research` через Wordstat MCP.
Читать `references/03_semantic.md`. Выход: focus keyword, secondary keywords, entity keywords, search queries.

## Этап 3 — Structure

Читать `references/04_structure.md`.
Вход: результаты Semantic + `inputs/seo_requirements.txt`. Выход: `article_structure.md`.

## Этап 4 — Article Writing

Читать `references/05_article_writer.md`.
Проверить длину: 10 000–16 000 символов (цель 11 500–14 500). Выход: `article_main_text.md`.

## Этап 5 — Fact Check

Читать `references/06_fact_check.md`.
Вход: `article_main_text.md`. Выход: `fact_checked_article.md`.

## Этап 6 — Entity SEO

Читать `references/07_entity_seo.md`.
Вход: `fact_checked_article.md`. Выход: `entity_seo_article.md`.

## Этап 7 — Internal Linking

Читать `references/08_internal_linking.md`.
Вход: `entity_seo_article.md` + `inputs/site_links.txt`. Цель: 5–6 ссылок (3 блог + 2 глоссарий/услуги).
Выход: `article_with_links.md`.

⛔ **СТОП-УСЛОВИЯ — выполнить до перехода к этапу 8:**
- Все URL взяты ТОЛЬКО из `inputs/site_links.txt` или живого поиска по сайту.
- Каждый slug проверен на отсутствие не-ASCII символов.
- Каждая ссылка проверена доступным средством: HTTP 200 плюс соответствие содержимого; 403/timeout обозначены «не проверено» и требуют другого разрешённого источника подтверждения.
- Ни одна ссылка с кодами 404/5xx/timeout не вошла в статью.

## Этап 8 — Link 404 Audit (финальный)

Независимая проверка всех внутренних ссылок из `article_with_links.md`:

```bash
SITE_URL="$(grep '^SITE_URL=' inputs/config.txt | cut -d= -f2)"
grep -oP "${SITE_URL//./\\.}[^\"\s)]+" article_with_links.md | sort -u | while read url; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -L --max-redirs 5 --connect-timeout 8 "$url")
  echo "$code | $url"
done
```

- 200 → проверить содержимое и релевантность; успешный код сам по себе не подтверждает факт.
- 403 → доступ запрещён, проверка не завершена; использовать разрешённый браузер/экспорт либо убрать зависимое утверждение.
- 404 → ❌ заменить из `site_links.txt`
- 5xx → ❌ проверить slug на кириллицу; заменить
- 0 / timeout → ❌ удалить ссылку

Переход к этапу 9: ссылки и зависящие от них утверждения проверены либо исключены; сохранять ограничения частичной проверки.

## Этап 9 — AI Citation

Читать `references/09_ai_citation.md`.
Вход: `article_with_links.md`. Выход: `ai_citation_article.md`.

## Этап 10 — E-E-A-T

Читать `references/10_eeat_builder.md`.
Вход: `ai_citation_article.md`. Выход: `eeat_article.md`.

## Этап 11 — Knowledge Graph

Читать `references/11_knowledge_graph.md`.
Вход: `eeat_article.md`. Выход: `kg_article.md` + `knowledge_graph.json`.

## Этап 12 — GEO Optimization

Читать `references/12_geo_optimizer.md`.
Вход: `kg_article.md`. Выход: `geo_optimized_article.md`.

## Этап 13 — FAQ + CTA

Читать `references/13_faq.md` → `article_with_faq.md`.
Читать `references/14_cta.md` → `article_with_cta.md`.

## Этап 14 — SEO Metadata

Читать `references/15_seo.md`.
Вход: `article_with_cta.md`. Выход: `seo_metadata.md` (Markdown, не JSON).

## Этап 15 — Schema.org

Читать `references/16_schema.md`.
JSON-LD встраивается в `final_article.html` — отдельный файл не создаётся.

## Этап 16 — Cover

Читать `references/17_visual.md`.
Выход: `cover_image.png`. В HTML не вставляется — отдельный файл.

## Этап 17 — Publication

Читать `references/18_publication.md`.
Style Lock: CSS из `references/style_reference.html`.
Выход: `final_article.html` + `geo_score_report.md`.

**Финал:** передать пользователю `final_article.html`, `seo_metadata.md`, `cover_image.png`, `geo_score_report.md`.
