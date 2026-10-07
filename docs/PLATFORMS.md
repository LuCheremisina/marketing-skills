# Platforms and practical compatibility

> **Published v2.0.1:** the table below is the historical v1.0.2 snapshot, not current CHE_ execution acceptance.
The canonical format follows [Agent Skills](https://agentskills.io/specification). Common instructions do not imply equal tool availability. The machine-readable catalogue reports actual verification per skill; the release catalogue is a baseline, and subsequent installation and sampled execution are recorded in the [2026-10-06 verification report](VERIFICATION-2026-10-06.md).

| Platform | Supported distribution path | Evidence as of 2026-10-06 / limitation |
|---|---|---|
| Codex | Local skill folder or plugin | 41 installed skills discovered; a representative global article task tested; other execution paths unverified |
| Claude Code | Local `.claude/skills` or plugin | 41 expected skills discovered; execution blocked by account OAuth401. `${CLAUDE_SKILL_DIR}` remains Claude Code-specific |
| Claude / Cowork | Supported skill upload mechanism | Import, file execution and connector availability require account-side testing |
| Cursor | Native Agent Skills | 41 skill folders installed; GUI discovery and execution remain unverified |
| ChatGPT | Skills-only plugin | Both plugins installed; UI lists 26/27 authored and 14/14 vendor skills; one synthetic intake task tested; che-research-loop discovery unresolved |
| Grok Bot | Saved skill library / supported packaged skill | Provide complete workflow and necessary resources, then test the saved skill; this is not a Grok Build filesystem install |

Official references checked 2026-10-06: [OpenAI skills](https://learn.chatgpt.com/docs/build-skills), [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Claude Code](https://code.claude.com/docs/en/skills), [Anthropic best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [Cursor](https://cursor.com/docs/skills), [Grok Bot](https://docs.x.ai/grok-bot/skills-routines-and-automations).

For other Agent Skills clients, including Gemini CLI and GitHub Copilot, use current official documentation and run a separate smoke test before adding a verified badge. A README assertion or YAML pass is not that test.

If a skill needs unavailable search, analytics, image generation, rendering or external delivery: accept authorized normalized exports where supported, identify the exact missing capability, and keep the dependent step unverified. Do not silently replace providers, fabricate results or add MCP servers.

## Frontmatter interoperability

A full YAML parser accepts plain descriptions continued across indented lines. In a native ChatGPT import of candidate 1.0.1, the UI displayed 26 of 27 authored workflows and omitted `che-research-loop`, whose description used this valid syntax. Release 1.0.2 serializes that same description as one quoted YAML line, but the repeated native import still displayed 26 skills and omitted `che-research-loop`. The cause is unknown; the serialization change did not resolve the discovery issue. This is a conservative discovery-compatibility adjustment, not a claim that the original YAML was invalid or that all clients reject continuation syntax. Prefer a quoted single-line description when a host fails to discover a valid skill, and verify the saved skill list after import. Static validation does not replace that native check.
