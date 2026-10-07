---
name: Schema
description: Генерация Schema.org (JSON-LD) типов Article, FAQPage, BreadcrumbList.
---

# Schema

## Входные данные

- `seo_metadata.md` — H1, Title, Description, slug
- FAQ вопросы и ответы из `article_with_cta.md`
- `inputs/config.txt` — AUTHOR_NAME, SITE_URL, BLOG_PREFIX

## Выходные данные

- JSON-LD, встроенный в `final_article.html` внутри `<script type="application/ld+json">`.
- Отдельный файл `schema_markup.html` пользователю не передаётся.

## Логика работы

1. Прочитать AUTHOR_NAME, SITE_URL, BLOG_PREFIX из `inputs/config.txt`.
2. Сгенерировать JSON-LD для:
   - `Article` — автор, дата, заголовок, описание (AUTHOR_NAME из config).
   - `FAQPage` — вопросы и ответы из FAQ-блока.
   - `BreadcrumbList` — Главная → Блог → Текущая статья (SITE_URL + BLOG_PREFIX из config).
3. Обернуть в `<script type="application/ld+json"></script>`.
4. Провести валидацию Schema.org.
5. Передать разметку в Publication для встраивания в `final_article.html`.
