# SEO/GEO Auditor — an AI skill for website audits

Audit a whole website or a set of URLs for technical SEO, on-page structure and AI-search visibility. Prioritise fixes using observable page evidence. For one page or a content brief, see the separate che-seo-geo-auditor-pro workflow.

[Install](#install) · [Download ZIP 2.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v1.0.2/seo-geo-auditor-2.0.0.zip) · [Read the workflow](../../skills/che-seo-geo-auditor/SKILL.md) · [Русский пример](#русский-пример)

## Who it helps

Marketers, consultants and business teams who need the result described above and can supply its inputs.

## What you need

An authorised public URL or crawl export, website type, business objective and crawl scope. Full crawling needs Python, the dependencies declared in the skill and network access.

## Install

In your project folder, with Node.js 22.20+ and Git:

```sh
npx skills add LuCheremisina/marketing-skills --skill che-seo-geo-auditor
```

Choose your AI client if prompted. For existing copies, use [verified installation](../INSTALL.md#verified-installation). For ChatGPT, use the [plugin route](../INSTALL.md#chatgpt), rather than the coding-agent CLI.

## Try it

Sample request — synthetic business context:

```text
Use che-seo-geo-auditor for a synthetic course website. First ask me for its authorised URL, business objective and crawl scope. Then inspect crawlability, titles, headings, internal links and structured data using the available tools. For each finding, give the affected URL, observation, priority and proposed fix. Mark crawl or field-data checks that could not run.
```

## Expected result

- Crawl scope and inspected URLs.
- Findings linked to observed page elements.
- Prioritised fixes and validation steps.
- Separate limits for inaccessible pages, search data and field performance.

Illustrative output structure; this is documentation, not a measured customer result:

| Finding field | Illustrative content |
|---|---|
| URL | An authorised page supplied at run time |
| Observation | Exact element or crawl result captured during the audit |
| Priority | Based on impact and affected scope |
| Validation | Repeat the relevant crawl or page check after a fix |

A public crawl does not require a search-console account. Search performance and field metrics require their own data access; an audit does not establish rankings or AI citations.

## Русский пример

```text
Используй che-seo-geo-auditor для учебного сайта курсов. Сначала запроси разрешённый URL, цель бизнеса и границы обхода. Проверь доступность для краулера, title, заголовки, внутренние ссылки и структурированные данные. Для каждой проблемы укажи URL, наблюдение, приоритет и исправление. Недоступные проверки обозначь отдельно.
```

## Version and platform status

Skill **2.0.0**, published in [library release v1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Quick installation was tested on an isolated project with skills CLI 1.7.0. This is separate from execution of the workflow. See [platform requirements](../PLATFORMS.md) and [actual verification](../VERIFICATION-2026-10-06.md).

Methodologist: **Любовь Черемисина (Lyubov Cheremisina)** — [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online). Methodology licence: [MIT](../../LICENSE).

[Choose another task](../START-HERE.md) · [All 41 skills](../CATALOG.md) · [Installation help](https://github.com/LuCheremisina/marketing-skills/discussions/categories/q-a)
