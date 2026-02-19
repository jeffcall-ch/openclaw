#!/usr/bin/env python3
import argparse
import re
import sys
import time
from collections import deque
from html import unescape
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


def normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:")):
        return None

    absolute = urljoin(base_url, href)
    absolute, _ = urldefrag(absolute)

    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None

    # Normalize trailing slash except for root.
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    normalized = parsed._replace(path=path, params="", query=parsed.query, fragment="").geturl()
    return normalized


def is_same_domain(url: str, root_netloc: str) -> bool:
    return urlparse(url).netloc == root_netloc


def extract_main_container(soup: BeautifulSoup):
    # Prefer common doc-content containers.
    selectors = [
        "main",
        "article",
        "[role='main']",
        ".content",
        ".markdown",
        ".docs-content",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node
    return soup.body or soup


def clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_code_language(code_node) -> str:
    cls = " ".join(code_node.get("class", []))

    patterns = [
        r"language-([a-zA-Z0-9_+-]+)",
        r"lang-([a-zA-Z0-9_+-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, cls)
        if m:
            return m.group(1).lower()

    parent = code_node.parent
    if parent is not None:
        parent_cls = " ".join(parent.get("class", []))
        for pat in patterns:
            m = re.search(pat, parent_cls)
            if m:
                return m.group(1).lower()

    return ""


def extract_content_markdown(container) -> str:
    lines: list[str] = []
    emitted_code = set()

    # Capture headings/paragraph/list text and code blocks in DOM order.
    for node in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code", "blockquote"]):
        name = node.name

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(name[1])
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                lines.append(f"{'#' * min(level + 1, 6)} {text}")
            continue

        if name in {"p", "li", "blockquote"}:
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                prefix = "- " if name == "li" else "> " if name == "blockquote" else ""
                lines.append(f"{prefix}{text}")
            continue

        if name == "pre":
            code = node.get_text("\n", strip=False).strip("\n")
            if code:
                lang = ""
                code_child = node.find("code")
                if code_child:
                    lang = infer_code_language(code_child)
                fence = f"```{lang}" if lang else "```"
                lines.append(fence)
                lines.append(code)
                lines.append("```")
                emitted_code.add(id(node))
            continue

        if name == "code":
            if node.parent and node.parent.name == "pre":
                continue
            text = node.get_text("\n", strip=False).strip("\n")
            if text:
                lang = infer_code_language(node)
                fence = f"```{lang}" if lang else "```"
                lines.append(fence)
                lines.append(text)
                lines.append("```")

    # Compact repeated blank lines.
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result


def crawl(start_url: str, output_path: str, timeout: float) -> None:
    parsed_start = urlparse(start_url)
    if parsed_start.scheme not in {"http", "https"}:
        raise ValueError("start_url must begin with http:// or https://")

    root_netloc = parsed_start.netloc
    start_normalized = normalize_url(start_url, start_url)
    if not start_normalized:
        raise ValueError("Could not normalize start URL")

    queue = deque([start_normalized])
    visited = set()
    pages_written = 0
    words_processed = 0

    with requests.Session() as session, open(output_path, "w", encoding="utf-8") as out:
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; OpenClawDocsCrawler/1.0; "
                    "+https://docs.openclaw.ai/)"
                )
            }
        )

        while queue:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            try:
                resp = session.get(url, timeout=timeout)
                if "text/html" not in resp.headers.get("Content-Type", ""):
                    continue
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"[warn] Failed {url}: {exc}", file=sys.stderr)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            title_node = soup.find("title")
            title = clean_text(title_node.get_text(" ", strip=True)) if title_node else url

            # Remove obvious non-content regions.
            for selector in ["nav", "footer", "aside", "script", "style", "noscript"]:
                for elem in soup.select(selector):
                    elem.decompose()

            container = extract_main_container(soup)
            body_md = extract_content_markdown(container)

            out.write(f"# {title}\n")
            out.write(f"Source: {url}\n\n")
            if body_md:
                out.write(body_md)
                out.write("\n\n")
            else:
                out.write("[No extractable content found]\n\n")
            out.write("---\n\n")
            out.flush()

            pages_written += 1
            page_words = len(re.findall(r"\S+", body_md))
            words_processed += page_words
            print(
                f"[ok] pages={pages_written} words={words_processed} page_words={page_words} url={url}",
                flush=True,
            )

            for a in soup.find_all("a", href=True):
                nxt = normalize_url(url, a["href"])
                if not nxt:
                    continue
                if not is_same_domain(nxt, root_netloc):
                    continue
                if nxt not in visited:
                    queue.append(nxt)

            # No deliberate rate limit requested.
            time.sleep(0)

    print(
        f"Done. Wrote pages={pages_written} words={words_processed} to {output_path}",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl all pages/subpages under a docs domain and write consolidated markdown."
        )
    )
    parser.add_argument(
        "--start-url",
        default="https://docs.openclaw.ai/",
        help="Root URL to start crawling from (default: https://docs.openclaw.ai/)",
    )
    parser.add_argument(
        "--output",
        default="docs2.md",
        help="Output markdown file path (default: docs2.md)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds (default: 20)",
    )
    args = parser.parse_args()

    crawl(start_url=args.start_url, output_path=args.output, timeout=args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
