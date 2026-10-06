# Contributing

You can help without editing a skill: improve installation docs, translate a use-case page, report a broken link, or share a synthetic example of a workflow that worked. Use [Discussions](https://github.com/LuCheremisina/marketing-skills/discussions) for questions and new task ideas. Documentation PRs should change documentation only; include the affected links or install command and how you checked them.

Use a focused pull request. Provide the current skill version, source commit when applicable, concrete trigger and before/after outcome, synthetic inputs, required connections and actual verification evidence. Preserve methodology contracts and original author notices.

Run `python3 -m pip install -r requirements-dev.txt`, `python3 scripts/validate.py --root .`, and `python3 -m unittest discover -s tests`. Test modified runtime scripts from an unrelated working directory. Never include profiles, credentials, datasets, transcripts, account IDs, local inventory or private source diffs in a public PR.

Semantic versions: breaking contract/behavior change → major; compatible capability → minor; correction → patch. Same version with changed bytes blocks release. Automatic PRs require review; they never grant permission to install, merge or publish.
