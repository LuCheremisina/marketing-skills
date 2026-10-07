---
name: Publication Skill
description: Сборка финального HTML с Style Lock, валидацией по template_manifest и расчётом GEO Score (цель ≥ 12).
---

# Publication Skill

## Входные данные

*   `article_with_cta.md`: Текст статьи со всеми дополнениями (FAQ, CTA, E-E-A-T, ссылки, GEO-блоки).
*   `seo_metadata.md`: SEO-метаданные в формате Markdown (H1, Title, Description, slug, теги).
*   Schema.org JSON-LD из `schema_skill/` — передаётся как строка для встраивания в HTML.
*   `knowledge_graph.json`: Entity Graph (опционально).

> **Важно:** `cover_image.png` **не вставляется** в HTML — передаётся пользователю отдельным файлом.
> **Важно:** `schema_markup.html` как отдельный файл не создаётся — Schema.org встраивается внутрь `final_article.html`.

## Выходные данные

*   `final_article.html`: Готовый HTML для публикации (Schema.org встроена, H1 отсутствует в теле).
*   `geo_score_report.md`: Отчёт с GEO Score.

## Style Lock

**Источник CSS — `references/style_reference.html`:**
Перед сборкой HTML прочитать `references/style_reference.html`. Вставить содержимое `<style>` блока в начало `final_article.html`.

- **НЕ** открывать браузер — стиль уже зафиксирован в файле.
- **НЕ** добавлять inline-стили к элементам.
- **НЕ** создавать новые CSS-классы.
- Менять разрешено только текстовое содержание блоков.
- Обновлять `style_reference.html` только вручную при изменении дизайна.

**Ключевые нормативы:**
- `font-size: 17px`
- `font-family: Inter, "Segoe UI", Arial, sans-serif`
- `line-height: 1.75`
- Акцентный цвет: `#cf391b` (терракотовый)
- Фон: белый

## Встраивание видео

При вставке видео (VK Video, YouTube, или любой iframe-embed) соблюдать следующие правила высоты:

- **Высота iframe: 470px** — фиксированная для десктопной версии.
- Ширина: `100%` (адаптивная).
- Пример корректного кода:
  ```html
  <iframe src="..." width="100%" height="470" frameborder="0" allowfullscreen></iframe>
  ```
- Допускается добавление `style="max-width:100%;"` для корректного отображения на мобильных устройствах.
- **НЕ** использовать высоту меньше 470px — видео будет обрезано.

## Логика сборки HTML

1.  Прочитать `references/style_reference.html` и извлечь CSS.
2.  Создать структуру HTML по шаблону `templates/article_template.html`.
3.  Заполнить блоки контентом из `article_with_cta.md`:
    *   Порядок блоков: подкаст (если есть) → оглавление → Direct Answer → основной контент → видео (если есть) → CTA → AI Summary → FAQ → автор → "Читать также".
    *   При встраивании видео использовать высоту 470px (см. раздел «Встраивание видео» выше).
4.  Встроить Schema.org JSON-LD в `<head>` или конец `<body>`.
5.  Встроить H1 из `seo_metadata.md` в мета-тег (не в тело статьи).
6.  Пройти чек-лист `references/style_qa_checklist.md`.

## GEO Score (цель ≥ 12 из 15)

| Критерий | Балл |
|---|---|
| Direct Answer в начале | +1 |
| Definition blocks | +1 за каждый, макс. 2 |
| Knowledge boxes | +1 за каждый, макс. 2 |
| AI Summary / Key Takeaways | +1 |
| FAQ (≥ 5 вопросов) | +1 |
| Schema.org Article | +1 |
| Schema.org FAQPage | +1 |
| Schema.org BreadcrumbList | +1 |
| Внутренние ссылки (≥ 5) | +1 |
| Entity keywords (≥ 3) | +1 |
| Таблицы (≥ 1) | +1 |
| Структурированные списки (≥ 2) | +1 |

Сохранить итоговый счёт и список выполненных критериев в `geo_score_report.md`.
