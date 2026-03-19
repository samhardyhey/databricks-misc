"""
Build a markdown digest from fetched Medium article JSON for internal policy notes.

Reads RSS-derived summaries (HTML), extracts list items as candidate tips, and emits
plain-text excerpts. Does not call the network.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger


def _strip_html_to_text(html: str, max_paragraphs: int = 12) -> str:
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    parts: list[str] = []
    for el in soup.find_all(["p", "h3", "h4"]):
        t = el.get_text(" ", strip=True)
        if t:
            parts.append(t)
        if len(parts) >= max_paragraphs:
            break
    if not parts:
        return soup.get_text(" ", strip=True)
    return "\n\n".join(parts)


def _list_bullets(html: str) -> list[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    for li in soup.find_all("li"):
        t = " ".join(li.stripped_strings)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 2:
            out.append(t)
    # de-dupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for b in out:
        if b not in seen:
            seen.add(b)
            unique.append(b)
    return unique


def _is_databricks_focused(tags: list[str], title: str, plain: str) -> bool:
    blob = f"{title} {' '.join(tags)} {plain[:2000]}".lower()
    return "databricks" in blob


def _load_articles(articles_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(articles_dir.glob("*.json"))
    articles: list[dict[str, Any]] = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            articles.append(json.load(f))
    return articles


def build_digest_markdown(articles: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append("# Databricks / MLOps practice digest (Marvelous MLOps source)")
    lines.append("")
    lines.append(
        "Auto-generated from `sources/medium/content/articles/*.json`. "
        "Use alongside originals on Medium; promote stable guidance into repo docs and Cursor rules."
    )
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append("")

    dab_focus: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []

    for a in articles:
        summary_html = a.get("summary") or ""
        plain = _strip_html_to_text(summary_html)
        tags = a.get("tags") or []
        title = a.get("title") or "(untitled)"
        if _is_databricks_focused(tags, title, plain):
            dab_focus.append(a)
        else:
            other.append(a)

    def emit_section(heading: str, subset: list[dict[str, Any]]) -> None:
        lines.append(f"## {heading}")
        lines.append("")
        if not subset:
            lines.append("_No entries in this section._")
            lines.append("")
            return
        for a in subset:
            title = a.get("title") or "(untitled)"
            url = a.get("url") or ""
            author = a.get("author") or ""
            published = a.get("published") or ""
            tags = a.get("tags") or []
            reading = a.get("reading_time") or ""
            summary_html = a.get("summary") or ""
            plain = _strip_html_to_text(summary_html)
            bullets = _list_bullets(summary_html)

            lines.append(f"### {title}")
            lines.append("")
            if url:
                lines.append(f"- **URL:** {url}")
            if author:
                lines.append(f"- **Author:** {author}")
            if published:
                lines.append(f"- **Published:** {published}")
            if reading:
                lines.append(f"- **Reading time:** {reading}")
            if tags:
                lines.append(f"- **Tags:** {', '.join(tags)}")
            lines.append("")
            if bullets:
                lines.append("**Extracted list items (candidate tips):**")
                lines.append("")
                for b in bullets[:40]:
                    lines.append(f"- {b}")
                if len(bullets) > 40:
                    lines.append(f"- _… {len(bullets) - 40} more list items omitted_")
                lines.append("")
            lines.append("**Summary excerpt:**")
            lines.append("")
            excerpt = plain[:2500] + ("…" if len(plain) > 2500 else "")
            lines.append(excerpt or "_No plain-text excerpt._")
            lines.append("")
            lines.append("---")
            lines.append("")

    emit_section("Databricks-focused (tag/title/text match)", dab_focus)
    emit_section("Other Marvelous MLOps articles", other)
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    root = Path(__file__).resolve().parent
    articles_dir = root / "sources" / "medium" / "content" / "articles"
    out_dir = root / "insights"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "databricks_practice_digest.md"

    if not articles_dir.is_dir():
        logger.error(f"Missing directory: {articles_dir} — run fetch_medium.py first")
        return

    articles = _load_articles(articles_dir)
    if not articles:
        logger.error("No article JSON files found.")
        return

    md = build_digest_markdown(articles)
    out_file.write_text(md, encoding="utf-8")
    logger.info(f"Wrote {out_file} ({len(articles)} articles)")


if __name__ == "__main__":
    main()
