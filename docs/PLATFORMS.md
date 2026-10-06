# Platforms and practical compatibility

The canonical format follows [Agent Skills](https://agentskills.io/specification). Common instructions do not imply equal tool availability. The machine-readable catalogue reports actual verification per skill; the initial candidate is not yet installed into user accounts.

| Platform | Supported distribution path | Initial evidence / limitation |
|---|---|---|
| Codex | Local skill folder or plugin | Structural validation and isolated CLI test tracked separately from global installation |
| Claude Code | Local `.claude/skills` or plugin | Scripts use an installed root, not cwd; `${CLAUDE_SKILL_DIR}` is specific to supported Claude Code contexts |
| Claude / Cowork | Supported skill upload mechanism | Import, file execution and connector availability require account-side testing |
| Cursor | Native Agent Skills | Installation folder/package detection requires testing in the installed Cursor client |
| ChatGPT | Skills-only plugin | Root portable `plugin.json`; account import and discovery require a native test |
| Grok Bot | Saved skill library / supported packaged skill | Provide complete workflow and necessary resources, then test the saved skill; this is not a Grok Build filesystem install |

Official references checked 2026-10-06: [OpenAI skills](https://learn.chatgpt.com/docs/build-skills), [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Claude Code](https://code.claude.com/docs/en/skills), [Anthropic best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [Cursor](https://cursor.com/docs/skills), [Grok Bot](https://docs.x.ai/grok-bot/skills-routines-and-automations).

For other Agent Skills clients, including Gemini CLI and GitHub Copilot, use current official documentation and run a separate smoke test before adding a verified badge. A README assertion or YAML pass is not that test.

If a skill needs unavailable search, analytics, image generation, rendering or external delivery: accept authorized normalized exports where supported, identify the exact missing capability, and keep the dependent step unverified. Do not silently replace providers, fabricate results or add MCP servers.

## Frontmatter interoperability

A full YAML parser accepts plain descriptions continued across indented lines. In a native ChatGPT import of candidate 1.0.1, the UI displayed 26 of 27 authored workflows and omitted `research-loop`, whose description used this valid syntax. Candidate 1.0.2 serializes that same description as one quoted YAML line. This is a conservative discovery-compatibility adjustment, not a claim that the original YAML was invalid or that all clients reject continuation syntax. Prefer a quoted single-line description when a host fails to discover a valid skill, and verify the saved skill list after import. Static validation does not replace that native check.
