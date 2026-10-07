# AI Marketing Skills — research, SEO/GEO, analytics & content

> **Published v2.0.5:** 34 authored CHE_ workflows + 14 licensed engineering skills. [Release](https://github.com/LuCheremisina/marketing-skills/releases/tag/v2.0.5) · [Migration](docs/MIGRATION-2.0.md) · [MCP Panel connections](docs/MCP-CONNECTIONS.md).

**Install all 34 marketing skills with one ZIP:** [Marketing Skill Cheremisina — Claude and ChatGPT installation](docs/INSTALL-PLUGIN.md).

[Platform guide](docs/PLATFORMS.md): installation options and compatibility limitations.
Research a market, audit a website, analyse Yandex campaigns, find search demand, or turn evidence into an expert article with reusable AI workflows.

**34 original marketing workflows + 14 optional engineering skills.** Open Agent Skills packages for Codex, Claude Code and Cursor; ChatGPT plugin packages are also available. Each workflow lists the inputs and connections it needs. [Platform status](docs/PLATFORMS.md).

[**Install your first skill**](#quick-install) · [**Start with 5 marketing skills**](docs/START-HERE.md) · [**Browse all 48**](docs/CATALOG.md) · [**Download the latest release**](https://github.com/LuCheremisina/marketing-skills/releases/latest) · [Русская версия](README.ru.md)

## Quick install

With **Node.js 22.20+ and Git**, run this inside your project:

```sh
npx skills add LuCheremisina/marketing-skills --skill che-deep-research
```

Select your AI client if prompted, then ask it to use `che-deep-research` for your question. [Try the example](docs/use-cases/deep-research.md#try-it). Prefer a ZIP? [Download Deep Research 2.0.0](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.5/che-deep-research-3.0.0.zip) and follow the [client installation guide](docs/INSTALL.md#zip-and-plugin-installation).

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

Current published release: [**v2.0.5**](https://github.com/LuCheremisina/marketing-skills/releases/tag/v2.0.5). Individual versions and sources are tracked in the [catalogue](catalog/skills.json). Verify downloads using the release manifest and SHA-256 checksums.

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

| System | Distribution path / requirement |
|---|---|
| Codex | Local skill folders or supported plugins |
| Claude Code | Skill folders or supported plugins; script dependencies and connections required |
| Cursor | Native Agent Skills; verify discovery and execution in your project |
| ChatGPT | Plugin ZIP where account import is supported; tools vary by account |
| Claude / Cowork | Account-supported skill upload; verify required file/tool execution |
| Grok Bot | Saved skill library where supported; resources may need separate transfer |

The [platform guide](docs/PLATFORMS.md) describes requirements and limitations. Full execution across all platforms is not verified; test your selected workflow in your environment.

Use [quick or verified installation](docs/INSTALL.md) for the route that fits your environment. Never place credentials or client data inside an installed skill. Detailed platform guidance and official sources are in [PLATFORMS.md](docs/PLATFORMS.md).

## Evidence and quality

The library separates facts, hypotheses, recommendations and measured outcomes. Missing inputs or unavailable tools produce a clear limitation rather than fabricated research, revenue or delivery success. Research workflows preserve source, date, scope and uncertainty. Publication and external actions follow explicit user authorization.

Release preparation includes YAML parsing, resource and attribution checks, privacy scans, deterministic ZIP archives and SHA-256 manifests. Use the [workflow quality checklist](docs/EVALUATION.md) and skill-local synthetic fixtures to assess a selected workflow. These checks do not establish full native execution.

Search and AI-search recommendations use current primary documentation. FAQPage and `llms.txt` are not universal ranking requirements; indexing, citations and business impact must be measured separately. See [Google AI-search guidance](https://developers.google.com/search/docs/appearance/ai-features).

## Versions and maintenance

Immutable release packages carry individual skill versions, source commits and checksums. Third-party upstream versions remain distinct from local adaptation versions. A changed package must receive a new version; filesystem dates are not used to decide which copy is newer.

Public upstream checks are scheduled monthly, on **the 1st day at 00:00 Asia/Novosibirsk**, with read-only repository permissions. Updates require review; there is no automatic merge, installation or release publication. The library may lag upstream between checks. See [governance](docs/GOVERNANCE.md) and [changelog](CHANGELOG.md).

## Methodology and attribution

**Methodologist — Любовь Черемисина (Lyubov Cheremisina).**

- [cheremisina.ru](https://cheremisina.ru)
- [cheremisina.online](https://cheremisina.online)
- [Marketing skills library](https://github.com/LuCheremisina/marketing-skills)

Original universal methodology workflows are licensed under [MIT](LICENSE). Third-party packages retain their original authors, licenses and notices; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Sources without established redistribution permission are linked rather than republished. Methodologist attribution does not make her the author, narrator or brand of a client's output.

For citation use [CITATION.cff](CITATION.cff). Contributions should include provenance, appropriate licensing, synthetic examples and evidence of the affected checks; see [CONTRIBUTING.md](CONTRIBUTING.md).
