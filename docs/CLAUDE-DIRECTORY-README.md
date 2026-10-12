# Marketing Skill Cheremisina

**34 original marketing skills by Lyubov Cheremisina**, for market research, competitor monitoring, SEO/GEO, demand research, advertising analytics, expert articles, email marketing, newsletters, social posts and marketing deliverable acceptance.

Supply your own business profile, goals, period and data. The skills ask for missing inputs, check sources and distinguish measured facts from assumptions. They do not contain client profiles or bundled access to customer accounts.

## Start with a useful task

- Research: “Use che-deep-research to prepare a research brief for a fictional B2B service. Ask for missing inputs.”
- SEO/GEO: “Use che-seo-geo-auditor on a public URL. Link evidence and explain unverified checks.”
- Content: “Use che-expert-article-workflow with my brief. Separate sourced claims from hypotheses.”
- Analytics: “Use che-direct-analyst with synthetic campaign data. Do not access live accounts or send data.”

All 34 workflows and their resources are included. Scripts run only when a user requests their task and the host supports the required runtime; no hooks, background processes or bundled MCP servers start on installation. Some tasks need Python libraries or user-connected tools. Claude chat, Cowork and Claude Code have different execution capabilities; file availability does not prove a workflow can execute in every host.

## Connections, execution and data handling

This plugin includes readable Python scripts for collecting public news/web pages, calculating campaign metrics, generating reports, exporting covers and optionally delivering a digest. Scripts can create reports, SQLite caches and history/subscriber files in a user-selected location; existing scripts otherwise use their documented local application data directories. Users control retention and can remove these generated files. The publisher operates no storage backend for this plugin.

Public research can fetch websites and feeds selected for the task. AI-digest preparation sends selected RSS/news titles, URLs, summaries, prior digest context and ranked news to OpenAI only after `--allow-openai` is authorized. Industry-digest processing is local by default; `--allow-openai` additionally sends the business name, niche, language and selected public-news fragments to OpenAI. Without that flag the industry result is an unverified draft. Daily-digest collection lists its public news sources in its source code. Optional Telegram delivery uses `api.telegram.org` and requires a bot token and explicit recipients; it sends the prepared digest and processes subscriptions. Digest preparation never delivers or starts a listener. Telegram delivery is a separate `send_digest.py` command with explicitly approved recipients, confirmation and a receipt journal that prevents duplicate sends. Subscription handling is a separate owner-operated `bot_subscribe.py` process; it is not launched by preparation or delivery. The listener writes local subscriber records and logs; authorize and stop it separately. Optional OpenAI commentary in `che-direct-analyst` uses `api.openai.com` and sends the calculated campaign dataset only when the user enables that step and supplies access. The report is local by default (`--no_llm`); only an explicitly authorized `--llm` step requests OpenAI commentary. Do not use live personal or client data in a test.

**Credential review disclosure:** optional Telegram access in `bot_subscribe.py` and `send_digest.py`, OpenAI processing in `collect_and_send.py` and `che-industry-news-digest/scripts/collect_digest.py`, and commentary in `che-direct-analyst/scripts/run_report.py` use credentials supplied by the execution environment. The reporting adapter can also load an explicitly configured local `.env` file. Do not run these optional network steps without explicit user authorization. These optional vendor-credential paths are disclosed for directory review; they do not automatically acquire credentials through native `userConfig`. No credentials are bundled in this plugin. Never paste credentials into chat or reports.

For security review: the Telegram token is used only to construct Telegram Bot API calls, not attached to public news feed requests. `test_dry_run.py` uses synthetic `.test` URLs, mocks delivery and model calls, and performs no live delivery. `validate_dashboard_input.py` imports no environment or network API: its Python `set()` calls build collections, rather than executing the shell `set` command or reading credentials. It is unrelated to the industry digest’s public-page fetching. These observations explain the static cross-surface warnings; they do not assert review approval.

Other workflows can use tools the user already connected, including advertising, Wordstat, analytics and email connectors. Installation grants no API access and does not automatically install or connect MCP Panel. For optional MCP Panel setup, visit [cheremisina.ru](https://cheremisina.ru). Review the destination, data and permission before any send, publish or account write.

[Privacy and data handling](https://github.com/LuCheremisina/marketing-skills/blob/main/docs/PLUGIN-PRIVACY.md) · [MIT license terms](https://github.com/LuCheremisina/marketing-skills/blob/main/LICENSE).

## Author and support

Methodologist: **Любовь Черемисина / Lyubov Cheremisina**. [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online).

[Complete catalogue](https://github.com/LuCheremisina/marketing-skills/blob/main/docs/CATALOG.md) · [Installation in English and Russian](https://github.com/LuCheremisina/marketing-skills/blob/main/docs/INSTALL-PLUGIN.md) · [Support and bug reports](https://github.com/LuCheremisina/marketing-skills/issues).

MIT licensed. This Claude directory package contains authored skills only; the optional third-party engineering plugin is distributed separately. Its technical identity is `cheremisina-marketing-skills`, distinct from earlier manual ZIP installations named `marketing-skills`; preserve local changes before replacing an older installation and avoid enabling both copies at once.


## Platform eligibility and review boundaries

This Claude plugin is intended for users aged 18 and older. Use it only in accounts and environments permitted by the host's current terms. Anthropic requires Claude account users to be at least 18 years old.

Skills can prepare image concepts, prompts, video scripts and storyboards; actual generation or rendering requires separately available, user-authorized tools. This package does not operate a publisher-hosted image, video or audio generation service. Whether its media workflows are eligible under the directory policy remains for Anthropic to confirm; no written exception is asserted.

Use only sources and task inputs the user explicitly authorizes. The package does not grant access to unrelated chat history, memory or private files. The intended scope of user-supplied task files and existing connected sources under the directory policy must be confirmed during review.
