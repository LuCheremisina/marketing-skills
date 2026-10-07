---
name: Visual
description: Генерация обложки статьи в стиле editorial sketch.
---

# Visual

## Входные данные

- `article_title` — заголовок статьи
- `focus_keyword` — основное ключевое слово
- `inputs/config.txt` — для кастомизации бренда (опционально)

## Выходные данные

- `cover_image.png` — обложка (16:9)

## Логика работы

1. Прочитать промпт из `references/cover_prompt.md`.
2. Дополнить промпт описанием тематики статьи на основе заголовка и ключевого слова.
3. Вызвать `generate` tool с полным промптом и negative prompt из `cover_prompt.md`.
4. Сохранить как `cover_image.png` (16:9).
