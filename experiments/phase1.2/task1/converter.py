"""
converter.py — Markdown → HTML / Plain Text / JSON AST converter.

Pure Python 3 standard-library implementation. No external dependencies.

Supported Markdown elements:
  - ATX headings (h1–h6)
  - Unordered lists (-, *, +)
  - Ordered lists (1. ...)
  - Fenced code blocks (```)
  - Inline code (`...`)
  - Bold (**...**, __...__)
  - Italic (*...*, _..._)
  - Links [text](url)
  - Images ![alt](src)
  - Paragraphs
  - Horizontal rules (---, ***, ___)
  - Blockquotes (> ...)
"""

import json
import re
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# 1. Tokeniser — produces a JSON AST
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _parse_inline(text: str) -> List[Dict[str, Any]]:
    """Parse inline Markdown elements within a line, returning AST nodes."""
    nodes: List[Dict[str, Any]] = []
    # Process in order: images, links, bold, italic, inline code
    pos = 0
    length = len(text)

    while pos < length:
        remaining = text[pos:]

        # Image: ![alt](src)
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", remaining)
        if m:
            nodes.append({"type": "image", "alt": m.group(1), "src": m.group(2)})
            pos += m.end()
            continue

        # Link: [text](url)
        m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", remaining)
        if m:
            nodes.append({"type": "link", "text": m.group(1), "url": m.group(2)})
            pos += m.end()
            continue

        # Inline code: `...`
        m = re.match(r"`([^`]+)`", remaining)
        if m:
            nodes.append({"type": "code", "text": m.group(1)})
            pos += m.end()
            continue

        # Bold: **...** or __...__
        m = re.match(r"(\*\*|__)(.+?)\1", remaining)
        if m:
            nodes.append({"type": "bold", "children": _parse_inline(m.group(2))})
            pos += m.end()
            continue

        # Italic: *...* or _..._  (single delim, not preceded/followed by same delim)
        m = re.match(r"(?<!\*)(\*)(?!\*)(.+?)(?<!\*)\*(?!\*)", remaining)
        if not m:
            m = re.match(r"(?<!_)([_])(?!_)(.+?)(?<!_)\_(?!_)", remaining)
        if m:
            nodes.append({"type": "italic", "children": _parse_inline(m.group(2))})
            pos += m.end()
            continue

        # Plain text — consume one character
        nodes.append({"type": "text", "value": remaining[0]})
        pos += 1

    # Merge adjacent text nodes
    merged: List[Dict[str, Any]] = []
    for node in nodes:
        if (
            node["type"] == "text"
            and merged
            and merged[-1]["type"] == "text"
        ):
            merged[-1]["value"] += node["value"]
        else:
            merged.append(node)

    return merged


