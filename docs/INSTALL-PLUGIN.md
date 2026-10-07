# Install Marketing Skill Cheremisina with one ZIP

[Русская инструкция](INSTALL-PLUGIN.ru.md)

Download **[marketing-skills-plugin-2.0.5.zip](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.5/marketing-skills-plugin-2.0.5.zip)**. Keep it zipped. This plugin includes all **34 original marketing skills** and their references, scripts and assets.

The optional **[marketing-skills-vendor-2.0.5.zip](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.5/marketing-skills-vendor-2.0.5.zip)** adds 14 third-party engineering skills, with their original attribution and licenses. Install it separately if needed. Together the two plugins provide 48 skills. The complete repository/source ZIP is not the native plugin installer.

## Claude

1. Open **Customize → Plugins** (Russian UI: **Персонализация → Плагины**).
2. Choose **Add → Upload a plugin**, then select `marketing-skills-plugin-2.0.5.zip`.
3. Confirm the import and enable **Marketing Skill Cheremisina**. Its Skills tab should show **34**.
4. Start a new chat or Cowork session. Ask: “Use che-deep-research to prepare a research brief for a fictional B2B service. Ask for missing inputs.”

To update an existing installation, upload the new ZIP through the same flow. Its technical name remains `marketing-skills`, so supported import flows recognize the existing plugin. Review the replacement prompt rather than creating a duplicate. Plugin import is separate from importing an individual skill through the Skills tab.

See [Claude's official plugin guide](https://support.claude.com/en/articles/13837440-use-plugins-in-claude). Availability and organization policies can affect access.

## ChatGPT

ChatGPT can create a plugin containing all 34 skills from this one ZIP **when the account has Plugins and Plugin Creator available**. An ordinary file attachment alone does not install skills.

1. Open the account's **Plugins** area and use its **Build plugins / Plugin Creator** entry to start a plugin-building conversation.
2. Attach `marketing-skills-plugin-2.0.5.zip` and request: “Create a private personal plugin from this archive, preserve its manifests and all 34 skills, and give me the plugin installation link. Do not publish it to an organization.”
3. Open the returned plugin page and install or enable it if prompted. Verify **Marketing Skill Cheremisina** and **34 skills**.
4. Start a new chat and request `che-deep-research` using the sample above.

For an existing installation, give Plugin Creator its existing plugin page link and ask it to **update that plugin from the ZIP**, preserving its audience. Do not request a second plugin. Button labels may vary by account. If Plugins or Plugin Creator is unavailable, this account cannot use this native route; uploading the ZIP as ordinary chat context is not an equivalent installation.

See [OpenAI's plugin guide](https://learn.chatgpt.com/docs/plugins) and [plugin package format](https://developers.openai.com/plugins/build/plugins).

## What installation includes

Installation makes the bundled instructions and resources available. It does not connect external accounts or grant API access. Some workflows need separate tools, credentials or MCP connections; see [MCP connection guidance](MCP-CONNECTIONS.md) and [MCP Panel](https://cheremisina.ru). Test one task and resource access before using a workflow for business decisions.

Methodologist: **Любовь Черемисина / Lyubov Cheremisina** — [cheremisina.ru](https://cheremisina.ru), [cheremisina.online](https://cheremisina.online).
