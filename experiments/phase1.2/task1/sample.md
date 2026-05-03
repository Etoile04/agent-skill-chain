# Getting Started Guide

Welcome to the **Markdown Converter** project! This tool converts Markdown to
multiple formats including HTML, plain text, and a structured JSON AST.

## Key Features

- Fast conversion with *zero external dependencies*
- Supports headings, lists, code blocks, links, images, and more
- **100% Python standard library** — no `pip install` needed

### Supported Elements

1. ATX-style headings (h1 through h6)
2. Unordered lists with `-`, `*`, or `+`
3. Ordered lists with `1.` numbering
4. Fenced code blocks with language hints
5. Inline formatting: **bold**, *italic*, `code`
6. Links like [Python Docs](https://docs.python.org)
7. Images like ![Logo](https://example.com/logo.png)

## Code Example

Here is a quick example:

```python
from converter import markdown_to_html, markdown_to_text, markdown_to_json

md = "# Hello\\nThis is **bold**."
print(markdown_to_html(md))
print(markdown_to_text(md))
print(markdown_to_json(md))
```

## Installation

Clone the repository and run directly:

```bash
git clone https://github.com/example/converter.git
cd converter
python converter.py sample.md
```

> **Note**: This project requires Python 3.6 or later.

---

## License

MIT License — see [LICENSE](https://opensource.org/licenses/MIT) for details.
