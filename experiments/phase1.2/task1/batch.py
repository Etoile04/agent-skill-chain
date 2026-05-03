#!/usr/bin/env python3
"""
batch.py — Directory scan, batch convert with per-file error isolation.

Conversion logic: .md → .html (simple markdown-to-HTML using stdlib only).
Invalid files (wrong extension or unparseable content) are caught and logged
but do NOT interrupt the batch.
"""

import os
import re
import json
import sys
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


# ── Inline converter (md → html) ──────────────────────────────────────────────

def md_to_html(md_text: str) -> str:
    """Minimal markdown-to-HTML converter using stdlib regex."""
    lines = md_text.split("\n")
    html_parts = ["<!DOCTYPE html>", "<html><head><meta charset='utf-8'>",
                  "<style>body{font-family:sans-serif;max-width:800px;margin:2em auto}"
                  "code{background:#f4f4f4;padding:2px 6px;border-radius:3px}"
                  "pre{background:#f4f4f4;padding:1em;border-radius:6px;overflow-x:auto}"
                  "</style></head><body>"]

    in_code_block = False
    code_buffer: List[str] = []

    for line in lines:
        # Code fence
        if line.strip().startswith("```"):
            if in_code_block:
                html_parts.append(f"<pre><code>{chr(10).join(code_buffer)}</code></pre>")
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            html_parts.append(f"<h{level}>{m.group(2)}</h{level}>")
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line):
            html_parts.append("<hr>")
            continue

        # List items
        m = re.match(r"^[-*+]\s+(.+)$", line)
        if m:
            html_parts.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        # Empty line
        if not line.strip():
            continue

        # Paragraph
        html_parts.append(f"<p>{_inline(line)}</p>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def _inline(text: str) -> str:
    """Process inline markdown: bold, italic, code, links."""
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class FileResult:
    path: str
    status: str          # "success" | "error" | "skipped"
    error: str | None
    input_size: int
    output_size: int | None
    output_path: str | None


@dataclass
class BatchResult:
    total_files: int
    success_count: int
    error_count: int
    skipped_count: int
    results: List[dict]


# ── Batch processor ───────────────────────────────────────────────────────────

def collect_files(directory: str, extensions: tuple = (".md",)) -> List[Path]:
    """Walk directory and collect candidate files."""
    base = Path(directory)
    if not base.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    files = sorted(p for p in base.rglob("*") if p.is_file())
    return files


def process_file(filepath: Path, output_dir: Path) -> FileResult:
    """Process a single file with error isolation."""
    input_size = filepath.stat().st_size

    # Only convert .md files
    if filepath.suffix.lower() != ".md":
        return FileResult(
            path=str(filepath),
            status="skipped",
            error=f"Unsupported extension: {filepath.suffix}",
            input_size=input_size,
            output_size=None,
            output_path=None,
        )

    try:
        content = filepath.read_text(encoding="utf-8")
        html = md_to_html(content)

        # Write output
        out_name = filepath.stem + ".html"
        out_path = output_dir / out_name
        out_path.write_text(html, encoding="utf-8")

        return FileResult(
            path=str(filepath),
            status="success",
            error=None,
            input_size=input_size,
            output_size=len(html.encode("utf-8")),
            output_path=str(out_path),
        )
    except Exception as exc:
        return FileResult(
            path=str(filepath),
            status="error",
            error=f"{type(exc).__name__}: {exc}",
            input_size=input_size,
            output_size=None,
            output_path=None,
        )


def batch_process(input_dir: str, output_dir: str) -> BatchResult:
    """Scan directory, convert each file, isolate errors."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    candidates = collect_files(input_dir)
    results: List[FileResult] = []

    for fpath in candidates:
        result = process_file(fpath, output_path)
        results.append(result)

    success = sum(1 for r in results if r.status == "success")
    errors = sum(1 for r in results if r.status == "error")
    skipped = sum(1 for r in results if r.status == "skipped")

    return BatchResult(
        total_files=len(results),
        success_count=success,
        error_count=errors,
        skipped_count=skipped,
        results=[asdict(r) for r in results],
    )


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "./test_batch"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./test_output"

    print(f"Scanning: {input_dir}")
    print(f"Output to: {output_dir}")
    print("-" * 50)

    result = batch_process(input_dir, output_dir)

    # Pretty-print summary
    print(f"\nTotal files scanned: {result.total_files}")
    print(f"  ✅ Success: {result.success_count}")
    print(f"  ❌ Error:   {result.error_count}")
    print(f"  ⏭  Skipped: {result.skipped_count}")
    print()

    for r in result.results:
        status_icon = {"success": "✅", "error": "❌", "skipped": "⏭"}.get(r["status"], "?")
        size_info = f"{r['input_size']}B → {r['output_size']}B" if r["output_size"] else f"{r['input_size']}B"
        err_info = f" ({r['error']})" if r["error"] else ""
        print(f"  {status_icon} {Path(r['path']).name}: {r['status']} | {size_info}{err_info}")

    # Write JSON result
    out_json = Path(output_dir) / "batch_result.json"
    out_json.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    print(f"\nJSON result → {out_json}")
