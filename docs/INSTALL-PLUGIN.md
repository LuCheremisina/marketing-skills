# Install the complete Marketing Skill Cheremisina plugin

[Русская инструкция](INSTALL-PLUGIN.ru.md)

For ZIP installation, download **[marketing-skills-plugin-2.0.7.zip](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.7/marketing-skills-plugin-2.0.7.zip)**. Keep it zipped. This plugin includes all **34 original marketing skills** and their references, scripts and assets.

The optional **[marketing-skills-vendor-2.0.7.zip](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.7/marketing-skills-vendor-2.0.7.zip)** adds 14 third-party engineering skills, with their original attribution and licenses. Install it separately if needed. Together the two plugins provide 48 skills. The complete repository/source ZIP is not the native plugin installer.

## Choose a route

| System | Complete plugin | Individual skills |
|---|---|---|
| Codex CLI / local Codex | GitHub marketplace; commands below | `npx skills`, all 34 or selected |
| Claude Code | GitHub marketplace; commands below | `npx skills`, all 34 or selected |
| Cursor | Use the Agent Skills bundle through the CLI | `npx skills`, all 34 or selected |
| Claude / Cowork | GitHub marketplace or ZIP | Individual ZIP through Skills, where supported |
| ChatGPT | Private plugin from ZIP through Plugin Creator | Individual ZIP through supported skill creation |
| Grok Bot | No universal plugin import command is verified | Save a skill and its resources in the Bot library |

Use one route for a given bundle to avoid duplicate active copies. [All Skills or one through the CLI](INSTALL.md). ZIP downloads are frozen releases; marketplaces use repository source. Updating `main` does not change an existing release ZIP.

## Claude Code

Enter these in your Claude Code chat, in order:

```text
/plugin marketplace add LuCheremisina/marketing-skills
/plugin install marketing-skills@cheremisina-marketing
```

Or use your terminal:

```sh
claude plugin marketplace add LuCheremisina/marketing-skills
claude plugin install marketing-skills@cheremisina-marketing --scope user
```

`user` enables it across projects for your user on this machine. For a shared project use `--scope project` instead. Check `claude plugin list`, open a new session and run:

```text
/marketing-skills:che-deep-research Prepare a research brief for a fictional B2B service. Ask for missing inputs first.
```

The [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) catalogue is named `cheremisina-marketing`, with plugin `marketing-skills` sourced from the repository root containing 34 skills. The Claude directory package at `platforms/claude/cheremisina-marketing-skills` has a separate technical identity; avoid installing it as a second copy of the same workflows.

