# Deep Research — an AI skill for market research

Compare markets, technologies or product options with a source-backed report. Use it for a decision that needs several perspectives and evidence, rather than a single factual lookup.

[Install](#install) · [Download ZIP 2.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v1.0.2/deep-research-2.0.0.zip) · [Read the workflow](../../skills/deep-research/SKILL.md) · [Русский пример](#русский-пример)

## Who it helps

Marketers, consultants and business teams who need the result described above and can supply its inputs.

## What you need

Your question, decision, geography, time window and available sources. Search/read tools are needed for new research; supplied documents can support a bounded document review.

## Install

In your project folder, with Node.js 22.20+ and Git:

```sh
npx skills add LuCheremisina/marketing-skills --skill deep-research
```

Choose your AI client if prompted. For existing copies, use [verified installation](../INSTALL.md#verified-installation). For ChatGPT, use the [plugin route](../INSTALL.md#chatgpt), rather than the coding-agent CLI.

## Try it

Sample request — synthetic business context:

```text
Use deep-research to compare two possible audiences for a synthetic business, Example Academy: small business owners and in-house marketing teams. The product is a beginner analytics course. The decision is which audience to research first. Ask for the region, period and source access before collecting evidence. Separate sourced facts, assumptions and recommendations.
```

## Expected result

- A research brief: decision, scope and unresolved inputs.
- A report comparing audience needs and available evidence.
- A source ledger with dates and uncertainty.
- A recommendation tied to the evidence, or a request for missing evidence.

Illustrative output structure; this is documentation, not a measured customer result:

| Report section | Illustrative content |
|---|---|
| Known from the brief | Beginner analytics course; two candidate audiences |
| Unknown | Region, demand, budget and conversion evidence |
| Next step | Set the research scope and gather public or supplied evidence |

No advertising or CRM account is needed for a public-source study. A source being unavailable is recorded; the workflow does not invent market size.

## Русский пример

```text
Используй deep-research: сравни две аудитории для учебного бизнеса «Пример Академии» — владельцы малого бизнеса и маркетологи компаний. Продукт — начальный курс аналитики. Решение — какую аудиторию исследовать первой. До исследования уточни регион, период и доступные источники. Раздели факты, допущения и рекомендации.
```

## Version and platform status

Skill **2.0.0**, published in [library release v1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Quick installation was tested on an isolated project with skills CLI 1.7.0. This is separate from execution of the workflow. See [platform requirements](../PLATFORMS.md) and [actual verification](../VERIFICATION-2026-10-06.md).

Methodologist: **Любовь Черемисина (Lyubov Cheremisina)** — [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online). Methodology licence: [MIT](../../LICENSE).

[Choose another task](../START-HERE.md) · [All 41 skills](../CATALOG.md) · [Installation help](https://github.com/LuCheremisina/marketing-skills/discussions/categories/q-a)