def tokenize(markdown: str) -> List[Dict[str, Any]]:
    """
    Parse Markdown text into a JSON AST (list of block-level nodes).

    Returns a list of dicts, each with at least a 'type' key.
    """
    ast: List[Dict[str, Any]] = []
    lines = markdown.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: List[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            # consume closing ```
            if i < n:
                i += 1
            ast.append({
                "type": "code_block",
                "language": lang or None,
                "content": "\n".join(code_lines),
            })
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            ast.append({"type": "horizontal_rule"})
            i += 1
            continue

        # ATX heading
        m = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if m:
            level = len(m.group(1))
            ast.append({
                "type": "heading",
                "level": level,
                "children": _parse_inline(m.group(2)),
            })
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines: List[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            ast.append({
                "type": "blockquote",
                "children": _parse_inline(" ".join(quote_lines)),
            })
            continue

        # Unordered list
        if re.match(r"^[-*+]\s+", stripped):
            items: List[Dict[str, Any]] = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                item_text = re.sub(r"^[-*+]\s+", "", lines[i].strip())
                items.append({"type": "list_item", "children": _parse_inline(item_text)})
                i += 1
            ast.append({"type": "unordered_list", "items": items})
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append({"type": "list_item", "children": _parse_inline(item_text)})
                i += 1
            ast.append({"type": "ordered_list", "items": items})
            continue

        # Paragraph — collect consecutive non-empty, non-special lines
        para_lines: List[str] = []
        while i < n and lines[i].strip() and not _is_block_start(lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            ast.append({
                "type": "paragraph",
                "children": _parse_inline(" ".join(para_lines)),
            })

    return ast


def _is_block_start(line: str) -> bool:
    """Check if a line starts a new block element."""
    if not line:
        return True
    if line.startswith("```"):
        return True
    if re.match(r"^#{1,6}\s+", line):
        return True
    if re.match(r"^[-*+]\s+", line):
        return True
    if re.match(r"^\d+\.\s+", line):
        return True
    if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line):
        return True
    if line.startswith(">"):
        return True
    return False


# ---------------------------------------------------------------------------
# 2. AST → HTML renderer
# ---------------------------------------------------------------------------

def _inline_to_html(nodes: List[Dict[str, Any]]) -> str:
    """Render inline AST nodes to HTML."""
    parts: List[str] = []
    for node in nodes:
        t = node["type"]
        if t == "text":
            parts.append(_escape_html(node["value"]))
        elif t == "bold":
            parts.append(f"<strong>{_inline_to_html(node['children'])}</strong>")
        elif t == "italic":
            parts.append(f"<em>{_inline_to_html(node['children'])}</em>")
        elif t == "code":
            parts.append(f"<code>{_escape_html(node['text'])}</code>")
        elif t == "link":
            parts.append(
                f'<a href="{_escape_html(node["url"])}">'
                f"{_escape_html(node['text'])}</a>"
            )
        elif t == "image":
            parts.append(
                f'<img src="{_escape_html(node["src"])}" '
                f'alt="{_escape_html(node["alt"])}" />'
            )
    return "".join(parts)


def to_html(ast: List[Dict[str, Any]]) -> str:
    """Convert a Markdown AST to an HTML string."""
    parts: List[str] = []
    for node in ast:
        t = node["type"]
        if t == "heading":
            tag = f"h{node['level']}"
            parts.append(f"<{tag}>{_inline_to_html(node['children'])}</{tag}>")
        elif t == "paragraph":
            parts.append(f"<p>{_inline_to_html(node['children'])}</p>")
        elif t == "code_block":
            lang_attr = f' class="language-{_escape_html(node["language"])}"' if node["language"] else ""
            parts.append(
                f"<pre><code{lang_attr}>{_escape_html(node['content'])}</code></pre>"
            )
        elif t == "unordered_list":
            items = "".join(
                f"<li>{_inline_to_html(item['children'])}</li>"
                for item in node["items"]
            )
            parts.append(f"<ul>{items}</ul>")
        elif t == "ordered_list":
            items = "".join(
                f"<li>{_inline_to_html(item['children'])}</li>"
                for item in node["items"]
            )
            parts.append(f"<ol>{items}</ol>")
        elif t == "horizontal_rule":
            parts.append("<hr />")
        elif t == "blockquote":
            parts.append(f"<blockquote><p>{_inline_to_html(node['children'])}</p></blockquote>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. AST → Plain Text renderer
# ---------------------------------------------------------------------------

def _inline_to_text(nodes: List[Dict[str, Any]]) -> str:
    """Render inline AST nodes to plain text, stripping all markup."""
    parts: List[str] = []
    for node in nodes:
        t = node["type"]
        if t in ("text",):
            parts.append(node["value"])
        elif t == "bold":
            parts.append(_inline_to_text(node["children"]))
        elif t == "italic":
            parts.append(_inline_to_text(node["children"]))
        elif t == "code":
            parts.append(node["text"])
        elif t == "link":
            parts.append(f"{node['text']} ({node['url']})")
        elif t == "image":
            parts.append(f"[Image: {node['alt']}]" if node["alt"] else "[Image]")
    return "".join(parts)


def to_text(ast: List[Dict[str, Any]]) -> str:
    """Convert a Markdown AST to plain text, preserving semantic content."""
    parts: List[str] = []
    for node in ast:
        t = node["type"]
        if t == "heading":
            prefix = "#" * node["level"] + " "
            parts.append(f"{prefix}{_inline_to_text(node['children'])}")
        elif t == "paragraph":
            parts.append(_inline_to_text(node["children"]))
        elif t == "code_block":
            parts.append(node["content"])
        elif t == "unordered_list":
            for item in node["items"]:
                parts.append(f"• {_inline_to_text(item['children'])}")
        elif t == "ordered_list":
            for idx, item in enumerate(node["items"], 1):
                parts.append(f"{idx}. {_inline_to_text(item['children'])}")
        elif t == "horizontal_rule":
            parts.append("---")
        elif t == "blockquote":
            parts.append(f"> {_inline_to_text(node['children'])}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 4. AST → JSON serialiser
# ---------------------------------------------------------------------------

def to_json(ast: List[Dict[str, Any]], indent: int = 2) -> str:
    """Serialise the AST to a JSON string."""
    return json.dumps(ast, indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 5. Convenience: full pipeline helpers
# ---------------------------------------------------------------------------

def markdown_to_html(md: str) -> str:
    """Markdown string → HTML in one call."""
    return to_html(tokenize(md))


def markdown_to_text(md: str) -> str:
    """Markdown string → plain text in one call."""
    return to_text(tokenize(md))


def markdown_to_json(md: str, indent: int = 2) -> str:
    """Markdown string → JSON AST in one call."""
    return to_json(tokenize(md), indent=indent)


# ---------------------------------------------------------------------------
# CLI demo / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sample_file = sys.argv[1] if len(sys.argv) > 1 else None
    if sample_file:
        with open(sample_file, "r", encoding="utf-8") as f:
            md = f.read()
    else:
        md = """\
# Sample Document

This is a **bold** and *italic* test paragraph with `inline code`.

## Features

- Item one with a [link](https://example.com)
- Item two with **bold text**
- Item three

### Ordered List

1. First item
2. Second item
3. Third item

## Code Example

```python
def hello(name: str) -> str:
    return f"Hello, {name}!"

print(hello("world"))
```

> This is a blockquote with **emphasis**.

---

End of document. Visit [OpenAI](https://openai.com) for more.
"""

    ast = tokenize(md)

    print("=" * 60)
    print("HTML OUTPUT")
    print("=" * 60)
    print(to_html(ast))
    print()

    print("=" * 60)
    print("PLAIN TEXT OUTPUT")
    print("=" * 60)
    print(to_text(ast))
    print()

    print("=" * 60)
    print("JSON AST OUTPUT")
    print("=" * 60)
    print(to_json(ast))
