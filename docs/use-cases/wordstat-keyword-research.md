# Wordstat Keyword Research — an AI skill for Yandex search demand

Turn seed queries into a Yandex Wordstat keyword map: related phrases, intent, region and frequency. Useful for content planning and paid-search research in a selected market.

[Install](#install) · [Download ZIP 2.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.1/che-wordstat-keyword-research-3.0.0.zip) · [Read the workflow](../../skills/che-wordstat-keyword-research/SKILL.md) · [Русский пример](#русский-пример)

## Who it helps

Marketers, consultants and business teams who need the result described above and can supply its inputs.

## What you need

Business niche, seed phrases, region, period and a working Wordstat connection or authorised export. Tools use the capabilities available in your client.

## Install

In your project folder, with Node.js 22.20+ and Git:

```sh
npx skills add LuCheremisina/marketing-skills --skill che-wordstat-keyword-research
```

Choose your AI client if prompted. For existing copies, use [verified installation](../INSTALL.md#verified-installation). For ChatGPT, use the [plugin route](../INSTALL.md#chatgpt), rather than the coding-agent CLI.

## Try it

Sample request — synthetic business context:

```text
Use che-wordstat-keyword-research for the synthetic niche “online Excel courses”. First ask for the target region and period. With authorised Wordstat data, collect relevant phrases, separate learning intent from purchase intent, exclude irrelevant queries and propose content clusters. State the data source and query operators. If Wordstat is unavailable, give a research plan without invented search volumes.
```

## Expected result

- Keyword table with source, region, date and query settings.
- Intent-based clusters and exclusions.
- Content or advertising research priorities.
- Missing-data notes when the connection is unavailable.

Illustrative output structure; this is documentation, not a measured customer result:

| Query | Intent | Frequency |
|---|---|---|
| online Excel course | Purchase / course selection | Retrieve from Wordstat |
| how to use pivot tables | Learning | Retrieve from Wordstat |

This is a Wordstat workflow, not a substitute for Google keyword metrics. Installing the skill does not grant Wordstat access; use your existing authorised connection or export.

## Русский пример

```text
Используй che-wordstat-keyword-research для учебной ниши «онлайн-курсы Excel». Сначала уточни регион и период. По разрешённым данным Wordstat собери запросы, отдели обучение от покупки, исключи нерелевантные фразы и предложи кластеры контента. Укажи источник и операторы запросов. Без Wordstat подготовь план и не выдумывай частотность.
```

## Version and platform status

Skill **2.0.0**, published in [library release v1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Quick installation was tested on an isolated project with skills CLI 1.7.0. This is separate from execution of the workflow. See [platform requirements](../PLATFORMS.md) and [actual verification](../VERIFICATION-2026-10-06.md).

Methodologist: **Любовь Черемисина (Lyubov Cheremisina)** — [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online). Methodology licence: [MIT](../../LICENSE).

[Choose another task](../START-HERE.md) · [All 41 skills](../CATALOG.md) · [Installation help](https://github.com/LuCheremisina/marketing-skills/discussions/categories/q-a)
