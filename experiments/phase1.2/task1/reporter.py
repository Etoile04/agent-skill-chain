#!/usr/bin/env python3
"""
reporter.py — Report generation and structured logging for batch conversion.

Accepts batch results from batch.py, outputs:
  - Structured JSON report to stdout
  - Leveled log messages to stderr (DEBUG, INFO, WARNING, ERROR)

Report includes: success/error/skipped counts, per-file size changes
(original → output, change rate), and total elapsed time.
"""

import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Any


# ── Logging to stderr ─────────────────────────────────────────────────────────

LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
_log_level = LOG_LEVELS["INFO"]


def set_log_level(level: str) -> None:
    """Set minimum log level. One of: DEBUG, INFO, WARNING, ERROR."""
    global _log_level
    level = level.upper()
    if level not in LOG_LEVELS:
        raise ValueError(f"Unknown log level: {level}. Use: {', '.join(LOG_LEVELS)}")
    _log_level = LOG_LEVELS[level]


def _log(level: str, message: str) -> None:
    if LOG_LEVELS.get(level, 0) >= _log_level:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{ts}] {level}: {message}", file=sys.stderr)


def debug(msg: str) -> None:
    _log("DEBUG", msg)


def info(msg: str) -> None:
    _log("INFO", msg)


def warning(msg: str) -> None:
    _log("WARNING", msg)


def error(msg: str) -> None:
    _log("ERROR", msg)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class FileReport:
    """Per-file reporting entry."""
    filename: str
    status: str           # "success" | "error" | "skipped"
    original_size: int    # bytes
    output_size: Optional[int]  # bytes, None if not converted
    change_rate: Optional[float]  # (output - input) / input, None if not applicable
    error: Optional[str]


@dataclass
class ConversionReport:
    """Full batch conversion report."""
    total_files: int
    success_count: int
    error_count: int
    skipped_count: int
    total_input_bytes: int
    total_output_bytes: int
    overall_change_rate: Optional[float]
    elapsed_seconds: float
    files: List[FileReport]

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_files": self.total_files,
                "success": self.success_count,
                "error": self.error_count,
                "skipped": self.skipped_count,
                "total_input_bytes": self.total_input_bytes,
                "total_output_bytes": self.total_output_bytes,
                "overall_change_rate": self.overall_change_rate,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
            },
            "files": [asdict(f) for f in self.files],
        }


# ── Report generation ─────────────────────────────────────────────────────────

def _calc_change_rate(input_size: int, output_size: Optional[int]) -> Optional[float]:
    """Calculate size change rate. Returns None if not applicable."""
    if output_size is None or input_size == 0:
        return None
    return round((output_size - input_size) / input_size, 4)


def generate_report(
    batch_results: List[dict],
    elapsed_seconds: float,
) -> ConversionReport:
    """
    Generate a ConversionReport from batch.py's result list.

    Args:
        batch_results: List of dicts from BatchResult.results (as returned by batch_process).
        elapsed_seconds: Total wall-clock time for the batch run.

    Returns:
        ConversionReport with per-file details and aggregate statistics.
    """
    file_reports: List[FileReport] = []
    total_input = 0
    total_output = 0
    success_count = 0
    error_count = 0
    skipped_count = 0

    for r in batch_results:
        status = r.get("status", "unknown")
        input_size = r.get("input_size", 0)
        output_size = r.get("output_size")

        filename = Path(r.get("path", "<unknown>")).name
        change_rate = _calc_change_rate(input_size, output_size) if status == "success" else None

        fr = FileReport(
            filename=filename,
            status=status,
            original_size=input_size,
            output_size=output_size,
            change_rate=change_rate,
            error=r.get("error"),
        )
        file_reports.append(fr)

        total_input += input_size
        if output_size is not None:
            total_output += output_size

        if status == "success":
            success_count += 1
        elif status == "error":
            error_count += 1
        elif status == "skipped":
            skipped_count += 1

        # Per-file logging
        if status == "success":
            rate_str = f" ({change_rate:+.1%})" if change_rate is not None else ""
            info(f"✅ {filename}: {input_size}B → {output_size}B{rate_str}")
        elif status == "error":
            error(f"❌ {filename}: {r.get('error', 'unknown error')}")
        elif status == "skipped":
            warning(f"⏭  {filename}: skipped ({r.get('error', '')})")
        else:
            debug(f"? {filename}: {status}")

    overall_rate = _calc_change_rate(total_input, total_output) if total_output > 0 else None

    return ConversionReport(
        total_files=len(file_reports),
        success_count=success_count,
        error_count=error_count,
        skipped_count=skipped_count,
        total_input_bytes=total_input,
        total_output_bytes=total_output,
        overall_change_rate=overall_rate,
        elapsed_seconds=elapsed_seconds,
        files=file_reports,
    )


