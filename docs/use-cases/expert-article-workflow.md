# Expert Article Workflow — an AI skill for sourced content

Create or review an expert article from a brief, sources or transcript. Choose research, outline, draft, review or integration mode and keep claims traceable to evidence.

[Install](#install) · [Download ZIP 3.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v1.0.2/expert-article-workflow-3.0.0.zip) · [Read the workflow](../../skills/expert-article-workflow/SKILL.md) · [Русский пример](#русский-пример)

## Who it helps

Marketers, consultants and business teams who need the result described above and can supply its inputs.

## What you need

Topic, audience, intended decision, source material, author profile and brand guidance. Web access helps research; Python validators and site context are needed for an integration package.

## Install

In your project folder, with Node.js 22.20+ and Git:

```sh
npx skills add LuCheremisina/marketing-skills --skill expert-article-workflow
```

Choose your AI client if prompted. For existing copies, use [verified installation](../INSTALL.md#verified-installation). For ChatGPT, use the [plugin route](../INSTALL.md#chatgpt), rather than the coding-agent CLI.

## Try it

Sample request — synthetic business context:

```text
Use expert-article-workflow in outline mode for a synthetic article: “How a small business should evaluate an AI marketing report”. Audience: business owners. Intended decision: which claims require evidence before action. Ask for source material and author/brand guidance; create an outline and a list of claims that need sources. Do not invent credentials or customer results.
```

## Expected result

- An outline or draft appropriate to the requested mode.
- A claim/source ledger and editorial checks.
- Questions for missing evidence and author inputs.
- An integration handoff only when site inputs and validators are available.

Illustrative output structure; this is documentation, not a measured customer result:

| Outline block | Purpose |
|---|---|
| What the report claims | Extract the proposed business decision |
| Sources and attribution | Check period, source and matching rules |
| Missing evidence | Separate unknowns from findings |
| Before acting | Identify the smallest verification step |

Publication is a separate authorised action. The skill does not assign its methodologist as the author of your article.

## Русский пример

```text
Используй expert-article-workflow в режиме структуры для учебной статьи «Как малому бизнесу проверять AI-отчёт по маркетингу». Аудитория — владельцы бизнеса. Решение — какие утверждения требуют доказательств до действий. Уточни источники, автора и бренд; подготовь структуру и список утверждений, которым нужны подтверждения. Не выдумывай регалии и клиентские результаты.
```

## Version and platform status

Skill **3.0.0**, published in [library release v1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Quick installation was tested on an isolated project with skills CLI 1.7.0. This is separate from execution of the workflow. See [platform requirements](../PLATFORMS.md) and [actual verification](../VERIFICATION-2026-10-06.md).

Methodologist: **Любовь Черемисина (Lyubov Cheremisina)** — [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online). Methodology licence: [MIT](../../LICENSE).

[Choose another task](../START-HERE.md) · [All 41 skills](../CATALOG.md) · [Installation help](https://github.com/LuCheremisina/marketing-skills/discussions/categories/q-a)
