"""
Generic HTML preprocessor for product detail pages.

This module pulls generic, framework-level signals out of a raw HTML
document -- signals that are common across many e-commerce sites but are
encoded differently by each one's frontend stack:

  - schema.org structured data (<script type="application/ld+json">)
  - framework hydration state (window.__NEXT_DATA__, window.__INITIAL_STATE__,
    <script type="application/json" id="__NEXT_DATA__">, etc.) -- detected by
    a generic naming pattern (__SOME_NAME__), not any specific site's key.
  - <meta> tags (Open Graph, description, keywords, ...)
  - candidate image URLs from <img>/<source>/<link> and from any JSON blobs
  - cleaned, script/style-free visible text

None of this logic is specific to any single site: it looks for patterns
that are part of common web conventions (schema.org, Open Graph, the
`window.__X__` hydration convention, the HTML `srcset` spec) rather than
any one domain's markup.

The output is a bounded, structured `PreprocessedPage` that a downstream
LLM-based extraction step can consume to hydrate a `Product`.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Comment
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|gif|avif)(?:\?[^\s\"'<>]*)?$", re.IGNORECASE)
_STATE_VAR_RE = re.compile(r"window\.(__[A-Za-z0-9_]+?__)\s*=\s*(?=[\{\[])")
_JS_SCRIPT_TYPES = {None, "", "text/javascript", "application/javascript", "module"}


class PreprocessedPage(BaseModel):
    """Generic signals extracted from a single product detail page's HTML."""

    title: str | None = None
    meta_tags: dict[str, str] = Field(default_factory=dict)
    ld_json: list[Any] = Field(default_factory=list)
    state_blobs: dict[str, Any] = Field(default_factory=dict)
    image_urls: list[str] = Field(default_factory=list)
    text_content: str = ""

    def to_llm_document(self, max_text_chars: int = 20_000, max_json_chars: int = 250_000) -> str:
        """Render a bounded, human/LLM-readable document from the extracted signals."""

        def _dump(obj: Any) -> str:
            text = json.dumps(obj, indent=2, ensure_ascii=False)
            if len(text) > max_json_chars:
                text = text[:max_json_chars] + "\n... [truncated]"
            return text

        parts: list[str] = []
        if self.title:
            parts.append(f"TITLE: {self.title}")
        if self.meta_tags:
            parts.append("META TAGS:\n" + _dump(self.meta_tags))
        if self.ld_json:
            parts.append("LD+JSON (schema.org structured data):\n" + _dump(self.ld_json))
        if self.state_blobs:
            # Truncate each blob independently (rather than the combined dict) so one
            # huge blob (e.g. a framework's full page state) can't starve out a smaller
            # one that happens to hold the actual product/SKU data.
            blob_sections = [f"--- {name} ---\n{_dump(blob)}" for name, blob in self.state_blobs.items()]
            parts.append("EMBEDDED APPLICATION STATE:\n" + "\n\n".join(blob_sections))
        if self.image_urls:
            parts.append("CANDIDATE IMAGE URLS:\n" + "\n".join(self.image_urls))
        if self.text_content:
            text = self.text_content
            if len(text) > max_text_chars:
                text = text[:max_text_chars] + " ... [truncated]"
            parts.append("VISIBLE PAGE TEXT:\n" + text)
        return "\n\n".join(parts)


def preprocess_html(html: str) -> PreprocessedPage:
    """Extract generic structured/text signals from a raw product page HTML string."""
    soup = BeautifulSoup(html, "lxml")

    title = _extract_title(soup)
    meta_tags = _extract_meta_tags(soup)
    ld_json = _extract_ld_json(soup)
    state_blobs = _extract_state_blobs(soup)
    image_urls = _extract_images(soup, json_blobs=[*ld_json, state_blobs])
    text_content = _extract_text_content(soup)

    return PreprocessedPage(
        title=title,
        meta_tags=meta_tags,
        ld_json=ld_json,
        state_blobs=state_blobs,
        image_urls=image_urls,
        text_content=text_content,
    )


