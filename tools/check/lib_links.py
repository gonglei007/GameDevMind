"""Local Markdown/HTML link parsing shared by the offline checks."""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from lib_config import ROOT

CONTENT_DIRS = ("mds", "cases", "ai-cases", "code", "docs", "tools", "nav", ".github")
SKIP_DIRS = {"node_modules", "__pycache__", "build", "build_debug", "build_release", ".git", "venv", ".venv"}


@dataclass(frozen=True)
class Link:
    target: str
    line: int
    image: bool = False


def content_files(root: Path = ROOT) -> list[Path]:
    files = list(root.glob("*.md"))
    for name in CONTENT_DIRS:
        for p in (root / name).rglob("*"):
            if p.is_file() and p.suffix in {".md", ".html"} and not (set(p.relative_to(root).parts) & SKIP_DIRS):
                files.append(p)
    return sorted(set(files))


def visible_text(text: str) -> str:
    """Mask examples/comments without changing offsets or line numbers."""
    def blank(match: re.Match) -> str:
        return re.sub(r"[^\n]", " ", match.group())

    text = re.sub(r"<!--.*?-->|<style\b[^>]*>.*?</style>", blank, text, flags=re.S | re.I)
    text = re.sub(r"(<script\b[^>]*>)(.*?)(</script>)",
                  lambda m: m.group(1) + re.sub(r"[^\n]", " ", m.group(2)) + m.group(3), text, flags=re.S | re.I)
    lines = text.splitlines(keepends=True)
    fence = None
    for i, line in enumerate(lines):
        # Fences can appear in quoted examples as well.
        marker = re.match(r"^(?:\s*>)*\s*(`{3,}|~{3,})", line)
        if marker and fence is None:
            fence = marker.group(1)
            lines[i] = re.sub(r"[^\n]", " ", line)
        elif fence:
            lines[i] = re.sub(r"[^\n]", " ", line)
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
    return "".join(lines)


class Attributes(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[Link] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if not value:
                continue
            if key == "id" or (tag == "a" and key == "name"):
                self.ids.add(value)
            if (key == "href" and tag in {"a", "link"}) or (key == "src" and tag in {"img", "script", "source", "video", "audio"}):
                self.links.append(Link(value, self.getpos()[0], tag == "img"))


def links_in(text: str) -> list[Link]:
    visible = visible_text(text)
    # Inline code often contains example links; leave their newlines in place.
    visible = re.sub(r"(`+)[^`\n]*?\1", lambda m: " " * len(m.group()), visible)
    links: list[Link] = []
    for match in re.finditer(r"(!?)\[[^\]\n]*\]\(", visible):
        start = match.end()
        end = start
        depth = 1
        in_angle = start < len(visible) and visible[start] == "<"
        while end < len(visible):
            ch = visible[end]
            if ch == "\\":
                end += 2
                continue
            if ch == "\n":
                break
            if ch == "(" and not in_angle:
                depth += 1
            elif ch == ")" and not in_angle:
                depth -= 1
                if depth == 0:
                    break
            elif ch == ">":
                in_angle = False
            end += 1
        if depth != 0:
            continue
        body = visible[start:end].strip()
        if body.startswith("<"):
            target = body[1:body.index(">")]
        else:
            target = re.split(r"\s+[\"']", body, maxsplit=1)[0]
        target = re.sub(r"\\([()\[\] ])", r"\1", target)
        links.append(Link(unescape(target), visible.count("\n", 0, match.start()) + 1, bool(match.group(1))))

    definitions = {m.group(1).casefold(): (m.group(2) or m.group(3)) for m in re.finditer(
        r"^\s{0,3}\[([^\]]+)\]:\s*(?:<([^>]+)>|(\S+))", visible, re.M)}
    for m in re.finditer(r"(!?)\[([^\]\n]+)\](?:\[([^\]\n]*)\])?(?![(:])", visible):
        label = (m.group(3) or m.group(2)).casefold()
        if label in definitions:
            links.append(Link(definitions[label], visible.count("\n", 0, m.start()) + 1, bool(m.group(1))))

    html = Attributes()
    html.feed(visible)
    links.extend(html.links)
    return links


def local_target(source: Path, target: str, root: Path = ROOT) -> tuple[Path, str] | None:
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    dest = source if not path else (root / path.lstrip("/") if path.startswith("/") else source.parent / path)
    return dest.resolve(), unquote(parts.fragment)


def anchors_in(text: str) -> set[str]:
    visible = visible_text(text)
    html = Attributes()
    html.feed(visible)
    anchors = set(html.ids)
    counts: dict[str, int] = {}
    for m in re.finditer(r"^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$", visible, re.M):
        title = re.sub(r"<[^>]+>", "", m.group(1))
        title = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", title)
        title = unescape(title).lower().replace("`", "")
        slug = "".join(ch for ch in title if ch in "-_ " or not unicodedata.category(ch).startswith(("P", "S", "C")))
        slug = slug.replace(" ", "-")
        count = counts.get(slug, 0)
        anchor = f"{slug}-{count}" if count else slug
        while anchor in anchors:
            count += 1
            anchor = f"{slug}-{count}"
        counts[slug] = count + 1
        anchors.add(anchor)
    return anchors


def check_links(files: list[Path], root: Path = ROOT) -> tuple[list[str], int]:
    errors: list[str] = []
    checked = 0
    anchor_cache: dict[Path, set[str]] = {}
    for source in files:
        text = source.read_text(encoding="utf-8-sig")
        for link in links_in(text):
            result = local_target(source, link.target, root)
            if result is None:
                continue
            checked += 1
            dest, fragment = result
            label = f"{source.relative_to(root)}:{link.line}: {link.target}"
            if not dest.is_relative_to(root.resolve()) or not dest.exists():
                errors.append(f"{label} — missing local target")
            elif fragment and not link.image and dest.suffix in {".md", ".html"}:
                if dest not in anchor_cache:
                    anchor_cache[dest] = anchors_in(dest.read_text(encoding="utf-8-sig"))
                if fragment not in anchor_cache[dest]:
                    errors.append(f"{label} — missing anchor #{fragment}")
    return errors, checked
