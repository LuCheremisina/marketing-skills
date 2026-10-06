# Marketing Skills

Reusable AI workflows for marketing research, campaign analytics, SEO/GEO, editorial content and business decisions. Each workflow defines its inputs, source requirements, expected output and limits so a team can review the result before acting.

[Русская версия](README.ru.md) · [Skill catalogue](docs/CATALOG.md) · [Installation](docs/INSTALL.md) · [Platform compatibility](docs/PLATFORMS.md) · [Releases](https://github.com/LuCheremisina/marketing-skills/releases)

![Marketing Skills — research, analytics, SEO/GEO and content](assets/social-preview.png)

The library contains **27 original methodology workflows** and **14 licensed third-party engineering skills**. It follows the [Agent Skills format](https://agentskills.io/specification). The public packages contain no client profiles, account credentials or personal workstation paths. Brand, author, business and data profiles are supplied by the user at run time.

## Choose a workflow

| Business task | Start with | Reviewable result |
|---|---|---|
| Understand a market or customer decision | `product-market-intake`, `deep-research`, `research-loop` | Research scope, evidence, uncertainty and next-process decision |
| Assess campaign performance | `direct-analytics-skill`, `direct-analyst`, `audit-unisender-email` | Source-separated metrics, attribution limits and prioritized actions |
| Plan growth and monitor demand | `build-predictive-growth-dashboard`, `wordstat-trend-radar`, `seo-demand-analytics` | Scenarios, trend signals and their assumptions |
| Improve search and AI-search visibility | `seo-geo-auditor`, `seo-geo-auditor-pro`, `wordstat-keyword-research`, `topic-planner` | Contextual findings, intent and a practical content plan |
| Create sourced expert content | `expert-article-workflow`, `seo-article-generator`, `news-editorial-workflow` | Draft, evidence ledger and conditional integration handoff |
| Produce social and audio content | `content-carousel`, `telegram-content-creator`, `news-voiceover-script`, `short-video-production` | Storyboard or script; actual media only when the runtime is available |
| Prepare covers and apply brand guidance | `brand-profile-guide`, `editorial-cover-prompts`, `news-cover-production` | Brand-aligned concepts, prompts and validated image export |
| Monitor industry and AI news | `industry-news-digest`, `daily-ai-news-digest` | Sourced digest with time window, deduplication and delivery status |
| Accept a delivery or prevent a regression | `brief-acceptance`, `skill-regression-check` | Requirement evidence, unresolved gaps and regression verdict |

See the [complete catalogue](docs/CATALOG.md) for inputs, outputs and required connections. Cloudflare skills and `autopilot` are optional engineering support packages; original authorship and licenses are documented in [third-party sources](docs/third-party-sources.md).

## Use with your AI system

| System | Distribution route | Practical status |
|---|---|---|
| Codex | Skill folders or skills plugin | Two workflows sampled in isolated Codex CLI; global installation and remaining workflows require acceptance |
| Claude Code | Skill folders or plugin | Package checks completed; native run blocked by account authentication |
| Claude / Cowork | Supported account-side skill import | Import and execution not verified |
| Cursor | Native Agent Skills | Client-side discovery and execution not verified |
| ChatGPT | Skills-only plugin with portable `plugin.json` | Account import and execution not verified |
| Grok Bot | Saved skill library with complete instructions/resources | Transfer and execution not verified |

Compatibility is recorded **per skill** in [catalog/skills.json](catalog/skills.json). `verified`, `requires_connection`, `not_verified` and `not_supported` describe practical execution, not marketing promises. File format compliance does not establish that every system can run scripts, access MCP tools, generate media or publish results.

Start with [installation instructions](docs/INSTALL.md). Select only the skills you need, inspect the manifest and run the installer in dry-run mode. Never place credentials or client data inside an installed skill. Detailed platform guidance and official sources are in [PLATFORMS.md](docs/PLATFORMS.md).

## Evidence and quality

The library separates facts, hypotheses, recommendations and measured outcomes. Missing inputs or unavailable tools produce a clear limitation rather than fabricated research, revenue or delivery success. Research workflows preserve source, date, scope and uncertainty. Publication and external actions follow explicit user authorization.

Release preparation includes actual YAML parsing, resource and attribution checks, whole-tree privacy scans, deterministic ZIP archives, SHA-256 manifests and installation/rollback tests. [Synthetic evaluation cases and responses](evals/cases-and-responses.json) cover three scenarios for each original workflow. These were evaluated by one independent Codex evaluator in a shared context; they do not establish 81 independent runtime tests. See [evaluation limits](docs/EVALUATION.md) and [summary](evals/summary.json).

Search and AI-search recommendations use current primary documentation. FAQPage and `llms.txt` are not universal ranking requirements; indexing, citations and business impact must be measured separately. See [Google AI-search guidance](https://developers.google.com/search/docs/appearance/ai-features).

## Versions and maintenance

Immutable release packages carry individual skill versions, source commits and checksums. Third-party upstream versions remain distinct from local adaptation versions. A changed package must receive a new version; filesystem dates are not used to decide which copy is newer.

Monthly source review is scheduled for **the 1st day at 00:00 Asia/Novosibirsk**. The workflow prepares a review PR and records source/license conflicts. It does not merge, install updates or publish a release. Runtime compatibility must be checked again after relevant changes. The library is current to its recorded verification date and may lag upstream between checks. See [governance](docs/GOVERNANCE.md) and [changelog](CHANGELOG.md).

## Methodology and attribution

**Methodologist — Любовь Черемисина (Lyubov Cheremisina).**

- [cheremisina.ru](https://cheremisina.ru)
- [cheremisina.online](https://cheremisina.online)
- [Marketing skills library](https://github.com/LuCheremisina/marketing-skills)

Original universal methodology workflows are licensed under [MIT](LICENSE). Third-party packages retain their original authors, licenses and notices; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Sources without established redistribution permission are linked rather than republished. Methodologist attribution does not make her the author, narrator or brand of a client's output.

For citation use [CITATION.cff](CITATION.cff). Contributions should include provenance, appropriate licensing, synthetic examples and evidence of the affected checks; see [CONTRIBUTING.md](CONTRIBUTING.md).
