# Yandex Direct Analytics — an AI skill for advertising diagnosis

Read Yandex Direct and Metrika data, compare independent source tables and explain advertising performance without changing campaigns or budgets. Keep unmatched revenue visible rather than allocating it by spend.

[Install](#install) · [Download ZIP 2.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v1.0.2/direct-analytics-skill-2.0.0.zip) · [Read the workflow](../../skills/direct-analytics-skill/SKILL.md) · [Русский пример](#русский-пример)

## Who it helps

Marketers, consultants and business teams who need the result described above and can supply its inputs.

## What you need

Project configuration, period, timezone and attribution rules; authorised read access to Direct/Metrika or prepared SQLite/exports. Python is needed for the bundled analytics scripts.

## Install

In your project folder, with Node.js 22.20+ and Git:

```sh
npx skills add LuCheremisina/marketing-skills --skill direct-analytics-skill
```

Choose your AI client if prompted. For existing copies, use [verified installation](../INSTALL.md#verified-installation). For ChatGPT, use the [plugin route](../INSTALL.md#chatgpt), rather than the coding-agent CLI.

## Try it

Sample request — synthetic business context:

```text
Use direct-analytics-skill in read-only mode. For a synthetic seven-day example, Direct reports 10,000 currency units of spend for campaign A; Metrika reports 30,000 of revenue explicitly matched to A and 2,000 unmatched. Explain the source-separated numbers, label any cross-source ratio and retain unmatched revenue separately. Before reading real accounts, ask for the project, dates, timezone and mapping rules.
```

## Expected result

- Parallel Direct and Metrika tables.
- Match coverage and reconciliation limits.
- Labelled cross-source ratios for matched records only.
- A diagnosis and proposed checks, with campaign settings unchanged.

Illustrative output structure; this is documentation, not a measured customer result:

| Measure | Synthetic illustration |
|---|---:|
| Direct spend, campaign A | 10,000 |
| Matched Metrika revenue, campaign A | 30,000 |
| CrossSourceROAS (matched revenue / Direct spend) | 3.0 |
| Unmatched Metrika revenue, separate | 2,000 |

The table demonstrates arithmetic on supplied synthetic numbers, not a native account run or client outcome. CrossSourceROAS is not reported as a source-native attribution metric.

## Русский пример

```text
Используй direct-analytics-skill только на чтение. Учебный пример за семь дней: расход кампании A в Директе — 10 000; явно сопоставленная выручка A в Метрике — 30 000; ещё 2 000 не сопоставлены. Покажи источники раздельно, подпиши межисточниковое отношение и оставь 2 000 отдельной строкой. Для реальных аккаунтов сначала уточни проект, даты, часовой пояс и правила сопоставления.
```

## Version and platform status

Skill **2.0.0**, published in [library release v1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Quick installation was tested on an isolated project with skills CLI 1.7.0. This is separate from execution of the workflow. See [platform requirements](../PLATFORMS.md) and [actual verification](../VERIFICATION-2026-10-06.md).

Methodologist: **Любовь Черемисина (Lyubov Cheremisina)** — [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online). Methodology licence: [MIT](../../LICENSE).

[Choose another task](../START-HERE.md) · [All 41 skills](../CATALOG.md) · [Installation help](https://github.com/LuCheremisina/marketing-skills/discussions/categories/q-a)
