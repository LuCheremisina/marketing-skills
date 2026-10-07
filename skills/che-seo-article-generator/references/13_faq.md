---
name: FAQ Skill
description: Генерация блока часто задаваемых вопросов (FAQ) в HTML-формате с использованием ключевых слов.
---

# FAQ Skill

## Входные данные

*   `geo_optimized_article.md`: Статья после GEO-оптимизации.
*   `focus_keyword`: Основное ключевое слово.
*   `secondary_keywords`: Второстепенные ключевые слова.

## Выходные данные

*   `article_with_faq.md`: Статья с блоком FAQ.

## Логика работы

1.  Проанализировать статью для выявления ключевых тем и потенциальных вопросов.
2.  Сгенерировать 5–7 вопросов и ответов.
3.  Оформить блок FAQ:

```html
<div class="faq-block">
<h2 class="section-heading">Частые вопросы</h2>
<details>
<summary><strong>Вопрос пользователя?</strong></summary>
<p>Краткий и чёткий ответ эксперта.</p>
</details>
</div>
```

4.  В вопросах и ответах использовать `focus_keyword` и `secondary_keywords`.
5.  Интегрировать блок FAQ в статью перед CTA.
