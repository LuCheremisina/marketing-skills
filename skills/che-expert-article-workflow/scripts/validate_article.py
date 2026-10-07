#!/usr/bin/env python3
"""Validate draft, Tilda fragment, and publication-ready article artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_author(run_dir: Path, errors: list[str]) -> dict:
    path = run_dir / "author-profile.json"
    if not path.is_file():
        return {"subject": {"name": ""}, "claims": [], "prohibited_phrases": [], "usage_rules": {"max_numeric_claims_per_author_block": 2}}
    try:
        profile = load_json(path)
        if not isinstance(profile, dict) or not isinstance(profile.get("subject"), dict) or not isinstance(profile.get("claims"), list):
            raise ValueError("expected subject object and claims list")
        if profile.get("example_only") or profile.get("verification", {}).get("status") == "synthetic_example":
            raise ValueError("synthetic author profile cannot establish real authorship")
        profile.setdefault("usage_rules", {"max_numeric_claims_per_author_block": 2})
        if not profile["subject"].get("name"):
            raise ValueError("subject.name is required")
        return profile
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"invalid author-profile.json: {exc}")
        return {"subject": {"name": ""}, "claims": [], "prohibited_phrases": [], "usage_rules": {"max_numeric_claims_per_author_block": 2}}


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def strip_html(text: str) -> str:
    return normalized(re.sub(r"<[^>]+>", " ", text))


def is_https(value) -> bool:
    return isinstance(value, str) and urlparse(value).scheme == "https"


def graph_nodes(data) -> list[dict]:
    if isinstance(data, dict) and isinstance(data.get("@graph"), list):
        return [node for node in data["@graph"] if isinstance(node, dict)]
    return [data] if isinstance(data, dict) else []


def nodes_by_type(data, type_name: str) -> list[dict]:
    result = []
    for node in graph_nodes(data):
        node_type = node.get("@type")
        if node_type == type_name or (
            isinstance(node_type, list) and type_name in node_type
        ):
            result.append(node)
    return result


class H1Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_h1 = False
        self.current: list[str] = []
        self.h1: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "h1":
            self.in_h1 = True
            self.current = []

    def handle_data(self, data):
        if self.in_h1:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "h1" and self.in_h1:
            self.h1.append(normalized("".join(self.current)))
            self.in_h1 = False


def read_claims(path: Path, errors: list[str]) -> list[dict]:
    claims: list[dict] = []
    if not path.is_file():
        errors.append("missing claims.jsonl")
        return claims
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            claim = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"claims.jsonl:{line_no}: invalid JSON: {exc.msg}")
            continue
        claims.append(claim)
        base = ["claim_id", "text", "claim_kind", "materiality", "status"]
        for field in base:
            if not claim.get(field):
                errors.append(f"claims.jsonl:{line_no}: missing {field}")
        if claim.get("materiality") == "material":
            if claim.get("status") != "verified":
                errors.append(
                    f"claims.jsonl:{line_no}: material claim is not verified"
                )
            if claim.get("claim_kind") in {"external_fact", "author_fact"}:
                for field in [
                    "source_type",
                    "source_url",
                    "source_date",
                    "checked_at",
                    "locator",
                    "article_locator",
                ]:
                    if not claim.get(field):
                        errors.append(
                            f"claims.jsonl:{line_no}: material fact missing {field}"
                        )
                if claim.get("source_url") and not is_https(claim["source_url"]):
                    errors.append(
                        f"claims.jsonl:{line_no}: source_url must be https"
                    )
            if claim.get("claim_kind") == "external_fact":
                allowed_sources = {
                    "primary",
                    "official",
                    "original_research",
                    "authoritative",
                }
                if claim.get("source_type") not in allowed_sources:
                    errors.append(
                        f"claims.jsonl:{line_no}: weak source type for material external fact"
                    )
    return claims


def validate_author_text(text: str, author: dict, errors: list[str]) -> None:
    lowered = normalized(text).lower()
    for phrase in author.get("prohibited_phrases", []):
        if phrase.lower() in lowered:
            errors.append(f"prohibited author phrase: {phrase}")


def validate_draft(run_dir: Path, errors: list[str]):
    article_path = run_dir / "article.md"
    metadata_path = run_dir / "metadata.json"
    if not article_path.is_file():
        errors.append("missing article.md")
        article_text = ""
    else:
        article_text = article_path.read_text(encoding="utf-8")

    author = load_author(run_dir, errors)
    validate_author_text(article_text, author, errors)
    claims = read_claims(run_dir / "claims.jsonl", errors)

    if not metadata_path.is_file():
        errors.append("missing metadata.json")
        metadata = {}
    else:
        try:
            metadata = load_json(metadata_path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid metadata.json: {exc}")
            metadata = {}

    for field in [
        "article_id",
        "title",
        "description",
        "h1",
        "semantic_mode",
        "semantic_status",
        "content_type",
        "funnel_stage",
        "offer_key",
    ]:
        if not metadata.get(field):
            errors.append(f"metadata.json missing {field}")
    if metadata.get("claims_complete") is not True:
        errors.append("metadata.json claims_complete must be true")
    if any(
        claim.get("claim_kind") == "external_fact"
        and claim.get("materiality") == "material"
        for claim in claims
    ) and "источник" not in article_text.lower():
        errors.append("article.md needs a visible sources section")
    return metadata, claims


def extract_block(html: str, class_name: str) -> str:
    pattern = (
        r'<(?:aside|section|div)[^>]*class="[^"]*\b'
        + re.escape(class_name)
        + r'\b[^"]*"[^>]*>(.*?)</(?:aside|section|div)>'
    )
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return strip_html(match.group(1)) if match else ""


def validate_fragment(
    run_dir: Path, metadata: dict, claims: list[dict], errors: list[str]
) -> tuple[str, list[str]]:
    html_path = run_dir / "article.html"
    if not html_path.is_file():
        errors.append("missing article.html")
        return "", []
    html = html_path.read_text(encoding="utf-8")
    if re.search(r"<(?:html|head|meta)\b", html, re.IGNORECASE):
        errors.append("article.html must be a fragment without html/head/meta")
    if "{{" in html or "}}" in html:
        errors.append("article.html contains unresolved template placeholders")
    if re.search(r'class="[^"]*\barticle-cover\b', html):
        errors.append("cover must not be embedded in article fragment")

    parser = H1Parser()
    parser.feed(html)
    if len(parser.h1) != 1:
        errors.append(f"article.html must contain exactly one H1, got {len(parser.h1)}")
    elif metadata.get("h1") and parser.h1[0] != normalized(metadata["h1"]):
        errors.append("visible H1 does not match metadata.h1")

    manifest = load_json(SKILL_ROOT / "assets/component-manifest.json")
    allowed = set(manifest["allowed_classes"])
    actual: list[str] = []
    for class_value in re.findall(r'class="([^"]+)"', html):
        actual.extend(class_value.split())
    unknown = set(actual) - allowed
    if unknown:
        errors.append(f"unknown HTML classes: {sorted(unknown)}")
    for required in [
        "article-body",
        "article-header",
        "article-content",
        "article-author",
    ]:
        if required not in actual:
            errors.append(f"missing required HTML class: {required}")

    present_order = []
    for component in manifest["component_order"]:
        match = re.search(
            r'class="[^"]*\b' + re.escape(component) + r'\b[^"]*"',
            html,
        )
        if match:
            present_order.append((match.start(), component))
    if [item[1] for item in sorted(present_order)] != [
        item[1] for item in present_order
    ]:
        errors.append("components do not follow canonical order")

    author = load_author(run_dir, errors)
    author_text = extract_block(html, "article-author")
    if not author["subject"]["name"] or author["subject"]["name"] not in author_text:
        errors.append("visible author block is missing canonical author name")
    validate_author_text(author_text, author, errors)
    allowed_phrases = [
        phrase
        for claim in author["claims"]
        for phrase in claim.get("allowed_phrases", [])
    ]
    remainder = normalized(author_text)
    used_metrics = 0
    for phrase in sorted(allowed_phrases, key=len, reverse=True):
        if phrase in remainder:
            used_metrics += 1
            remainder = remainder.replace(phrase, "")
    if re.search(r"\d", remainder):
        errors.append("author block contains a numeric claim outside canonical phrases")
    if used_metrics > author["usage_rules"]["max_numeric_claims_per_author_block"]:
        errors.append("author block contains too many numeric proof claims")

    external_material = any(
        claim.get("claim_kind") == "external_fact"
        and claim.get("materiality") == "material"
        for claim in claims
    )
    has_sources = "article-sources" in actual
    if external_material and not has_sources:
        errors.append("visible sources component required for external material claims")
    return html, parser.h1


def validate_integrate(
    run_dir: Path,
    html: str,
    h1_values: list[str],
    metadata: dict,
    errors: list[str],
) -> None:
    for filename in ["schema.json", "integration-manifest.json", "article.css"]:
        if not (run_dir / filename).is_file():
            errors.append(f"missing {filename}")
    if errors:
        return

    schema = load_json(run_dir / "schema.json")
    integration = load_json(run_dir / "integration-manifest.json")
    required_meta = [
        "production_url",
        "canonical_url",
        "datePublished",
        "dateModified",
        "og_image_url",
    ]
    for field in required_meta:
        if not metadata.get(field):
            errors.append(f"metadata.json missing integrate field {field}")
    for field in ["production_url", "canonical_url", "og_image_url"]:
        if metadata.get(field) and not is_https(metadata[field]):
            errors.append(f"metadata.{field} must be https")
    if metadata.get("production_url") != metadata.get("canonical_url"):
        errors.append("production_url and canonical_url must match")
    if metadata.get("twitter_card") != "summary_large_image":
        errors.append("twitter_card must be summary_large_image")
    site_path = run_dir / "site-profile.json"
    try:
        site = load_json(site_path)
    except (OSError, ValueError):
        site = {}
    base_url = site.get("base_url", "")
    expected_language = site.get("language", "")
    if not is_https(base_url) or not expected_language:
        errors.append("site-profile.json requires https base_url and language")
    elif urlparse(metadata.get("production_url", "")).netloc != urlparse(base_url).netloc:
        errors.append("production_url host must match provided site profile")

    postings = nodes_by_type(schema, "BlogPosting")
    persons = nodes_by_type(schema, "Person")
    breadcrumbs = nodes_by_type(schema, "BreadcrumbList")
    if len(postings) != 1:
        errors.append(f"schema must contain one BlogPosting, got {len(postings)}")
        return
    posting = postings[0]
    for field in [
        "headline",
        "description",
        "datePublished",
        "dateModified",
        "mainEntityOfPage",
        "author",
        "image",
        "publisher",
        "inLanguage",
    ]:
        if not posting.get(field):
            errors.append(f"BlogPosting missing {field}")
    if h1_values and posting.get("headline") != h1_values[0]:
        errors.append("BlogPosting.headline does not match visible H1")
    if posting.get("description") != metadata.get("description"):
        errors.append("BlogPosting.description does not match metadata")
    if posting.get("mainEntityOfPage") != metadata.get("canonical_url"):
        errors.append("BlogPosting.mainEntityOfPage does not match canonical URL")
    if posting.get("image") != metadata.get("og_image_url"):
        errors.append("BlogPosting.image does not match OG image")
    if posting.get("inLanguage") != expected_language:
        errors.append("BlogPosting.inLanguage must match provided site profile")
    author = load_author(run_dir, errors)
    if not persons or not author["subject"]["name"] or persons[0].get("name") != author["subject"]["name"]:
        errors.append("schema needs canonical Person")
    if len(breadcrumbs) != 1:
        errors.append("schema needs one BreadcrumbList")

    visible_faq_count = len(
        re.findall(r'class="[^"]*\barticle-faq-item\b[^"]*"', html)
    )
    faq_nodes = nodes_by_type(schema, "FAQPage")
    if visible_faq_count == 0 and faq_nodes:
        errors.append("FAQPage exists without visible FAQ")
    if visible_faq_count > 0:
        if len(faq_nodes) != 1:
            errors.append("visible FAQ requires one FAQPage")
        else:
            schema_count = len(faq_nodes[0].get("mainEntity", []))
            if schema_count != visible_faq_count:
                errors.append("FAQPage question count does not match visible FAQ")

    if integration.get("status") != "ready_for_publish":
        errors.append("integration manifest status must be ready_for_publish")
    cover = integration.get("cover", {})
    if cover.get("status") != "ready":
        errors.append("cover status must be ready")
    if cover.get("unique_confirmed") is not True:
        errors.append("cover uniqueness must be confirmed")
    if cover.get("webp_url") != metadata.get("og_image_url"):
        errors.append("cover WebP URL must match metadata OG image")
    validation = integration.get("validation", {})
    if validation.get("draft") != "pass":
        errors.append("integration manifest must record draft validation pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument(
        "--stage",
        choices=["draft", "fragment", "integrate"],
        default="draft",
    )
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    errors: list[str] = []
    if not run_dir.is_dir():
        print(f"ERROR: run directory does not exist: {run_dir}")
        return 1

    metadata, claims = validate_draft(run_dir, errors)
    html = ""
    h1_values: list[str] = []
    if args.stage in {"fragment", "integrate"}:
        html, h1_values = validate_fragment(run_dir, metadata, claims, errors)
    if args.stage == "integrate":
        validate_integrate(run_dir, html, h1_values, metadata, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: {args.stage} contract validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
