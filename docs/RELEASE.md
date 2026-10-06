# Reviewed releases

Run the public checks and affected workflow tests. Build into a new directory with a new release version. For every release after the first, provide the accepted previous manifest explicitly:

```bash
python scripts/build_release.py --output dist --version 1.1.0 --previous-manifest /path/to/accepted-previous/manifest.json
python scripts/audit_public.py --archives-dir dist
```

The baseline prevents changed skill bytes under the same skill/adaptation version, even across separate output directories. The previous manifest must come from an accepted immutable release, not a regenerated local copy. Keep it with the release checksums. A new library release version alone does not authorize replacing an unchanged individual package version with new contents.

The standalone `manifest.json` is authoritative for all release archives. The complete bundle embeds a package manifest without its own outer ZIP checksum to avoid a self-reference; verify the complete ZIP against the standalone manifest and `SHA256SUMS`.

Before publication, verify SHA256SUMS, licensing, attribution, synthetic examples and runtime evidence. Review the exact repository commit and archive manifest. Publication, release upload and global installation are separate acceptance steps. Record successful public anonymous repository/download checks after publication; do not infer them from a local build.

GitHub's verification workflow builds a candidate and does not publish it. The monthly GitHub workflow checks sources with read-only permissions; the local Codex task recreates candidates and prepares PRs with the existing CLI login. Neither route substitutes for release acceptance.

The verification workflow derives its candidate version from `plugin.json`. It rebuilds a clean candidate without a previous-release file and does not authorize publication. Before an actual subsequent release, the maintainer must supply the accepted previous release manifest with `--previous-manifest`; the source checks alone cannot enforce immutability against historical artifacts. Published immutable release: [1.0.2](https://github.com/LuCheremisina/marketing-skills/releases/tag/v1.0.2). Only the `research-loop` individual package changed from 1.0.1: its description serialization and package version, with unchanged parsed text, workflow body and resources. The other 40 individual skill archives remain byte-identical.

Post-publication verification documentation may advance on `main` while the immutable release tag and artifacts remain unchanged. Do not rebuild or re-upload 1.0.2 from a later documentation commit: passing the accepted 1.0.2 manifest with `--previous-manifest` rejects changed bundle contents under that release version. A future distributed package must use a new library version and the accepted previous manifest, even when its individual skill payloads are unchanged.
