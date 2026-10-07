---
name: CTA
description: Генерация блока призыва к действию с UTM-метками.
---

# CTA

## Входные данные

- `article_with_faq.md`
- `inputs/config.txt` — CTA_URL

## Выходные данные

- `article_with_cta.md`

## Логика работы

1. Прочитать CTA_URL из `inputs/config.txt`.
2. Определить основную тему и цель статьи.
3. Сгенерировать релевантный призыв к действию.
4. Оформить блок по шаблону:

```html
<div class="cta-block">
  <p>{{cta_text}}</p>
  <a class="cta-button" href="{{CTA_URL}}?utm_source=blog&utm_medium=article&utm_campaign={{slug}}">{{cta_button_text}}</a>
</div>
```

5. Интегрировать CTA после FAQ, перед источниками.