def format_report_json(report: ConversionReport) -> str:
    """Format report as JSON string (to stdout)."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def format_report_text(report: ConversionReport) -> str:
    """Format report as human-readable text (fallback)."""
    lines = []
    lines.append("=" * 60)
    lines.append("BATCH CONVERSION REPORT")
    lines.append("=" * 60)
    lines.append(f"Total files:  {report.total_files}")
    lines.append(f"  ✅ Success: {report.success_count}")
    lines.append(f"  ❌ Error:   {report.error_count}")
    lines.append(f"  ⏭  Skipped: {report.skipped_count}")
    lines.append(f"")
    lines.append(f"Total input:  {report.total_input_bytes} bytes")
    lines.append(f"Total output: {report.total_output_bytes} bytes")
    if report.overall_change_rate is not None:
        lines.append(f"Change rate:  {report.overall_change_rate:+.2%}")
    lines.append(f"Elapsed:      {report.elapsed_seconds:.3f}s")
    lines.append("")

    lines.append("-" * 60)
    lines.append(f"{'File':<30} {'Status':<10} {'Size Change':<20} {'Rate':<10}")
    lines.append("-" * 60)
    for f in report.files:
        size_str = f"{f.original_size}B"
        if f.output_size is not None:
            size_str = f"{f.original_size}B → {f.output_size}B"
        rate_str = f"{f.change_rate:+.1%}" if f.change_rate is not None else "-"
        lines.append(f"{f.filename:<30} {f.status:<10} {size_str:<20} {rate_str:<10}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ── Convenience: run from BatchResult dict ────────────────────────────────────

def report_from_batch_result(batch_result_dict: dict, elapsed: float, output_json: bool = True) -> str:
    """
    Accept a full BatchResult dict (as returned by batch_process → asdict),
    generate the report, log to stderr, return formatted report string.
    """
    results = batch_result_dict.get("results", [])
    report = generate_report(results, elapsed)

    info(f"Batch complete: {report.success_count} success, "
         f"{report.error_count} error, {report.skipped_count} skipped "
         f"in {report.elapsed_seconds:.3f}s")

    if output_json:
        return format_report_json(report)
    else:
        return format_report_text(report)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate conversion report from batch result")
    parser.add_argument("batch_result_json", help="Path to batch_result.json from batch.py")
    parser.add_argument("--elapsed", type=float, default=None,
                        help="Elapsed time in seconds (default: read from file or 0)")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO", help="Minimum log level (default: INFO)")
    args = parser.parse_args()

    set_log_level(args.log_level)

    result_path = Path(args.batch_result_json)
    if not result_path.exists():
        error(f"File not found: {result_path}")
        sys.exit(1)

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
        debug(f"Loaded batch result from {result_path}")
    except Exception as exc:
        error(f"Failed to read {result_path}: {exc}")
        sys.exit(1)

    elapsed = args.elapsed if args.elapsed is not None else batch_data.get("elapsed_seconds", 0.0)

    output = report_from_batch_result(batch_data, elapsed, output_json=(args.format == "json"))
    print(output)  # stdout — structured report
