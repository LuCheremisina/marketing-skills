# Platforms and practical compatibility

[Установка на русском](INSTALL.ru.md) · [Full plugin guide](INSTALL-PLUGIN.md) · [Полный плагин на русском](INSTALL-PLUGIN.ru.md)

The canonical format follows [Agent Skills](https://agentskills.io/specification). A package provides instructions and resources; available tools, permissions and execution support depend on your environment. A valid archive does not establish end-to-end compatibility for every workflow.

| Platform | Distribution path | Before use |
|---|---|---|
| Codex | [GitHub marketplace plugin](INSTALL-PLUGIN.md#codex) or [all / selected Skills via CLI](INSTALL.md#quick-install) | Verify discovery, invocation, resource loading and required tools |
| Claude Code | [GitHub marketplace plugin](INSTALL-PLUGIN.md#claude-code) or [Skills CLI](INSTALL.md#quick-install) | Verify discovery, script dependencies and connections; `${CLAUDE_SKILL_DIR}` is specific to Claude Code |
| Claude / Cowork | [GitHub marketplace or plugin ZIP](INSTALL-PLUGIN.md#claude--cowork); individual skill upload | Confirm that your account supports import and the required file/tool execution |
| Cursor | [All / selected Agent Skills via CLI](INSTALL.md#quick-install) | Verify discovery and execution in your project |
| ChatGPT | Skills plugin ZIP where supported | Check the imported skill list and required tools; availability depends on the account |
| Grok Bot | Saved skill library where supported | Transfer instructions and required resources, then test the saved skill |

Per-skill requirements and conservative verification statuses are in the [catalogue](../catalog/skills.json). Full runtime execution across all these platforms is not verified. Confirm the required capabilities for your selected skill before relying on its output.

Official references: [OpenAI skills](https://learn.chatgpt.com/docs/build-skills), [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Claude Code](https://code.claude.com/docs/en/skills), [Anthropic best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [Cursor](https://cursor.com/docs/skills), [Grok Bot](https://docs.x.ai/grok-bot/skills-routines-and-automations).

For other Agent Skills clients, consult current official documentation and test a selected workflow before claiming compatibility. If a required connection is unavailable, use an authorized normalized export where the workflow supports it or report the missing capability. Never fabricate results.

## Installation scope and usage

Native plugin installation registers the 34-skill bundle. `npx skills` installs the skills as folders; it does not register a plugin. Choose one route per bundle to avoid duplicates. CLI `-g` makes skills available across projects for your user; without it, they are installed in the current project. A local installation does not establish availability in a separate cloud session.

See [English usage examples](../README.md#how-to-use) or [примеры на русском](../README.ru.md#как-пользоваться), including plain-language requests and the Claude Code plugin namespace. Optional engineering workflows remain separate from the authored marketing plugin.

## Frontmatter interoperability

Use valid YAML with a description explaining both purpose and triggering conditions. A full YAML parser accepts folded and continued scalars; a quoted single-line description can improve discovery compatibility in some hosts. Verify the imported skill list and resource links rather than assuming that successful YAML validation proves native discovery.

## Русская версия

Пакет содержит инструкции и ресурсы. Доступность инструментов, MCP, исполнения скриптов и импорта зависит от вашей системы и аккаунта. Проверяйте обнаружение навыка, вызов, загрузку ресурсов и подключение источников. Полное выполнение всех навыков во всех системах не подтверждено. При отсутствии подключения используйте разрешённую выгрузку, если методология допускает её, либо укажите ограничение.

Русские инструкции: [весь плагин по системам](INSTALL-PLUGIN.ru.md), [все Skills или один через CLI](INSTALL.ru.md), [как пользоваться](../README.ru.md#как-пользоваться).
