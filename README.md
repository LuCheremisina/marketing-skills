# AI Marketing Skills — research, SEO/GEO, analytics & content

> **Published v2.0.1:** 34 authored CHE_ workflows + 14 licensed engineering skills. [Release](https://github.com/LuCheremisina/marketing-skills/releases/tag/v2.0.1) · [Migration](docs/MIGRATION-2.0.md) · [MCP Panel connections](docs/MCP-CONNECTIONS.md).

[Installation evidence](docs/INSTALLATION-2026-10-07.md): verified package installation and scoped execution; remaining runtime limits are explicit.
Research a market, audit a website, analyse Yandex campaigns, find search demand, or turn evidence into an expert article with reusable AI workflows.

**34 original marketing workflows + 14 optional engineering skills.** Open Agent Skills packages for Codex, Claude Code and Cursor; ChatGPT plugin packages are also available. Each workflow lists the inputs and connections it needs. [Platform status](docs/PLATFORMS.md).

[**Install your first skill**](#quick-install) · [**Start with 5 marketing skills**](docs/START-HERE.md) · [**Browse all 48**](docs/CATALOG.md) · [**Download the latest release**](https://github.com/LuCheremisina/marketing-skills/releases/latest) · [Русская версия](README.ru.md)

## Quick install

With **Node.js 22.20+ and Git**, run this inside your project:

```sh
npx skills add LuCheremisina/marketing-skills --skill che-deep-research
```

Select your AI client if prompted, then ask it to use `che-deep-research` for your question. [Try the example](docs/use-cases/deep-research.md#try-it). Prefer a ZIP? [Download Deep Research 2.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.1/che-deep-research-3.0.0.zip) and follow the [client installation guide](docs/INSTALL.md#zip-and-plugin-installation).

The CLI installs into the current project by default. For an existing installation, or a release pinned to checksums, use [verified installation](docs/INSTALL.md#verified-installation). Quick install was checked with `skills` CLI 1.7.0; installation does not connect accounts or establish runtime compatibility.

## Start here: 5 useful marketing skills

| Your task | Skill and example | What you can get | Needs |
|---|---|---|---|
| Research a market or compare options | [Deep Research](docs/use-cases/deep-research.md) | A sourced report with findings, uncertainty and decision options | A research question; web access or supplied sources |
| Audit search and AI-search visibility | [SEO/GEO Auditor](docs/use-cases/seo-geo-auditor.md) | A website audit with evidence and prioritised fixes | An authorised URL; Python and crawl/read tools |
| Find demand in Yandex search | [Wordstat Keyword Research](docs/use-cases/wordstat-keyword-research.md) | Query clusters with region, frequency and intent | Wordstat connection or an authorised export |
| Diagnose advertising performance | [Yandex Direct Analytics](docs/use-cases/direct-analytics-skill.md) | Source-separated advertising and attribution tables | Direct/Metrika read access or prepared exports |
| Create a sourced expert article | [Expert Article Workflow](docs/use-cases/expert-article-workflow.md) | A draft, claim ledger and editorial checks | A brief, sources and an author/brand profile |

Each page includes a sample request, expected output, install command and individual ZIP. [Full task catalogue →](docs/CATALOG.md)

![Marketing Skills — research, analytics, SEO/GEO and content](assets/social-preview.png)

## Get help and share what worked

[Installation questions](https://github.com/LuCheremisina/marketing-skills/discussions/categories/q-a) · [Request a skill](https://github.com/LuCheremisina/marketing-skills/discussions/categories/ideas) · [Share a result](https://github.com/LuCheremisina/marketing-skills/discussions/categories/show-and-tell)

Include your client, chosen skill and a synthetic example. Keep account credentials and client records private. If a workflow helped, **star the repository** to find it again; [watch releases](https://github.com/LuCheremisina/marketing-skills/releases) for published updates.

## What's in the library

The packages follow the [Agent Skills format](https://agentskills.io/specification). Marketing workflows are MIT licensed; engineering packages retain their original licences. Brand, business and author profiles are supplied at run time, so the public packages contain no client profiles or credentials.

Current published release: [**v1.0.2**](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Individual versions and sources are tracked in the [catalogue](catalog/skills.json). [Checksums, evaluations and the dated verification record](docs/VERIFICATION-2026-10-06.md) are available for review.

## Choose a workflow

| Business task | Start with | Reviewable result |
|---|---|---|
| Understand a market or customer decision | `che-product-market-intake`, `che-deep-research`, `che-research-loop` | Research scope, evidence, uncertainty and next-process decision |
| Assess campaign performance | `che-direct-analytics-skill`, `che-direct-analyst`, `che-audit-unisender-email` | Source-separated metrics, attribution limits and prioritized actions |
| Plan growth and monitor demand | `che-build-predictive-growth-dashboard`, `che-wordstat-trend-radar`, `che-seo-demand-analytics` | Scenarios, trend signals and their assumptions |
| Improve search and AI-search visibility | `che-seo-geo-auditor`, `che-seo-geo-auditor-pro`, `che-wordstat-keyword-research`, `che-topic-planner` | Contextual findings, intent and a practical content plan |
| Create sourced expert content | `che-expert-article-workflow`, `che-seo-article-generator`, `che-news-editorial-workflow` | Draft, evidence ledger and conditional integration handoff |
| Produce social and audio content | `che-content-carousel`, `che-telegram-content-creator`, `che-news-voiceover-script`, `che-short-video-production` | Storyboard or script; actual media only when the runtime is available |
| Prepare covers and apply brand guidance | `che-brand-profile-guide`, `che-editorial-cover-prompts`, `che-cover-production` | Brand-aligned concepts, prompts and validated image export |
| Monitor industry and AI news | `che-industry-news-digest`, `che-daily-ai-news-digest` | Sourced digest with time window, deduplication and delivery status |
| Accept a delivery or prevent a regression | `che-brief-acceptance`, `che-skill-regression-check` | Requirement evidence, unresolved gaps and regression verdict |

See the [complete catalogue](docs/CATALOG.md) for inputs, outputs and required connections. Cloudflare skills and `autopilot` are optional engineering support packages; original authorship and licenses are documented in [third-party sources](docs/third-party-sources.md).

## Use with your AI system

| System | Current evidence and limit |
|---|---|
| Codex | 34 authored + 14 vendor payloads match the release; 34 new names discovered without parse errors; three authored skills sampled natively |
| Claude Code | 34 authored + 14 vendor payloads match; native execution blocked by OAuth 401 |
| Cursor | 34 authored + 14 vendor folders match; GUI discovery and execution not verified |
| ChatGPT | Existing authored cloud plugin updated to 2.0.1; all 34 CHE_ skills listed. Vendor plugin updated to 2.0.1 with 14 skills listed; execution remains separately unverified |
| Claude / Cowork | Separate account import and execution not verified |
| Grok Bot | Transfer and execution not verified |

[Current dated evidence](docs/INSTALLATION-2026-10-07.md) distinguishes files, discovery, sampled execution and live integrations. The catalog does not claim full native execution from package presence. Earlier v1.0.2 evidence remains historical.

Use [quick or verified installation](docs/INSTALL.md) for the route that fits your environment. Never place credentials or client data inside an installed skill. Detailed platform guidance and official sources are in [PLATFORMS.md](docs/PLATFORMS.md).

## Evidence and quality

The library separates facts, hypotheses, recommendations and measured outcomes. Missing inputs or unavailable tools produce a clear limitation rather than fabricated research, revenue or delivery success. Research workflows preserve source, date, scope and uncertainty. Publication and external actions follow explicit user authorization.

Release preparation includes actual YAML parsing, resource and attribution checks, whole-tree privacy scans, deterministic ZIP archives, SHA-256 manifests and installation/rollback tests. [Synthetic evaluation cases and responses](evals/cases-and-responses.json) cover three scenarios for each original workflow. These were evaluated by one independent Codex evaluator in a shared context; they do not establish 81 independent runtime tests. See [evaluation limits](docs/EVALUATION.md) and [summary](evals/summary.json).

Search and AI-search recommendations use current primary documentation. FAQPage and `llms.txt` are not universal ranking requirements; indexing, citations and business impact must be measured separately. See [Google AI-search guidance](https://developers.google.com/search/docs/appearance/ai-features).

## Versions and maintenance

Immutable release packages carry individual skill versions, source commits and checksums. Third-party upstream versions remain distinct from local adaptation versions. A changed package must receive a new version; filesystem dates are not used to decide which copy is newer.

Monthly source review is scheduled for **the 1st day at 00:00 Asia/Novosibirsk**. GitHub Actions checks public sources and validates candidate changes with read-only repository permissions; full results stay in the run logs. A local Codex task first reconciles private/local copies, then reruns the public-source review from a fresh clone and prepares a PR using the existing GitHub CLI login after license and privacy checks. Manual PR creation has been demonstrated; a future scheduled run with changed sources remains unverified. Neither route merges, installs updates or publishes a release. Runtime compatibility must be checked again after relevant changes. The library is current to its recorded verification date and may lag upstream between checks. See [governance](docs/GOVERNANCE.md) and [changelog](CHANGELOG.md).

## Methodology and attribution

**Methodologist — Любовь Черемисина (Lyubov Cheremisina).**

- [cheremisina.ru](https://cheremisina.ru)
- [cheremisina.online](https://cheremisina.online)
- [Marketing skills library](https://github.com/LuCheremisina/marketing-skills)

Original universal methodology workflows are licensed under [MIT](LICENSE). Third-party packages retain their original authors, licenses and notices; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Sources without established redistribution permission are linked rather than republished. Methodologist attribution does not make her the author, narrator or brand of a client's output.

For citation use [CITATION.cff](CITATION.cff). Contributions should include provenance, appropriate licensing, synthetic examples and evidence of the affected checks; see [CONTRIBUTING.md](CONTRIBUTING.md).
