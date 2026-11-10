#!/usr/bin/env python3
"""Validate the public content contract before generating or publishing the site."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def load_json(path: Path, issues: list[str]) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"{path.name}: invalid JSON ({exc})")
        return {}


def validate(root: Path) -> list[str]:
    issues: list[str] = []
    data_dir = root / "data"
    site = load_json(data_dir / "site-content.json", issues)
    scholar = load_json(data_dir / "scholar-2026-11-10.json", issues)
    metadata = load_json(data_dir / "publication-metadata.json", issues)
    media = load_json(data_dir / "media-links-2026-11-10.json", issues)

    expected_areas = {"foundation", "safety", "knowledge"}
    areas = site.get("areas", [])
    area_ids = {item.get("id") for item in areas}
    if area_ids != expected_areas:
        issues.append(f"site-content.json: research areas mismatch: {sorted(area_ids)}")
    for item in areas:
        for field in ("title", "text"):
            if not isinstance(item.get(field), dict) or not item[field].get("zh") or not item[field].get("en"):
                issues.append(f"area {item.get('id')}: missing bilingual {field}")
    for item in site.get("profile", {}).get("services", []):
        for field in ("title", "term", "source"):
            if not isinstance(item.get(field), dict) or not item[field].get("zh") or not item[field].get("en"):
                issues.append(f"service {item.get('id')}: missing bilingual {field}")

    projects = site.get("projects", [])
    detailed = {item.get("id") for item in projects if item.get("detail", True)}
    if detailed != {"llm-safety", "rag-knowledge", "tinyr1", "memory-agents"}:
        issues.append(f"site-content.json: detail projects mismatch: {sorted(detailed)}")
    representative = {item.get("id") for item in projects if not item.get("detail", True)}
    if not {"xiaobei-assistant", "ai-house-tour"}.issubset(representative):
        issues.append("site-content.json: missing Beike/Rushi representative work cards")
    if len(site.get("patentThemes", [])) != 4:
        issues.append("site-content.json: patentThemes must contain four public categories")
    theme_ids = {item.get("id") for item in site.get("patentThemes", [])}
    for item in site.get("patents", []):
        if item.get("themeId") not in theme_ids:
            issues.append(f"patent {item.get('id')}: unknown themeId")
        if not item.get("title") or not item.get("titleEn"):
            issues.append(f"patent {item.get('id')}: missing bilingual title")
    for item in projects:
        for field in ("title", "summary"):
            if not isinstance(item.get(field), dict) or not item[field].get("zh") or not item[field].get("en"):
                issues.append(f"project {item.get('id')}: missing bilingual {field}")
        if item.get("detail", True):
            for field in ("problem", "role", "approach", "result", "evidence", "boundary"):
                if not isinstance(item.get(field), dict) or not item[field].get("zh") or not item[field].get("en"):
                    issues.append(f"project {item.get('id')}: missing bilingual {field}")
            if "relatedMedia" not in item or "images" not in item:
                issues.append(f"project {item.get('id')}: missing relatedMedia/images data")

    paper_rows = scholar.get("papers", [])
    if len(paper_rows) != 30:
        issues.append(f"scholar snapshot: expected 30 papers, got {len(paper_rows)}")
    paper_titles = {paper.get("title") for paper in paper_rows}
    if paper_titles != set(metadata):
        issues.append("publication metadata keys do not match the Scholar snapshot")
    for title, item in metadata.items():
        if item.get("status") not in {"published", "accepted", "preprint", "technical-report", "submitted", "unverified"}:
            issues.append(f"publication {title}: unsupported status {item.get('status')}")
        if not item.get("evidence"):
            issues.append(f"publication {title}: missing evidence")

    expected_videos = {
        "BV1dA7Y6cEgX": "拆AI共识：Mythos被禁背后，为什么最强AI反而更危险！",
        "BV19SKQ6HEau": "【精华版】AI越强，为什么大家反而开始担心了？｜Mythos争议背后的AI安",
    }
    video_items = [item for item in media.get("items", []) if item.get("kind") == "video" and item.get("publish")]
    for video_id, title in expected_videos.items():
        found = [item for item in video_items if video_id in item.get("url", "")]
        if len(found) != 1 or found[0].get("title") != title or found[0].get("date") is not None:
            issues.append(f"video {video_id}: title, URL, or undated contract mismatch")
    if len(video_items) != len(expected_videos):
        issues.append(f"media snapshot: expected {len(expected_videos)} published videos, got {len(video_items)}")
    media_items = media.get("items", [])
    media_ids = [item.get("id") for item in media_items]
    if any(not item_id for item_id in media_ids) or len(media_ids) != len(set(media_ids)):
        issues.append("media snapshot: every item needs a unique stable id")
    for item in site.get("media", []) + site.get("talks", []):
        if not item.get("id") or "sourceDate" not in item or "featured" not in item:
            issues.append("site-content media/talk item is missing id, sourceDate, or featured")

    for path in sorted(root.glob("**/index.html")):
        content = path.read_text()
        for match in re.finditer(r'<a\b[^>]*href="(https?://[^" ]+)"[^>]*>', content):
            tag = match.group(0)
            if 'target="_blank"' not in tag or 'rel="noopener"' not in tag:
                issues.append(f"{path.relative_to(root)}: external link lacks target/rel")
        for pattern in (r"身份证", r"员工号", r"缴费", r"推荐信", r"192\.168\.", r"10\.\d{1,3}\."):
            if re.search(pattern, content, flags=re.IGNORECASE):
                issues.append(f"{path.relative_to(root)}: private content pattern {pattern}")

    return sorted(set(issues))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues = validate(root)
    if issues:
        print("\n".join(f"- {issue}" for issue in issues))
        return 1
    print("Content and generated-page contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