[Official Claude Code guide](https://code.claude.com/docs/en/discover-plugins).

## Codex

Run in a terminal with Codex CLI installed:

```sh
codex plugin marketplace add LuCheremisina/marketing-skills
codex plugin add marketing-skills@cheremisina-marketing
codex plugin list
```

In the Codex interface, open **Plugins → Add plugin marketplace**, enter `LuCheremisina/marketing-skills`, then install **Marketing Skill Cheremisina** from `cheremisina-marketing`. In a Codex CLI session, `/plugins` opens the browser. If your version lacks these commands or controls, use the [Skills CLI](INSTALL.md).

Codex reads [`.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json) and [`.codex-plugin/plugin.json`](../.codex-plugin/plugin.json). Start a new chat, select the installed plugin and ask: “Use che-deep-research to prepare a research brief for a fictional B2B service.”

A local installation does not establish availability in a separate cloud task: configure installation and verify discovery there separately. [Official Codex commands](https://learn.chatgpt.com/docs/developer-commands), [marketplace format](https://developers.openai.com/plugins/build/plugins).

## Claude / Cowork

### From GitHub without a ZIP download

Open **Customize → Plugins → Add → Add marketplace → Add from a repository** and enter:

```text
https://github.com/LuCheremisina/marketing-skills
```

Sync the catalogue, select **Marketing Skill Cheremisina** and install it. Check for 34 skills. If account or organization policy restricts marketplace addition, use the permitted ZIP import below.

### From ZIP

1. Open **Customize → Plugins** (Russian UI: **Персонализация → Плагины**).
2. Choose **Add → Upload a plugin**, then select `marketing-skills-plugin-2.0.7.zip`.
3. Confirm the import and enable **Marketing Skill Cheremisina**. Its Skills tab should show **34**.
4. Start a new chat or Cowork session. Ask: “Use che-deep-research to prepare a research brief for a fictional B2B service. Ask for missing inputs.”

To update an existing installation, upload the new ZIP through the same flow. Its technical name remains `marketing-skills`, so supported import flows recognize the existing plugin. Review the replacement prompt rather than creating a duplicate. Plugin import is separate from importing an individual skill through the Skills tab.

See [Claude's official plugin guide](https://support.claude.com/en/articles/13837440-use-plugins-in-claude). Availability and organization policies can affect access.

## ChatGPT

ChatGPT can create a plugin containing all 34 skills from this one ZIP **when the account has Plugins and Plugin Creator available**. An ordinary file attachment alone does not install skills.

1. Open the account's **Plugins** area and use its **Build plugins / Plugin Creator** entry to start a plugin-building conversation.
2. Attach `marketing-skills-plugin-2.0.7.zip` and request: “Create a private personal plugin from this archive, preserve its manifests and all 34 skills, and give me the plugin installation link. Do not publish it to an organization.”
3. Open the returned plugin page and install or enable it if prompted. Verify **Marketing Skill Cheremisina** and **34 skills**.
4. Start a new chat and request `che-deep-research` using the sample above.

For an existing installation, give Plugin Creator its existing plugin page link and ask it to **update that plugin from the ZIP**, preserving its audience. Do not request a second plugin. Button labels may vary by account. If Plugins or Plugin Creator is unavailable, this account cannot use this native route; uploading the ZIP as ordinary chat context is not an equivalent installation.

See [OpenAI's plugin guide](https://learn.chatgpt.com/docs/plugins) and [plugin package format](https://developers.openai.com/plugins/build/plugins).

## Cursor and individual Skills

Use the [Skills CLI guide](INSTALL.md) for all 34 or one skill in Codex, Claude Code and Cursor, with global and project scopes, checks, updates and removal. This installs skill folders; it does not register a Cursor marketplace plugin. [Usage examples](../README.md#how-to-use).

## What installation includes

Installation makes the bundled instructions and resources available. It does not connect external accounts or grant API access. Some workflows need separate tools, credentials or MCP connections; see [MCP connection guidance](MCP-CONNECTIONS.md) and [MCP Panel](https://cheremisina.ru). Test one task and resource access before using a workflow for business decisions.

Methodologist: **Любовь Черемисина / Lyubov Cheremisina** — [cheremisina.ru](https://cheremisina.ru), [cheremisina.online](https://cheremisina.online).

## Update an existing ChatGPT plugin

Attach the latest authored-plugin ZIP and ask: “Update my existing Marketing Skill Cheremisina plugin from this archive. Preserve its identity, access and all 34 skills; do not create a duplicate or downgrade a newer installation. Verify the version and the changed digest scripts after updating. Do not run delivery or paid APIs.”

Repository changes and release downloads do not automatically update existing installations. Account update support depends on the current host; if unavailable, use its supported editor/import flow and retain a backup.

## Updates and removal

Use the same mechanism used for installation. For `npx` Skills, see [CLI updates and removal](INSTALL.md#updates-and-removal).

**Claude Code**, in your terminal:

```sh
claude plugin marketplace update cheremisina-marketing
claude plugin update marketing-skills@cheremisina-marketing
claude plugin uninstall marketing-skills@cheremisina-marketing
```

The first two lines update; the third uninstalls. Run only the action you need. For a project installation, pass `--scope project` to update or uninstall. Preserve local edits, then check the version and a sample task.

**Codex**: `codex plugin marketplace upgrade cheremisina-marketing` refreshes the Git marketplace source. Check `codex plugin list` and apply the available plugin update through Plugins. To uninstall: `codex plugin remove marketing-skills@cheremisina-marketing`. Refreshing source alone is not evidence that an installed copy has been replaced.

**Claude / Cowork**: manage the marketplace and plugin through Plugins; for ZIP imports, replace the existing plugin through the supported flow. **ChatGPT**: update the existing plugin through Plugin Creator as above, or remove it through Installed. Before switching installation routes, preserve edits and disable the old copy.
