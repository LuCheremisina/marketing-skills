# Reviewed releases

Run the public checks and affected workflow tests. Build into a new directory with a new release version. For every release after the first, provide the accepted previous manifest explicitly:

```bash
python scripts/build_release.py --output dist --version 1.1.0 --previous-manifest /path/to/accepted-previous/manifest.json
python scripts/audit_public.py --archives-dir dist
```

The baseline prevents changed skill bytes under the same skill/adaptation version, even across separate output directories. The previous manifest must come from an accepted immutable release, not a regenerated local copy. Keep it with the release checksums. A new library release version alone does not authorize replacing an unchanged individual package version with new contents.

The standalone `manifest.json` is authoritative for all release archives. The complete bundle embeds a package manifest without its own outer ZIP checksum to avoid a self-reference; verify the complete ZIP against the standalone manifest and `SHA256SUMS`.

Before publication, verify SHA256SUMS, licensing, attribution, synthetic examples and runtime evidence. Review the exact repository commit and archive manifest. Publication, release upload and global installation are separate acceptance steps. Record successful public anonymous repository/download checks after publication; do not infer them from a local build.

GitHub's verification workflow builds a candidate and does not publish it. The monthly workflow prepares a PR and cannot substitute for release acceptance.
