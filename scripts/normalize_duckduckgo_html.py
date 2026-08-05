#!/usr/bin/env python3
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

BASE = "https://html.duckduckgo.com"


def fetch(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=30) as res:
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset, errors="replace")


def absolutize(url: str) -> str:
    if not url or url.startswith(("data:", "mailto:", "javascript:", "#")):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE + url
    return url


def unwrap_ddg(url: str) -> str:
    url = absolutize(url)
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url
    if not (parsed.path.rstrip("/") == "/l" or parsed.path.startswith("/l/")):
        return url
    target = parse_qs(parsed.query).get("uddg", [None])[0]
    if not target:
        return url
    return unquote(target)


def rewrite_attr(match: re.Match) -> str:
    attr, quote, value = match.group(1), match.group(2), match.group(3)
    fixed = unwrap_ddg(unescape(value))
    return f"{attr}={quote}{fixed}{quote}"


def inline_css(match: re.Match) -> str:
    tag = match.group(0)
    href_match = re.search(r'href=(["\'])(.*?)\1', tag, flags=re.IGNORECASE | re.DOTALL)
    if not href_match:
        return tag

    css_url = href_match.group(2)
    try:
        css = fetch(css_url)

        def fix_css_url(m: re.Match) -> str:
            inner = m.group(1).strip(" \"'")
            return f"url({absolutize(urljoin(css_url, inner))})"

        css = re.sub(r"url\(([^)]+)\)", fix_css_url, css)
        return f"<style>/* inlined from {css_url} */\n{css}\n</style>"
    except Exception as exc:
        print(f"Warning: failed to inline CSS {css_url}: {exc}", file=sys.stderr)
        return tag


def normalize(html: str) -> str:
    html = re.sub(
        r'\b(href|src|action|poster)=(["\'])(.*?)\2',
        rewrite_attr,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>',
        inline_css,
        html,
        flags=re.IGNORECASE,
    )
    if "charset=" not in html[:500].lower():
        html = html.replace("<head>", '<head>\n  <meta charset="UTF-8" />', 1)
    return html


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.html> <output.html>", file=sys.stderr)
        sys.exit(1)

    raw_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    html = raw_path.read_text(encoding="utf-8", errors="replace")
    out_path.write_text(normalize(html), encoding="utf-8")
    print(f"Normalized HTML written to {out_path}")


if __name__ == "__main__":
    main()
