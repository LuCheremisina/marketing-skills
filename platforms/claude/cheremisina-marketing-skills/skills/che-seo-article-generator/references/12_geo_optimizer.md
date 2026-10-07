---
name: GEO Optimizer Skill
description: Финальная оптимизация статьи под генеративные поисковые системы (Knowledge Box, AI Summary, Definition Blocks).
---

# GEO Optimizer Skill

## Входные данные

*   `kg_article.md`: Статья после Knowledge Graph Builder.

## Выходные данные

*   `geo_optimized_article.md`: Статья, оптимизированная под GEO-SEO.

## Логика работы

1.  Проанализировать статью и проверить наличие всех GEO-элементов.
2.  Добавить или усилить:
    *   Definition blocks (краткие определения ключевых понятий).
    *   Knowledge boxes (блоки ключевых идей).
    *   Структурированные списки.
    *   Таблицы (минимум одна).
    *   AI Summary (блок ключевых выводов).
3.  Убедиться, что элементы чётко выделены и легко парсятся AI-поисковиками.
4.  Не дублировать содержание блоков AI Citation Optimization.
