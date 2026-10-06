# Contributing

Use a focused pull request. Provide the current skill version, source commit when applicable, concrete trigger and before/after outcome, synthetic inputs, required connections and actual verification evidence. Preserve methodology contracts and original author notices.

Run `python3 -m pip install -r requirements-dev.txt`, `python3 scripts/validate.py --root .`, and `python3 -m unittest discover -s tests`. Test modified runtime scripts from an unrelated working directory. Never include profiles, credentials, datasets, transcripts, account IDs, local inventory or private source diffs in a public PR.

Semantic versions: breaking contract/behavior change → major; compatible capability → minor; correction → patch. Same version with changed bytes blocks release. Automatic PRs require review; they never grant permission to install, merge or publish.
