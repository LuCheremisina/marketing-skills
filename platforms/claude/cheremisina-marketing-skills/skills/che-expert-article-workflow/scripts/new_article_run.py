#!/usr/bin/env python3
"""Create a non-passing article run scaffold from the canonical assets."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--h1", required=True)
    parser.add_argument("--content-type", default="author_framework")
    parser.add_argument(
        "--semantic-mode",
        choices=["required", "optional", "not_needed"],
        default="optional",
    )
    args = parser.parse_args()

    run_dir = args.output_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    for source, target in [
        ("article-fragment.html", "article.html"),
        ("article.css", "article.css"),
        ("integration-manifest.example.json", "integration-manifest.json"),
        ("schema.example.json", "schema.json"),
        ("run-manifest.example.json", "run-manifest.json"),
    ]:
        shutil.copy2(ROOT / "assets" / source, run_dir / target)

    metadata = json.loads(
        (ROOT / "assets/metadata.example.json").read_text(encoding="utf-8")
    )
    metadata.update(
        {
            "article_id": args.article_id,
            "title": args.h1,
            "h1": args.h1,
            "content_type": args.content_type,
            "semantic_mode": args.semantic_mode,
        }
    )
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "article.md").write_text(
        f"# {args.h1}\n\nTODO: подготовить доказательный draft.\n",
        encoding="utf-8",
    )
    (run_dir / "article_brief.md").write_text(
        f"# Brief: {args.h1}\n\n- article_id: `{args.article_id}`\n",
        encoding="utf-8",
    )
    (run_dir / "claims.jsonl").write_text("", encoding="utf-8")
    manifest = load_json(run_dir / "run-manifest.json")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest.update(
        {
            "article_id": args.article_id,
            "content_type": args.content_type,
            "created_at": now,
            "updated_at": now,
        }
    )
    (run_dir / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created scaffold: {run_dir}")
    print("Expected initial state: validators fail until evidence and content are complete.")
    return 0


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
