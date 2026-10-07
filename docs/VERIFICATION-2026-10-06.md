# Verification record — 2026-10-06

This record distinguishes publication, installation, discovery and sampled behavior. It is a dated snapshot, not a guarantee that every workflow or connector works in every client. The immutable release catalogue retains its original conservative execution statuses; this post-release document records subsequent evidence.

## Public distribution and checks

- [Release 1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2) is public: 41 individual skill archives, 3 bundles, manifest and SHA256SUMS, 46 files total. All 46 files downloaded without an authorization header and matched their accepted SHA-256 values. This establishes client download access and byte identity, not search indexing.
- [Public change PR1](https://github.com/LuCheremisina/marketing-skills/pull/1) merged the reviewed discovery-format adjustment. [Verification CI](https://github.com/LuCheremisina/marketing-skills/actions/runs/37439634549) succeeded: 49 tests, YAML/resource checks and public privacy checks. Whole-tree and 44-archive text scans found no flagged private paths, credentials or account/client identifiers; binary cover review was performed separately.
- Two deterministic release builds produced identical artifacts. Research-loop 1.0.1 changed only its description serialization and package version; parsed description, workflow body and other resources remained identical. The other 40 individual packages retained their preceding checksums.

## Installation and native evidence

| Client | Confirmed evidence | Remaining limitation |
|---|---|---|
| Codex | 27 authored skills and 14 shared vendor skills installed; all 41 enabled routes discovered with no parse errors. A global che-expert-article-workflow invocation loaded its requested resources and correctly refused production integration without verified author/site profiles. | Other workflows, connectors and full end-to-end outcomes have not all been executed. |
| Claude Code | 41 expected skills discovered after local installation. | Execution failed with account OAuth401; successful discovery is not successful task execution. Claude/Cowork account import is separate and unverified. |
| Cursor | 41 skill folders installed and payloads checked. | GUI discovery and task execution remain unverified. |
| ChatGPT | Both skills plugins saved and installed. The UI listed 26/27 authored skills and 14/14 vendor skills. One synthetic che-product-market-intake invocation produced a useful result. | Research-loop was missing from the UI before and after the quoted description retry in 1.0.2. Cause: UNKNOWN. Other plugin workflows and external connectors are not fully tested. |
| Grok Bot |Distribution guidance prepared. | Saved-library transfer, resource loading and execution remain unverified. |

Previous installed copies and private runtime profiles were retained in verified backups outside skill discovery roots. Installation journals, exact hashes and rollback evidence stay private; they are not part of this public repository. Sandbox installation, repeat unchanged detection and actual rollback were tested separately. Public packages require user-supplied brand, author, business and data profiles.

## Monthly maintenance

The schedule is the first day of each month at 00:00 Asia/Novosibirsk. A manual [monthly-source workflow run](https://github.com/LuCheremisina/marketing-skills/actions/runs/37438905717) completed successfully and found no updates across six monitored sources. The no-change run did not exercise changed-source PR creation. The current GitHub workflow now has read-only repository permissions and no PR-creation action: it logs full monitor results and validates ephemeral candidate files. The separately configured local Codex task reconciles private copies first, then reruns public monitoring from a fresh clone, checks license/privacy and prepares a PR with the existing GitHub CLI login. Manual PR creation through that existing login is demonstrated by [PR1](https://github.com/LuCheremisina/marketing-skills/pull/1) and [PR2](https://github.com/LuCheremisina/marketing-skills/pull/2); a future scheduled changed-source run remains unverified. Neither route merges, publishes a release or installs updates.

## Limits and reproducibility

The 81 synthetic text responses and targeted retests were reviewed by one evaluator in a shared context; they are not 81 independent native executions. Source availability, licensing and platform-dependent execution remain separate from package validity. The separate cloud audit's 36 source packages were unavailable for direct reconciliation. Managed plugins use provider updates; restricted sources remain linked rather than redistributed.

Use the release [manifest](https://github.com/LuCheremisina/marketing-skills/releases/download/v1.0.2/manifest.json) and [SHA256SUMS](https://github.com/LuCheremisina/marketing-skills/releases/download/v1.0.2/SHA256SUMS) when installing. This document was added after publication; it does not replace or repackage the frozen 1.0.2 artifacts. Search indexing, AI-search citations and measured business effect have not been established.
