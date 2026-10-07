---
name: Research Context
description: Анализ исходных материалов для извлечения фактов, аргументов и контекста.
---

# Research Context

## Входные данные

- `inputs/source_links.txt` ИЛИ `inputs/transcript.txt`
- `inputs/brand_voice.txt` — tone of voice и ценности бренда

## Выходные данные

- `main_arguments`, `topic_angles`, `examples`, `additional_facts`

## Логика работы

1. Прочитать `inputs/brand_voice.txt` — понять tone of voice, ценности, авторский стиль.
2. Если предоставлен `source_links.txt` — перейти по каждой ссылке через browser tool.
3. Если предоставлен `transcript.txt` — извлечь ключевые тезисы.
4. Для каждого источника выявить: аргументы, углы раскрытия, примеры, факты.
5. При выборе углов ориентироваться на ценности бренда из п. 1.
6. Синтезировать контекст для передачи в следующие этапы.
