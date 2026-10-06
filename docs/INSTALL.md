# Install, review and restore

The release provides two plugin ZIPs: the original-methodology bundle (`marketing-skills-plugin-<version>.zip`, 27 skills) and the optional third-party bundle (`marketing-skills-vendor-<version>.zip`, 14 skills). Each has its own portable plugin manifest. Install both only when the relevant workflows and dependencies are needed. Third-party packages retain original licenses and source attribution. The complete repository ZIP is for source review and tooling; do not assume its nested vendor folders are automatically discovered by every plugin host.

Use a frozen release, not mutable `main` or an unverified `latest` download. Before installing, verify the manifest and SHA256SUMS and inspect the changes. This candidate must be accepted before replacing user-global skills.

## Local clients

From a downloaded release and this repository's tools:

```sh
python3 scripts/install.py --manifest /absolute/release/manifest.json --target-dir /absolute/skill-root --ids daily-ai-news-digest,expert-article-workflow
```

The default is a dry run. `--target-dir` and explicit `--ids` are mandatory. Choose the directory already used by the client: Codex personal skills, Claude Code `~/.claude/skills`, or Cursor `~/.cursor/skills`. Do not repurpose managed plugin caches. Add `--apply` only after accepting the plan and backup location. Keep backups outside all scanned skill roots. Existing edited copies require a verified baseline or an explicit per-skill review; they are not silently overwritten.

Save the transaction journal and use the installer's `--rollback JOURNAL` mode for restore. A changed installed tree after the transaction must not be destroyed by rollback. Restart/refresh the client and check skill discovery and one safe task; file presence is not runtime acceptance.

Renamed private skills are mapped in the private migration report. Preserve their profile outside discovery before disabling an old route. Never upload that report to this public repository.

## Claude / Cowork

Use the single-skill ZIP accepted by the specific application. Import one first, invoke it, open a required reference, and test the missing-input path. Do not assume Claude Code environment substitutions work in Cowork.

## ChatGPT

Use the `marketing-skills-plugin` ZIP containing portable root `plugin.json` and authored skills. Follow the supported personal plugin creation/import flow in the account, install if prompted and begin a new chat. Verify discovery, resources and a safe task before marking installed. Availability depends on the account surface; merely attaching SKILL.md as a chat file is not native installation. No new MCP service or external account access is bundled.

## Grok Bot

Save the selected workflow as a skill in the private skill library through the supported Bot flow. Preserve decision rules, expected output and approval boundaries. Attach or transfer required resources through supported file handling and test the saved skill. If a package resource or script cannot execute, record the affected capability as unverified rather than claiming full import. No routine is created during compatibility testing.
