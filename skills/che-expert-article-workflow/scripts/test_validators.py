#!/usr/bin/env python3
"""Smoke-test validators with valid and intentionally invalid artifacts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_article.py"


def write_json(path: Path, data) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(stage: str, run_dir: Path, expect_success: bool) -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), str(run_dir), "--stage", stage],
        text=True,
        capture_output=True,
        check=False,
    )
    success = completed.returncode == 0
    if success != expect_success:
        print(completed.stdout)
        print(completed.stderr)
        raise AssertionError(
            f"stage={stage} expected success={expect_success}, got {success}"
        )


def build_valid_run(run_dir: Path) -> None:
    write_json(run_dir / "author-profile.json", {"subject": {"name": "Алексей Пример"}, "claims": [], "prohibited_phrases": [], "usage_rules": {"max_numeric_claims_per_author_block": 2}, "verification": {"status": "test_fixture"}})
    write_json(run_dir / "site-profile.json", {"base_url": "https://example.com", "language": "ru-RU"})
    h1 = "Как проверить AI-пилот до масштабирования"
    url = "https://example.com/blog/ai-pilot-check"
    image = "https://example.com/assets/ai-pilot-check-cover.webp"
    article = f"""# {h1}

Короткий доказательный материал.

## Источники

- [Официальный отчёт](https://example.com/report)
"""
    (run_dir / "article.md").write_text(article, encoding="utf-8")
    claim = {
        "claim_id": "C-001",
        "text": "Внешний проверяемый факт.",
        "claim_kind": "external_fact",
        "fact_type": "product_capability",
        "materiality": "material",
        "status": "verified",
        "source_type": "official",
        "source_url": "https://example.com/report",
        "source_date": "2026-07-01",
        "checked_at": "2026-07-30",
        "locator": "Section 2",
        "article_locator": "## Источники",
    }
    (run_dir / "claims.jsonl").write_text(
        json.dumps(claim, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "article_id": "ai-pilot-check",
        "title": h1,
        "description": "Проверка AI-пилота: доказательства, ограничения и критерии масштабирования.",
        "h1": h1,
        "production_url": url,
        "canonical_url": url,
        "datePublished": "2026-07-30T10:00:00+07:00",
        "dateModified": "2026-07-30T10:00:00+07:00",
        "og_image_url": image,
        "twitter_card": "summary_large_image",
        "semantic_mode": "optional",
        "semantic_status": "available",
        "claims_complete": True,
        "content_type": "research_implementation",
        "funnel_stage": "consideration",
        "offer_key": "none",
    }
    write_json(run_dir / "metadata.json", metadata)

    html = f"""<article class="article-body" data-article-id="ai-pilot-check">
<header class="article-header">
<p class="article-kicker">AI и управление</p>
<h1 class="article-title">{h1}</h1>
<p class="article-lede">Сначала критерии решения, затем масштабирование.</p>
</header>
<section class="article-direct-answer"><h2 class="article-section-title">Коротко</h2><p>Пилот готов к росту только после проверки эффекта и ограничений.</p></section>
<div class="article-content"><section class="article-section"><h2 class="article-section-title">Что проверить</h2><p>Эффект, данные и владельца решения.</p></section></div>
<section class="article-sources"><h2 class="article-section-title">Источники</h2><ol class="article-source-list"><li class="article-source-item"><a href="https://example.com/report">Официальный отчёт</a></li></ol></section>
<aside class="article-author"><p class="article-author-name">Алексей Пример</p><p class="article-author-role">Стратегический маркетолог, консультант, fractional CMO</p></aside>
</article>
"""
    (run_dir / "article.html").write_text(html, encoding="utf-8")
    shutil.copy2(ROOT / "assets/article.css", run_dir / "article.css")
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": h1,
                "description": metadata["description"],
                "datePublished": metadata["datePublished"],
                "dateModified": metadata["dateModified"],
                "mainEntityOfPage": url,
                "author": {
                    "@id": "https://example.com/author/example-author/#person"
                },
                "image": image,
                "publisher": {
                    "@type": "Organization",
                    "name": "Проекты Example Brand",
                },
                "inLanguage": "ru-RU",
            },
            {
                "@type": "Person",
                "@id": "https://example.com/author/example-author/#person",
                "name": "Алексей Пример",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Блог",
                        "item": "https://example.com/blog",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": h1,
                        "item": url,
                    },
                ],
            },
        ],
    }
    write_json(run_dir / "schema.json", schema)
    integration = {
        "contract_version": "1.0.0",
        "article_id": "ai-pilot-check",
        "status": "ready_for_publish",
        "cover": {
            "status": "ready",
            "png_url": "https://example.com/assets/ai-pilot-check-cover.png",
            "webp_url": image,
            "unique_confirmed": True,
        },
        "validation": {
            "draft": "pass",
            "fragment": "pass",
            "integrate": "running",
            "production_smoke": "not_run",
        },
    }
    write_json(run_dir / "integration-manifest.json", integration)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="article-validator-") as tmp:
        valid = Path(tmp) / "valid"
        valid.mkdir()
        build_valid_run(valid)
        run("draft", valid, True)
        run("fragment", valid, True)
        run("integrate", valid, True)

        bad_author = Path(tmp) / "bad-author"
        shutil.copytree(valid, bad_author)
        html_path = bad_author / "article.html"
        html_path.write_text(
            html_path.read_text(encoding="utf-8").replace(
                "Стратегический маркетолог, консультант, fractional CMO",
                "Стратегический маркетолог, 16 лет в digital",
            ),
            encoding="utf-8",
        )
        run("fragment", bad_author, False)

        bad_faq = Path(tmp) / "bad-faq"
        shutil.copytree(valid, bad_faq)
        html_path = bad_faq / "article.html"
        html_path.write_text(
            html_path.read_text(encoding="utf-8").replace(
                '<aside class="article-author">',
                '<section class="article-faq"><div class="article-faq-item">'
                '<h3 class="article-faq-question">Вопрос?</h3>'
                '<div class="article-faq-answer">Ответ.</div></div></section>'
                '<aside class="article-author">',
            ),
            encoding="utf-8",
        )
        run("integrate", bad_faq, False)

        missing_profile = Path(tmp) / "missing-profile"
        shutil.copytree(valid, missing_profile)
        (missing_profile / "author-profile.json").unlink()
        run("fragment", missing_profile, False)
        synthetic_profile = Path(tmp) / "synthetic-profile"
        shutil.copytree(valid, synthetic_profile)
        write_json(synthetic_profile / "author-profile.json", {"subject": {"name": "Алексей Пример"}, "claims": [], "example_only": True})
        run("fragment", synthetic_profile, False)
        foreign_host = Path(tmp) / "foreign-host"
        shutil.copytree(valid, foreign_host)
        write_json(foreign_host / "site-profile.json", {"base_url": "https://another.example", "language": "ru-RU"})
        run("integrate", foreign_host, False)
        other_language = Path(tmp) / "other-language"
        shutil.copytree(valid, other_language)
        write_json(other_language / "site-profile.json", {"base_url": "https://example.com", "language": "en-US"})
        run("integrate", other_language, False)
    print("PASS: validator smoke tests (9 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
