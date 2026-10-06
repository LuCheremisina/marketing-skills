# Integration contract: Tilda fragment

## Оглавление

1. [Граница результата](#граница-результата)
2. [Файлы](#файлы)
3. [HTML](#html)
4. [Metadata](#metadata)
5. [Schema](#schema)
6. [Cover](#cover)
7. [Publish gate](#publish-gate)
8. [Smoke test](#smoke-test)

## Граница результата

Канон v2 — **CMS fragment**, не полный HTML document. Fragment содержит один
семантический H1 и всё видимое тело статьи. `<head>`, canonical, Open Graph,
Twitter Cards и JSON-LD передаются отдельно через integration manifest.

H1 owner — fragment. При интеграции отключить или понизить визуальный title
Tilda, если он уже рендерится как H1. Итоговая страница обязана иметь ровно
один H1.

## Файлы

```text
article.html                 CMS fragment
metadata.json                SEO/OG/Twitter и production context
schema.json                  BlogPosting + optional FAQPage + BreadcrumbList
integration-manifest.json    статусы, порядок компонентов, asset URLs
claims.jsonl                 evidence ledger
run-manifest.json            версия, проверки и measurement plan
```

Использовать `assets/article-fragment.html`, `assets/article.css`,
`assets/component-manifest.json` и примеры JSON как шаблоны.

## HTML

Обязательные условия:

- корневой `.article-body`;
- один `<h1 class="article-title">`;
- lede и основное содержимое;
- видимый author block с автором материала;
- видимый sources block при external material claims;
- FAQ только при самостоятельных вопросах;
- один CTA или ни одного;
- нет cover image, `<html>`, `<head>` и meta tags;
- используются только классы из component manifest.

Канонический порядок:

```text
header → direct answer (optional) → content → sources (conditional)
→ FAQ (conditional) → author → CTA (conditional)
```

Удалять необязательный компонент целиком, а не оставлять пустой заголовок.

## Metadata

Для draft разрешены `null`. Для integrate обязательны:

```json
{
  "article_id": "stable-id",
  "title": "SEO title",
  "description": "SEO description",
  "h1": "Visible H1",
  "production_url": "https://example.com/...",
  "canonical_url": "https://example.com/...",
  "datePublished": "2026-07-30T10:00:00+07:00",
  "dateModified": "2026-07-30T10:00:00+07:00",
  "og_image_url": "https://.../unique-cover.webp",
  "twitter_card": "summary_large_image",
  "semantic_status": "available",
  "claims_complete": true
}
```

`og_image_url` не может быть общим placeholder. `canonical_url` должен быть
self-canonical для production page.

## Schema

Создавать `@graph` с:

- `BlogPosting`;
- `BreadcrumbList`;
- `FAQPage` только при видимом FAQ.

Для BlogPosting обязательны `headline`, `description`, `datePublished`,
`dateModified`, `mainEntityOfPage`, `author`, `image`, `publisher`,
`inLanguage` из предоставленного `site-profile.json`; author из проверенного `author-profile.json`. Без этих входов не подставлять синтетический профиль в HTML или Schema.

Headline должен совпадать с видимым H1 по смыслу и в текущем контракте —
дословно. Schema image должен совпадать с `og_image_url`. Questions в FAQPage
должны совпадать с видимыми вопросами и их порядком.

## Cover

В режиме integrate или при явном запросе вызвать установленный
`editorial-cover-prompts`, `news-cover-production` или другой реально установленный подходящий навык. Не дублировать его
визуальные правила в article Skill.

Контракт результата:

- уникальный PNG и WebP;
- проверенная кириллица и композиция;
- реальный URL после загрузки;
- один и тот же URL в OG и Schema.

Если cover Skill недоступен, подготовить только cover brief и отметить
`cover_status: unavailable`; не утверждать, что изображение создано.

## Publish gate

Перед внешним действием проверить:

- явное разрешение пользователя в текущем запросе;
- production URL и CMS/repository target;
- final dates и asset URLs;
- `validate_article.py --stage integrate` = PASS;
- отсутствие unresolved material claims;
- способ отката или сохранённая предыдущая версия.

## Smoke test

После публикации проверить по production URL:

- HTTP 200 и self-canonical;
- ровно один H1;
- уникальный `og:image`;
- `twitter:card=summary_large_image`;
- BlogPosting, Person reference и BreadcrumbList;
- FAQ/FAQPage parity;
- видимый author block;
- рабочие внутренние ссылки;
- отсутствие видимой поломки desktop/mobile.

Сообщать фактический результат каждой проверки. Не считать успешный build
доказательством успешной публикации.
