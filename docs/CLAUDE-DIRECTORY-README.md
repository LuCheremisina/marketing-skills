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

Public research can fetch websites and feeds selected for the task. Daily-digest collection lists its public news sources in its source code. Optional Telegram delivery uses `api.telegram.org` and requires a bot token and explicit recipients; it sends the prepared digest and processes subscriptions. A live digest run can launch the included `bot_subscribe.py` listener as a separate background process if it is not already running; this does not happen on installation or in dry-run mode. That listener writes a local subscription log, so obtain authorization for running it and stop it when subscription processing is no longer needed. Optional OpenAI commentary in `che-direct-analyst` uses `api.openai.com` and sends the calculated campaign dataset only when the user enables that step and supplies access. Use its `--no-llm` mode for a deterministic local report. Do not use live personal or client data in a test.

**Credential review disclosure:** three included scripts currently accept user-provided vendor credentials through environment configuration: `bot_subscribe.py`, `collect_and_send.py` and `run_report.py`. The reporting adapter can also load an explicitly configured local `.env` file. Do not run these optional network steps without explicit user authorization. These optional vendor-credential paths are disclosed for directory review; they do not automatically acquire credentials through native `userConfig`. No credentials are bundled in this plugin. Never paste credentials into chat or reports.

For security review: the Telegram token is used only to construct Telegram Bot API calls, not attached to public news feed requests. `test_dry_run.py` uses synthetic `.test` URLs, mocks delivery and model calls, and performs no live delivery. `validate_dashboard_input.py` imports no environment or network API: its Python `set()` calls build collections, rather than executing the shell `set` command or reading credentials. It is unrelated to the industry digest’s public-page fetching. These observations explain the static cross-surface warnings; they do not assert review approval.

Other workflows can use tools the user already connected, including advertising, Wordstat, analytics and email connectors. Installation grants no API access and does not automatically install or connect MCP Panel. For optional MCP Panel setup, visit [cheremisina.ru](https://cheremisina.ru). Review the destination, data and permission before any send, publish or account write.

## Author and support

Methodologist: **Любовь Черемисина / Lyubov Cheremisina**. [cheremisina.ru](https://cheremisina.ru) · [cheremisina.online](https://cheremisina.online).

[Complete catalogue](https://github.com/LuCheremisina/marketing-skills/blob/main/docs/CATALOG.md) · [Installation in English and Russian](https://github.com/LuCheremisina/marketing-skills/blob/main/docs/INSTALL-PLUGIN.md) · [Support and bug reports](https://github.com/LuCheremisina/marketing-skills/issues).

MIT licensed. This Claude directory package contains authored skills only; the optional third-party engineering plugin is distributed separately. Its technical identity is `cheremisina-marketing-skills`, distinct from earlier manual ZIP installations named `marketing-skills`; preserve local changes before replacing an older installation and avoid enabling both copies at once.
