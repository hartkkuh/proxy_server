#!/usr/bin/env python3
"""Search DuckDuckGo and save a normalized HTML page of the results."""

from __future__ import annotations

import re
import sys
from html import escape, unescape
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen

from normalize_duckduckgo_html import normalize

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HTML_BASE = "https://html.duckduckgo.com"
TYPE_LABELS = {
    "web": "אינטרנט",
    "images": "תמונות",
    "videos": "וידאו",
    "news": "חדשות",
}


def http_get(url: str, accept: str = "*/*") -> str:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Referer": "https://duckduckgo.com/",
        },
    )
    with urlopen(req, timeout=45) as res:
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset, errors="replace")


def absolutize(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    return url


def unwrap_ddg(url: str) -> str:
    url = absolutize(url)
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url
    if not (parsed.path.rstrip("/") == "/l" or parsed.path.startswith("/l/")):
        return url
    target = parse_qs(parsed.query).get("uddg", [None])[0]
    return unquote(target) if target else url


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return unescape(str(value)).strip()


def fetch_web_html(question: str) -> str:
    url = f"{HTML_BASE}/html/?q={quote(question)}"
    return normalize(http_get(url, accept="text/html,application/xhtml+xml"))


def fetch_ddgs_results(question: str, search_type: str) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS  # type: ignore

    ddgs = DDGS()
    if search_type == "videos":
        return list(ddgs.videos(question, max_results=40) or [])
    if search_type == "images":
        return list(ddgs.images(question, max_results=40) or [])
    if search_type == "news":
        return list(ddgs.news(question, max_results=40) or [])
    raise ValueError(f"Unsupported type: {search_type}")


def render_page(question: str, search_type: str, body: str) -> str:
    label = TYPE_LABELS.get(search_type, search_type)
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(question)} — DuckDuckGo {escape(label)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0f1419;
      --surface: #1a2332;
      --border: #2d3a4f;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --link: #60a5fa;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f4f6f9;
        --surface: #ffffff;
        --border: #d8e0ea;
        --text: #1a2332;
        --muted: #64748b;
        --link: #2563eb;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .wrap {{
      max-width: 960px;
      margin: 0 auto;
      padding: 1.5rem 1rem 3rem;
    }}
    header {{
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{ margin: 0 0 0.35rem; font-size: 1.4rem; }}
    .meta {{ color: var(--muted); font-size: 0.95rem; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 1rem;
    }}
    .list {{ display: flex; flex-direction: column; gap: 1rem; }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .card.row {{
      flex-direction: row;
      gap: 1rem;
      padding: 1rem;
    }}
    .thumb {{
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: cover;
      background: #111;
      display: block;
    }}
    .card.row .thumb {{
      width: 180px;
      min-width: 180px;
      aspect-ratio: 16 / 9;
      border-radius: 8px;
    }}
    .body {{
      padding: 0.9rem 1rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}
    .card.row .body {{ padding: 0; flex: 1; }}
    a.title {{
      color: var(--link);
      text-decoration: none;
      font-weight: 600;
      font-size: 1.05rem;
    }}
    a.title:hover {{ text-decoration: underline; }}
    .snippet {{ color: var(--text); font-size: 0.95rem; }}
    .url, .meta-line {{
      color: var(--muted);
      font-size: 0.85rem;
      word-break: break-word;
    }}
    .img-card .thumb {{ aspect-ratio: 1; object-fit: cover; }}
    .empty {{
      padding: 2rem;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--border);
      border-radius: 12px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{escape(question)}</h1>
      <div class="meta">DuckDuckGo · {escape(label)}</div>
    </header>
    {body}
  </div>
</body>
</html>
"""


def render_videos(results: list[dict]) -> str:
    if not results:
        return '<div class="empty">לא נמצאו סרטונים</div>'

    cards = []
    for item in results:
        url = unwrap_ddg(
            clean_text(item.get("content") or item.get("href") or item.get("url"))
        )
        title = clean_text(item.get("title")) or url
        desc = clean_text(item.get("description"))
        images = item.get("images") if isinstance(item.get("images"), dict) else {}
        thumb = absolutize(
            clean_text(
                item.get("image")
                or item.get("thumbnail")
                or images.get("large")
                or images.get("medium")
                or images.get("small")
                or images.get("motion")
            )
        )
        duration = clean_text(item.get("duration"))
        publisher = clean_text(
            item.get("publisher")
            or item.get("uploader")
            or item.get("provider")
            or item.get("source")
        )
        meta_bits = [x for x in (duration, publisher) if x]
        thumb_html = (
            f'<img class="thumb" src="{escape(thumb)}" alt="" loading="lazy" />'
            if thumb
            else ""
        )
        cards.append(
            f"""
            <article class="card row">
              <a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{thumb_html}</a>
              <div class="body">
                <a class="title" href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(title)}</a>
                <div class="url">{escape(url)}</div>
                {f'<div class="meta-line">{escape(" · ".join(meta_bits))}</div>' if meta_bits else ""}
                {f'<div class="snippet">{escape(desc)}</div>' if desc else ""}
              </div>
            </article>
            """
        )
    return f'<div class="list">{"".join(cards)}</div>'


def render_images(results: list[dict]) -> str:
    if not results:
        return '<div class="empty">לא נמצאו תמונות</div>'

    cards = []
    for item in results:
        url = unwrap_ddg(clean_text(item.get("url") or item.get("href")))
        title = clean_text(item.get("title")) or url
        image = absolutize(clean_text(item.get("image") or item.get("thumbnail")))
        thumb = absolutize(clean_text(item.get("thumbnail") or item.get("image")))
        source = clean_text(item.get("source"))
        cards.append(
            f"""
            <article class="card img-card">
              <a href="{escape(url or image)}" target="_blank" rel="noopener noreferrer">
                <img class="thumb" src="{escape(thumb or image)}" alt="{escape(title)}" loading="lazy" />
              </a>
              <div class="body">
                <a class="title" href="{escape(url or image)}" target="_blank" rel="noopener noreferrer">{escape(title)}</a>
                {f'<div class="meta-line">{escape(source)}</div>' if source else ""}
                <div class="url">{escape(url or image)}</div>
              </div>
            </article>
            """
        )
    return f'<div class="grid">{"".join(cards)}</div>'


def render_news(results: list[dict]) -> str:
    if not results:
        return '<div class="empty">לא נמצאו חדשות</div>'

    cards = []
    for item in results:
        url = unwrap_ddg(clean_text(item.get("url") or item.get("href")))
        title = clean_text(item.get("title")) or url
        excerpt = re.sub(
            r"<[^>]+>",
            "",
            clean_text(item.get("body") or item.get("excerpt") or item.get("description")),
        )
        source = clean_text(item.get("source"))
        image = absolutize(clean_text(item.get("image")))
        thumb_html = (
            f'<img class="thumb" src="{escape(image)}" alt="" loading="lazy" />'
            if image
            else ""
        )
        cards.append(
            f"""
            <article class="card row">
              {f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{thumb_html}</a>' if image else ""}
              <div class="body">
                <a class="title" href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(title)}</a>
                <div class="url">{escape(url)}</div>
                {f'<div class="meta-line">{escape(source)}</div>' if source else ""}
                {f'<div class="snippet">{escape(excerpt)}</div>' if excerpt else ""}
              </div>
            </article>
            """
        )
    return f'<div class="list">{"".join(cards)}</div>'


def search_to_html(question: str, search_type: str) -> str:
    if search_type == "web":
        return fetch_web_html(question)

    results = fetch_ddgs_results(question, search_type)
    if search_type == "videos":
        body = render_videos(results)
    elif search_type == "images":
        body = render_images(results)
    elif search_type == "news":
        body = render_news(results)
    else:
        raise ValueError(f"Unsupported type: {search_type}")
    return render_page(question, search_type, body)


def main() -> int:
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <question> <type:web|images|videos|news> <output.html>",
            file=sys.stderr,
        )
        return 1

    question = sys.argv[1].strip()
    search_type = sys.argv[2].strip()
    out_path = Path(sys.argv[3])

    if not question:
        print("Missing question", file=sys.stderr)
        return 1
    if search_type not in TYPE_LABELS:
        print(f"Invalid type: {search_type}", file=sys.stderr)
        return 1

    html = search_to_html(question, search_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Saved {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
