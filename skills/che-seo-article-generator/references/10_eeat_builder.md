---
name: E-E-A-T Builder
description: Усиление статьи по модели Google E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness).
---

# E-E-A-T Builder

## Входные данные

- `ai_citation_article.md`
- `inputs/config.txt` — AUTHOR_NAME, AUTHOR_ROLE, AUTHOR_EXPERTISE
- `inputs/brand_voice.txt` — дополнительный контекст об авторе

## Выходные данные

- `eeat_article.md`

## Логика работы

1. Прочитать AUTHOR_NAME, AUTHOR_ROLE, AUTHOR_EXPERTISE из `inputs/config.txt`.
2. Добавить **блок автора** (`author-block`) с именем, ролью и экспертизой из config.
3. Найти через `search` tool авторитетные исследования, подтверждающие ключевые тезисы.
4. Добавить ссылки на источники данных (статистика, отчёты, публикации).
5. Убедиться, что блок автора соответствует шаблону `author-block` из `template_manifest.json`.
