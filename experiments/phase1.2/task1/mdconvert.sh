#!/usr/bin/env bash
# mdconvert.sh — CLI entry point for Markdown conversion pipeline
# Usage: ./mdconvert.sh [选项] <输入路径>

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
FORMAT="html"
OUTPUT_DIR="./output"
BATCH_MODE=false
INPUT_PATH=""

# ── Resolve script directory ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Help ──────────────────────────────────────────────────────────────────────
show_help() {
    cat <<EOF
用法: $(basename "$0") [选项] <输入路径>

选项:
  -f, --format FORMAT   输出格式: html|text|json (默认: html)
  -o, --output DIR      输出目录 (默认: ./output)
  -b, --batch           批量模式（处理目录下所有.md文件）
  -h, --help            显示帮助

退出码:
  0  全部成功
  1  部分失败
  2  参数错误
EOF
}

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--format)
            if [[ -z "${2:-}" ]]; then
                echo "错误: --format 需要指定格式 (html|text|json)" >&2
                exit 2
            fi
            FORMAT="$2"
            if [[ "$FORMAT" != "html" && "$FORMAT" != "text" && "$FORMAT" != "json" ]]; then
                echo "错误: 不支持的格式 '$FORMAT' (可选: html, text, json)" >&2
                exit 2
            fi
            shift 2
            ;;
        -o|--output)
            if [[ -z "${2:-}" ]]; then
                echo "错误: --output 需要指定目录路径" >&2
                exit 2
            fi
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -b|--batch)
            BATCH_MODE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "错误: 未知选项 '$1'" >&2
            show_help >&2
            exit 2
            ;;
        *)
            if [[ -n "$INPUT_PATH" ]]; then
                echo "错误: 只能指定一个输入路径" >&2
                exit 2
            fi
            INPUT_PATH="$1"
            shift
            ;;
    esac
done

# ── Validate input path ──────────────────────────────────────────────────────
if [[ -z "$INPUT_PATH" ]]; then
    echo "错误: 未指定输入路径" >&2
    show_help >&2
    exit 2
fi

if [[ ! -e "$INPUT_PATH" ]]; then
    echo "错误: 路径不存在 '$INPUT_PATH'" >&2
    exit 2
fi

# ── Resolve to absolute path ─────────────────────────────────────────────────
INPUT_PATH="$(cd "$(dirname "$INPUT_PATH")" && pwd)/$(basename "$INPUT_PATH")"
OUTPUT_DIR="$(cd "$(dirname "$OUTPUT_DIR")" 2>/dev/null && pwd)/$(basename "$OUTPUT_DIR")" || {
    # Output dir parent doesn't exist yet; make it absolute
    [[ "$OUTPUT_DIR" != /* ]] && OUTPUT_DIR="$(pwd)/$OUTPUT_DIR"
}

mkdir -p "$OUTPUT_DIR"

# ── Python helper — single file conversion via converter.py ───────────────────
convert_single() {
    local input_file="$1"
    local fmt="$2"
    local out_dir="$3"

    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from converter import tokenize, to_html, to_text, to_json
from pathlib import Path

md = Path('$input_file').read_text(encoding='utf-8')
ast = tokenize(md)

if '$fmt' == 'html':
    result = to_html(ast)
    ext = '.html'
elif '$fmt' == 'text':
    result = to_text(ast)
    ext = '.txt'
elif '$fmt' == 'json':
    result = to_json(ast)
    ext = '.json'
else:
    print(f'Unknown format: $fmt', file=sys.stderr)
    sys.exit(1)

stem = Path('$input_file').stem
out_path = Path('$out_dir') / (stem + ext)
out_path.write_text(result, encoding='utf-8')
print(out_path)
"
}

# ── Single file mode ─────────────────────────────────────────────────────────
if [[ "$BATCH_MODE" == "false" ]]; then
    if [[ ! -f "$INPUT_PATH" ]]; then
        echo "错误: 单文件模式需要指定文件，不是目录 '$INPUT_PATH'" >&2
        exit 2
    fi

    if [[ "${INPUT_PATH##*.}" != "md" ]]; then
        echo "警告: 输入文件不是 .md 扩展名，仍尝试转换" >&2
    fi

    echo "转换: $INPUT_PATH → $FORMAT"
    output_file=$(convert_single "$INPUT_PATH" "$FORMAT" "$OUTPUT_DIR") || {
        echo "错误: 转换失败 '$INPUT_PATH'" >&2
        exit 1
    }
    echo "输出: $output_file"

    # Call reporter if available
    if [[ -x "$SCRIPT_DIR/reporter.py" ]]; then
        python3 "$SCRIPT_DIR/reporter.py" "$INPUT_PATH" "$output_file" "$FORMAT" || true
    fi

    exit 0
fi

# ── Batch mode ───────────────────────────────────────────────────────────────
if [[ "$BATCH_MODE" == "true" ]]; then
    if [[ ! -d "$INPUT_PATH" ]]; then
        echo "错误: 批量模式需要指定目录，不是文件 '$INPUT_PATH'" >&2
        exit 2
    fi

    echo "批量转换: $INPUT_PATH/ → $FORMAT (输出: $OUTPUT_DIR/)"
    echo "─────────────────────────────────────"

    SUCCESS=0
    FAIL=0
    TOTAL=0

    # Find all .md files in the directory (non-recursive first, then recursive)
    shopt -s nullglob
    md_files=("$INPUT_PATH"/*.md)
    shopt -u nullglob

    if [[ ${#md_files[@]} -eq 0 ]]; then
        echo "警告: 目录中没有找到 .md 文件" >&2
        exit 0
    fi

    for md_file in "${md_files[@]}"; do
        TOTAL=$((TOTAL + 1))
        fname="$(basename "$md_file")"
        if output_file=$(convert_single "$md_file" "$FORMAT" "$OUTPUT_DIR" 2>/dev/null); then
            echo "  ✅ $fname → $(basename "$output_file")"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "  ❌ $fname — 转换失败"
            FAIL=$((FAIL + 1))
        fi
    done

    echo "─────────────────────────────────────"
    echo "完成: $SUCCESS/$TOTAL 成功, $FAIL 失败"

    # Call reporter if available
    if [[ -x "$SCRIPT_DIR/reporter.py" ]]; then
        python3 "$SCRIPT_DIR/reporter.py" "$INPUT_PATH" "$OUTPUT_DIR" "$FORMAT" || true
    fi

    if [[ $FAIL -gt 0 ]]; then
        exit 1
    fi
    exit 0
fi
