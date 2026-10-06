# Third-party sources and attribution

Third-party authors and source licenses remain in force. The repository MIT license applies only to original library materials. Provider-managed plugins are updated through their provider, not overwritten by this library.

| Publisher / repository | Pinned source | License | Distribution |
|---|---|---|---|
| [cloudflare/skills](https://github.com/cloudflare/skills) | `41e0d1985894` | Apache-2.0 | licensed-vendor |
| [nick-vels/skills](https://github.com/nick-vels/skills) | `d6427a85557c` | MIT | licensed-vendor |
| [AgriciDaniel/codex-seo](https://github.com/AgriciDaniel/codex-seo) | `9a4a0b9e3c44` | Custom / proprietary; see publisher terms | external-only |
| [openai/skills](https://github.com/openai/skills) | `49f948faa925` | Not established | external-only |
| [openai/plugins](https://github.com/openai/plugins) | `5fd93af4cd0c` | Not established | external-only |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | `4f5677ad3527` | Custom / proprietary; see publisher terms | external-only |

## Installation and limits

For external-only sources, follow the upstream repository installation instructions and obtain the current package from its official publisher. Do not copy managed provider caches. Remotion packages can require a commercial license; OpenAI public counterpart versions do not establish which installed channel is current.

Bundled third-party packages preserve upstream instructions; no cross-platform execution claims are made. Review required connectors, permissions, scripts, and external service dependencies before installation.

## Update policy

Source commits and complete resource directories are pinned. Different contents under the same version are treated as a conflict requiring review. Local modifications are preserved until compared against a common baseline. No automated installation or merge is enabled.

## License exclusions

The inspected stable release of `AgriciDaniel/codex-seo` uses a proprietary license that expressly prohibits redistribution and requires current publisher membership for use. It is not bundled. The Remotion root license governs video/image production use and does not establish a general standalone skill-library redistribution right; no permissive skill-package license was found, so Remotion packages are not bundled. These packages remain available through their original publishers subject to their terms.
