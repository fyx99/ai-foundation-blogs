#!/usr/bin/env python3
"""Convert a Markdown blog post to SAP Community HTML.

The Community editor uses <li-code lang="..."> for code blocks. Everything
else is standard HTML (h1-h6, p, ul/ol/li, code, table, ...). We render
markdown to HTML with python-markdown, then post-process:

  1. <pre><code class="language-X">...</code></pre>
       -> <li-code lang="X">...</li-code>
     Inside <li-code>, contents are NOT HTML-escaped — un-escape what
     python-markdown emitted.
  2. Standalone "--" in prose -> em-dash "—". Code blocks are protected
     (bash flags like --name must stay intact) by stashing them before the
     dash pass and restoring after.
  3. <img> tags become a plain-text placeholder paragraph:
       <p>[ Insert image here: <alt> (file: <src>) ]</p>
     The Community editor doesn't accept external <img> URLs anyway —
     authors upload images via the editor UI and the placeholder marks
     where the uploaded image goes.

Usage:
    python3 render.py <input.md> [output.html]

If output is omitted, writes <input>.html alongside the source.
"""
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.stderr.write(
        "error: the 'markdown' package is required.\n"
        "  pip install markdown\n"
    )
    sys.exit(1)


LANG_MAP = {
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "yaml": "yaml",
    "yml": "yaml",
    "json": "json",
    "python": "python",
    "py": "python",
    "sql": "sql",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "java": "java",
    "xml": "xml",
    "html": "html",
}


def render(src_path: Path, out_path: Path) -> None:
    src = src_path.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["fenced_code", "tables"])
    html = md.convert(src)

    # 1. Pull code blocks out of the way before we touch dashes/quotes.
    placeholders: list[str] = []

    def stash(match: re.Match) -> str:
        cls = match.group(1) or ""
        body = match.group(2)
        lang = "markup"
        m = re.search(r"language-(\S+)", cls)
        if m:
            lang = LANG_MAP.get(m.group(1), m.group(1))
        # python-markdown HTML-escapes code contents — undo that for li-code.
        body = (body.replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&quot;", '"')
                    .replace("&#39;", "'"))
        placeholders.append(f'<li-code lang="{lang}">{body}</li-code>')
        return f"\x00CODE{len(placeholders) - 1}\x00"

    html = re.sub(
        r'<pre><code(?:\s+class="([^"]*)")?>(.*?)</code></pre>',
        stash,
        html,
        flags=re.DOTALL,
    )

    # 2. Now safe to fix typography in prose.
    #    "--" surrounded by whitespace -> em-dash. Hyphenated words and
    #    HTML attribute syntax (e.g. lang="...") are left alone.
    html = re.sub(r" -- ", " — ", html)
    html = re.sub(r"--\n", "—\n", html)

    # 3. Replace <img> tags with a plain-text upload marker. The Community
    #    editor uploads images via its own UI; an external <img src="..."> is
    #    useless. The marker tells the author where to drop the uploaded image.
    def img_marker(match: re.Match) -> str:
        attrs = match.group(1)
        alt_m = re.search(r'alt="([^"]*)"', attrs)
        src_m = re.search(r'src="([^"]*)"', attrs)
        alt = alt_m.group(1) if alt_m else ""
        src = src_m.group(1) if src_m else ""
        descriptor = alt or src or "image"
        suffix = f" (file: {src})" if src and alt else ""
        return f"[ Insert image here: {descriptor}{suffix} ]"

    # Strip surrounding <p>...</p> when the paragraph is just an image.
    html = re.sub(
        r"<p>\s*<img\b([^>]*?)/?>\s*</p>",
        lambda m: f"<p>{img_marker(m)}</p>",
        html,
    )
    # Inline images that aren't standalone paragraphs.
    html = re.sub(r"<img\b([^>]*?)/?>", img_marker, html)

    # 4. Restore code blocks.
    def restore(match: re.Match) -> str:
        return placeholders[int(match.group(1))]

    html = re.sub(r"\x00CODE(\d+)\x00", restore, html)

    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({html.count(chr(10)) + 1} lines)")


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write("usage: render.py <input.md> [output.html]\n")
        sys.exit(1)

    src_path = Path(sys.argv[1])
    if not src_path.exists():
        sys.stderr.write(f"error: {src_path} not found\n")
        sys.exit(1)

    if len(sys.argv) >= 3:
        out_path = Path(sys.argv[2])
    else:
        out_path = src_path.with_suffix(".html")

    render(src_path, out_path)


if __name__ == "__main__":
    render(Path("ai-core-governance-levels/blog.md"), Path("ai-core-governance-levels/blog.html"))