def _extract_title(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None


def _extract_meta_tags(soup: BeautifulSoup) -> dict[str, str]:
    tags: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        key = meta.get("property") or meta.get("name")
        content = meta.get("content")
        if key and content:
            tags[key] = content
    return tags


def _extract_ld_json(soup: BeautifulSoup) -> list[Any]:
    results: list[Any] = []
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or script.get_text()
        if not text or not text.strip():
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.debug("Skipping malformed ld+json block")
            continue
        if isinstance(parsed, list):
            results.extend(parsed)
        else:
            results.append(parsed)
    return results


def _extract_state_blobs(soup: BeautifulSoup) -> dict[str, Any]:
    """Find framework hydration state, whether embedded as a `window.__X__ = {...}`
    assignment inside a <script> or as a dedicated <script type="application/json">
    block. Matched purely by the generic `__NAME__` naming convention, not any
    specific site's variable name.
    """
    blobs: dict[str, Any] = {}

    for script in soup.find_all("script"):
        script_type = script.get("type")
        text = script.string or script.get_text()
        if not text or not text.strip():
            continue

        if script_type == "application/json":
            name = script.get("id") or f"json_script_{len(blobs)}"
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            _keep_richest(blobs, name, parsed)
            continue

        if script_type not in _JS_SCRIPT_TYPES:
            continue

        for match in _STATE_VAR_RE.finditer(text):
            name = match.group(1)
            blob_text = _scan_balanced(text, match.end())
            if blob_text is None:
                continue
            try:
                parsed = json.loads(blob_text)
            except json.JSONDecodeError:
                continue
            _keep_richest(blobs, name, parsed)

    return blobs


def _keep_richest(blobs: dict[str, Any], name: str, parsed: Any) -> None:
    """A variable may be assigned an empty placeholder before its real value
    (e.g. `window.__X__ = window.__X__ || {}` followed by the real payload
    later); keep whichever parse is larger."""
    if name not in blobs or len(json.dumps(parsed)) > len(json.dumps(blobs[name])):
        blobs[name] = parsed


def _scan_balanced(text: str, start: int) -> str | None:
    """Scan a balanced {...} or [...] region starting at `start`, respecting
    JS string literals, and return the matched substring (inclusive)."""
    if start >= len(text) or text[start] not in "{[":
        return None

    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string: str | None = None
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_string is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue

        if ch in "\"'":
            in_string = ch
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _extract_images(soup: BeautifulSoup, json_blobs: list[Any]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []

    def add(url: str | None) -> None:
        if url and url not in seen and not url.startswith("data:"):
            seen.add(url)
            urls.append(url)

    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-zoom-image"):
            add(img.get(attr))
        for attr in ("srcset", "data-srcset"):
            add(_best_from_srcset(img.get(attr)))

    for source in soup.find_all("source"):
        add(_best_from_srcset(source.get("srcset")))

    for link in soup.find_all("link", attrs={"as": "image"}):
        add(link.get("href"))

    for blob in json_blobs:
        for s in _walk_strings(blob):
            if s.startswith("http") and _IMAGE_EXT_RE.search(s):
                add(s)

    return urls


def _best_from_srcset(srcset: str | None) -> str | None:
    """Pick the highest-resolution candidate from a `srcset` attribute, per
    the standard `url descriptor` syntax (e.g. "a.jpg 400w, b.jpg 800w")."""
    if not srcset:
        return None

    best_url: str | None = None
    best_weight = -1.0
    for candidate in srcset.split(","):
        parts = candidate.strip().split()
        if not parts:
            continue
        url = parts[0]
        weight = 0.0
        if len(parts) > 1 and parts[1] and parts[1][-1] in "wx":
            try:
                weight = float(parts[1][:-1])
            except ValueError:
                weight = 0.0
        if weight >= best_weight:
            best_weight = weight
            best_url = url
    return best_url


def _walk_strings(obj: Any):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def _extract_text_content(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    path = sys.argv[1] if len(sys.argv) > 1 else "data/nike.html"
    with open(path, encoding="utf-8") as f:
        html = f.read()

    page = preprocess_html(html)
    print(f"title: {page.title}")
    print(f"meta_tags: {len(page.meta_tags)} keys")
    print(f"ld_json: {len(page.ld_json)} block(s)")
    print(f"state_blobs: {list(page.state_blobs.keys())}")
    print(f"image_urls: {len(page.image_urls)} candidate(s)")
    print(f"text_content: {len(page.text_content)} chars")
    print()
    print("--- sample image urls ---")
    for u in page.image_urls[:10]:
        print(" ", u)
