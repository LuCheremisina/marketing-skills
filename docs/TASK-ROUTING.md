# Choose one workflow for the requested result

Shared tools do not make workflows duplicates. Choose by input and deliverable, then load supporting workflows only when needed.

| Need | Workflow boundary |
|---|---|
| Audit an existing skill library | `che-skill-optimizer`; `che-skill-regression-check` reproduces a specific observed failure instead |
| Find a public skill | `che-internet-skill-finder`; it does not replace plugin management or installed-library auditing |
| Email from supplied materials | `che-email-marketing` writes the reviewed message; no audit or automatic send |
| Choose the weekly editorial axis | `che-email-digest-topic-planner` selects demand-backed materials; it does not create a campaign |
| Full audit → demand → draft cycle | `che-unisender-email-pipeline` maintains state and an authorized draft; sending remains separate |
| Campaign effectiveness | `che-audit-unisender-email` diagnoses existing delivery and post-click data |
| Competitor changes | `che-competitive-monitor` tracks configured signals, thresholds, owners and actions |
| Brand presence | `che-brand-presence` measures comparable baselines; BPI components and SoV remain separate |
| Cover prompt vs ready image | `che-editorial-cover-prompts` returns a brief; `che-cover-production` generates/QA/exports article or news images |
| Full crawl vs scoped SEO question | `che-seo-geo-auditor` crawls the site; `che-seo-geo-auditor-pro` reviews a specific page or disputed claim |
| Intake vs deep research | `che-product-market-intake` structures provided context and research gaps; `che-deep-research` investigates evidence |
| Keyword set vs historical trend vs full SEO funnel | `che-wordstat-keyword-research`, `che-wordstat-trend-radar`, `che-seo-demand-analytics` have distinct output contracts |

The main catalogue contains one installable folder per canonical ID. Project names, competitor sets, tone, palette and account details are run-time inputs, not additional skills.
