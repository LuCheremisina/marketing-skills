# Install an AI marketing skill

## Quick install

For a new project, use the open-source [skills CLI](https://github.com/vercel-labs/skills). Requirements for CLI 1.7.0: **Node.js 22.20+ and Git**.

```sh
npx skills add LuCheremisina/marketing-skills --skill che-deep-research
```

Run inside your project folder. Select a client if prompted, or add `--agent codex`, `--agent claude-code` or `--agent cursor`. The default is a project installation. Start a fresh client session and request the skill by name using its [sample task](use-cases/deep-research.md#try-it).

To browse before installing:

```sh
# 34 original marketing workflows
npx skills add LuCheremisina/marketing-skills --list
# All 48, including nested third-party engineering packages
npx skills add LuCheremisina/marketing-skills --list --full-depth
```

Choose only the skills you need. The five [starter pages](START-HERE.md) have individual commands and ZIP links. Global installation is an explicit CLI option, `--global`; for existing or modified copies use the verified route below. Quick install follows the current repository source; it does not verify a frozen release manifest, supply API access or prove workflow execution.

The CLI has its own install telemetry. To opt out, set `DISABLE_TELEMETRY=1` (PowerShell: `$env:DISABLE_TELEMETRY='1'`) before running it. See the [CLI documentation](https://github.com/vercel-labs/skills#telemetry).

## ZIP and plugin installation

For all 34 marketing skills in one ZIP, follow the native plugin guide: [English](INSTALL-PLUGIN.md) · [Русский](INSTALL-PLUGIN.ru.md).

Download an [individual skill ZIP or plugin bundle](https://github.com/LuCheremisina/marketing-skills/releases/latest). For coding clients, extract the complete skill folder into the client's documented skill directory, retaining `SKILL.md` and its resources. The ZIP is an alternative to the Node-based CLI. For an existing copy, compare it and keep a backup before replacing it. For account-side imports, use the supported ZIP/plugin flow described below; do not drop required references.

## Verified installation

For a frozen release, checksum verification, reviewed replacement of existing skills and rollback, use the repository installer.

The release provides two plugin ZIPs: the original-methodology bundle (`marketing-skills-plugin-<version>.zip`, 34 skills) and the optional third-party bundle (`marketing-skills-vendor-<version>.zip`, 14 skills). Each has its own portable plugin manifest. Install both only when the relevant workflows and dependencies are needed. Third-party packages retain original licenses and source attribution. The complete repository ZIP is for source review and tooling; do not assume its nested vendor folders are automatically discovered by every plugin host.

Select the frozen release tag you intend to install. Verify its manifest and SHA256SUMS and inspect the changes before replacing user-global skills. The quick CLI route above is a separate way to try the current repository source.

## Local clients

From a downloaded release and this repository's tools:

```sh
python3 scripts/install.py --manifest /absolute/release/manifest.json --target-dir /absolute/skill-root --ids che-daily-ai-news-digest,che-expert-article-workflow
```

The default is a dry run. `--target-dir` and explicit `--ids` are mandatory. Choose the directory already used by the client: Codex personal skills, Claude Code `~/.claude/skills`, or Cursor `~/.cursor/skills`. Do not repurpose managed plugin caches. Add `--apply` only after accepting the plan and backup location. Keep backups outside all scanned skill roots. Existing edited copies require a verified baseline or an explicit per-skill review; they are not silently overwritten.

Save the transaction journal and use the installer's `--rollback JOURNAL` mode for restore. A changed installed tree after the transaction must not be destroyed by rollback. Restart/refresh the client and check skill discovery and one safe task; file presence is not runtime acceptance.

For renamed authored skills, use the [public migration map](MIGRATION-2.0.md). Preserve your project profiles outside discovery before disabling an old route.

## Claude / Cowork

Use the complete marketing plugin ZIP through Customize → Plugins → Add → Upload a plugin; see the [full guide](INSTALL-PLUGIN.md#claude). A single-skill ZIP is also available through the separate Skills import flow. Import one first, invoke it, open a required reference, and test the missing-input path. Do not assume Claude Code environment substitutions work in Cowork.

## ChatGPT

Use the `marketing-skills-plugin` ZIP containing portable root `plugin.json` and authored skills. Follow the supported personal plugin creation/import flow in the account, install if prompted and begin a new chat. Verify discovery, resources and a safe task before marking installed. Availability depends on the account surface; merely attaching SKILL.md as a chat file is not native installation. No new MCP service or external account access is bundled.

## Grok Bot

Save the selected workflow as a skill in the private skill library through the supported Bot flow. Preserve decision rules, expected output and approval boundaries. Attach or transfer required resources through supported file handling and test the saved skill. If a package resource or script cannot execute, record the affected capability as unverified rather than claiming full import. No routine is created during compatibility testing.
