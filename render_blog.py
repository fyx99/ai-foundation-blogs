"""Convert blog.md to SAP Community HTML format.

The Community uses <li-code lang="..."> for code blocks. Everything else is
standard HTML (h1-h3, p, ul, li, code, table). We render markdown to HTML
with the python-markdown library, then post-process:

  1. <pre><code class="language-X">...</code></pre>
       -> <li-code lang="X">...</li-code>
  2. Standalone "--" in prose -> em-dash "—"
     (Code blocks are protected: bash flags like --name must stay intact.)
"""
import re
import markdown

SRC = "ai-core-governance-levels/blog.md"
OUT = "ai-core-governance-levels/blog.html"

LANG_MAP = {"bash": "bash", "yaml": "yaml", "json": "json",
            "python": "python", "sql": "sql"}


def render():
    src = open(SRC).read()
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

    # 3. Restore code blocks.
    def restore(match: re.Match) -> str:
        return placeholders[int(match.group(1))]

    html = re.sub(r"\x00CODE(\d+)\x00", restore, html)

    open(OUT, "w").write(html)
    print(f"wrote {OUT}, lines: {html.count(chr(10)) + 1}")


if __name__ == "__main__":
    render()
