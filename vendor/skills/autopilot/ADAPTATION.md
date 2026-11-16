# Distribution adaptation

Original author, source and license are retained in UPSTREAM.md and LICENSE.

Changes include portable metadata, resource navigation, and the plan-gate correction recorded below; original attribution and license are retained.

- Claude-specific invocation fields moved to namespaced string metadata; explicit invocation boundary preserved in portable instructions.

## Packaging adaptation 1.0.1

The plan gate reports missing or unparseable requirement manifests and missing ticket files instead of silently passing or relying on stale in-memory ticket state.
