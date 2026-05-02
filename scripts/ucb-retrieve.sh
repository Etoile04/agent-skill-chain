#!/usr/bin/env bash
# ucb-retrieve.sh — UCB 混合检索选择器
# 从 skill-cards/ 目录读取技能卡，计算 UCB 混合分数，输出排序结果
#
# 用法:
#   ./scripts/ucb-retrieve.sh --query "配置 A2A 通信" --top-k 3
#   ./scripts/ucb-retrieve.sh --query "知识库同步" --task-type "飞书集成"
#   ./scripts/ucb-retrieve.sh --query "超时" --alpha 0.7 --beta 0.3
#
# 依赖: python3, yq (可选，fallback 到 python yaml 解析)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_CARDS_DIR="$WORKSPACE_DIR/skill-cards"

# 默认参数
QUERY=""
TASK_TYPE=""
TOP_K=3
ALPHA=0.6
BETA=0.4
EXPLORATION_C=1.414
DECAY_LAMBDA=0.01
VERBOSE=0

# 解析参数
while [[ $# -gt 0 ]]; do
  case "$1" in
    --query)       QUERY="$2"; shift 2 ;;
    --task-type)   TASK_TYPE="$2"; shift 2 ;;
    --top-k)       TOP_K="$2"; shift 2 ;;
    --alpha)       ALPHA="$2"; shift 2 ;;
    --beta)        BETA="$2"; shift 2 ;;
    --c)           EXPLORATION_C="$2"; shift 2 ;;
    --lambda)      DECAY_LAMBDA="$2"; shift 2 ;;
    --verbose|-v)  VERBOSE=1; shift ;;
    --help|-h)
      echo "用法: $0 --query QUERY [选项]"
      echo ""
      echo "选项:"
      echo "  --query QUERY       查询描述（必填）"
      echo "  --task-type TYPE    过滤特定 task_type（可选）"
      echo "  --top-k N           返回前 N 个结果（默认 3）"
      echo "  --alpha FLOAT       UCB 权重（默认 0.6）"
      echo "  --beta FLOAT        语义相似度权重（默认 0.4）"
      echo "  --c FLOAT           探索系数（默认 1.414）"
      echo "  --lambda FLOAT      衰减速率（默认 0.01）"
      echo "  --verbose, -v       输出详细评分过程"
      echo "  --help, -h          显示帮助"
      exit 0
      ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [[ -z "$QUERY" ]]; then
  echo "错误: --query 是必填参数" >&2
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "错误: 需要安装 python3" >&2
  exit 1
fi

# 导出参数给 Python
export _QUERY="$QUERY"
export _TASK_TYPE="$TASK_TYPE"
export _TOP_K="$TOP_K"
export _ALPHA="$ALPHA"
export _BETA="$BETA"
export _C="$EXPLORATION_C"
export _LAMBDA="$DECAY_LAMBDA"
export _VERBOSE="$VERBOSE"
export _CARDS_DIR="$SKILL_CARDS_DIR"

# Python 核心计算逻辑
python3 << 'PYTHON_SCRIPT'
import sys
import os
import json
import math
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ===== 参数 =====
query = os.environ.get("_QUERY", "")
task_type = os.environ.get("_TASK_TYPE", "")
top_k = int(os.environ.get("_TOP_K", "3"))
alpha = float(os.environ.get("_ALPHA", "0.6"))
beta = float(os.environ.get("_BETA", "0.4"))
c = float(os.environ.get("_C", "1.414"))
decay_lambda = float(os.environ.get("_LAMBDA", "0.01"))
verbose = os.environ.get("_VERBOSE", "0") == "1"
cards_dir = os.environ.get("_CARDS_DIR", "")

# ===== 工具函数 =====

def parse_yaml_frontmatter(content):
    """从 Markdown 内容中提取 YAML frontmatter"""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    yaml_text = match.group(1)
    # 简单 YAML 解析（不依赖 PyYAML）
    result = {}
    current_key = None
    current_list = None
    in_list = False
    
    for line in yaml_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        # 列表项
        if stripped.startswith('- ') and in_list and current_key:
            value = stripped[2:].strip().strip('"').strip("'")
            if current_key not in result:
                result[current_key] = []
            result[current_key].append(value)
            continue
        
        # 键值对
        if ':' in stripped and not stripped.startswith('- '):
            in_list = False
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            if value:
                # 尝试解析类型
                if value in ('true', 'True'):
                    result[key] = True
                elif value in ('false', 'False'):
                    result[key] = False
                else:
                    try:
                        result[key] = float(value) if '.' in value else int(value)
                    except ValueError:
                        result[key] = value
                current_key = key
            else:
                # 空值，可能是列表开始
                current_key = key
                in_list = True
                result[key] = []
    
    return result

def jaccard_similarity(query, text):
    """Jaccard 相似度（关键词匹配 fallback）"""
    def tokenize(s):
        # 中英文分词：按空格和标点切分，过滤空串
        tokens = set(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', s.lower()))
        return tokens
    
    q_tokens = tokenize(query)
    t_tokens = tokenize(text)
    
    if not q_tokens or not t_tokens:
        return 0.0
    
    intersection = q_tokens & t_tokens
    union = q_tokens | t_tokens
    
    # 加权：匹配到的 query token 比例更重要
    query_coverage = len(intersection) / len(q_tokens) if q_tokens else 0
    jaccard = len(intersection) / len(union) if union else 0
    
    return 0.6 * query_coverage + 0.4 * jaccard

def compute_semantic_sim(query, card_content, task_types):
    """计算语义相似度（关键词匹配 fallback）"""
    # 在全文 + task_types 上计算相似度
    full_text = card_content + " " + " ".join(task_types)
    return jaccard_similarity(query, full_text)

def compute_decay(last_used_str, created_str, decay_lambda):
    """计算时间衰减因子"""
    now = datetime.now(timezone(timedelta(hours=8)))  # Asia/Shanghai
    
    # 优先用 last_used，否则用 created
    date_str = last_used_str or created_str
    if not date_str:
        return 1.0
    
    try:
        ref_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            tzinfo=timezone(timedelta(hours=8))
        )
        days_since = (now - ref_date).days
        return math.exp(-decay_lambda * max(days_since, 0))
    except:
        return 1.0

# ===== 加载技能卡 =====

cards = []
cards_path = Path(cards_dir)

for card_file in cards_path.rglob("*.md"):
    if card_file.name == "README.md":
        continue
    
    try:
        content = card_file.read_text(encoding='utf-8')
        fm = parse_yaml_frontmatter(content)
        
        if not fm.get('id'):
            continue
        
        # 从正文（跳过 frontmatter）提取标题
        body = re.sub(r'^---\s*\n.*?\n---', '', content, flags=re.DOTALL).strip()
        title_line = body.split('\n')[0] if body else ''
        title = re.sub(r'^#+\s*', '', title_line).strip() or card_file.stem
        
        transfer_mode = fm.get('transfer_mode', 'indirect')
        if transfer_mode not in ('direct', 'indirect', 'forbidden'):
            transfer_mode = 'indirect'

        card = {
            'id': fm.get('id', ''),
            'title': title,
            'type': fm.get('type', ''),
            'category': fm.get('category', ''),
            'task_types': fm.get('task_types', []),
            'avg_reward': float(fm.get('avg_reward', 0.5)),
            'usage_count': int(fm.get('usage_count', 0)),
            'created': fm.get('created', ''),
            'updated': fm.get('updated', ''),
            'last_used': fm.get('last_used', fm.get('updated', '')),
            'status': fm.get('status', 'draft'),
            'file_path': str(card_file.relative_to(cards_path.parent)),
            'transfer_mode': transfer_mode,
        }
        
        # task_type 过滤
        if task_type:
            if not any(task_type.lower() in str(tt).lower() for tt in card['task_types']):
                continue
        
        # 计算语义相似度
        card['semantic_sim'] = compute_semantic_sim(
            query, content, card['task_types']
        )
        
        cards.append(card)
    except Exception as e:
        if verbose:
            print(f"警告: 解析 {card_file} 失败: {e}", file=sys.stderr)

if not cards:
    print(json.dumps({"results": [], "metadata": {"error": "未找到匹配的技能卡"}}, ensure_ascii=False, indent=2))
    sys.exit(0)

# ===== 计算 UCB 分数 =====

N_total = sum(card['usage_count'] for card in cards)

ucb_scores = []
for card in cards:
    n_e = card['usage_count']
    r_bar = card['avg_reward']
    
    if n_e == 0:
        # 冷启动：赋予最高探索优先级
        ucb_raw = 999.0
    else:
        ucb_raw = r_bar + c * math.sqrt(math.log(max(N_total, 1)) / n_e)
    
    ucb_scores.append(ucb_raw)

# 归一化 UCB 到 [0, 1]
# 当所有卡片都是冷启动（ucb_raw=999）时，用 avg_reward 作为区分
all_cold = all(s == 999.0 for s in ucb_scores)
if all_cold:
    # 冷启动降级：用 avg_reward 直接排序，归一化到 [0.5, 1.0]
    rewards = [card['avg_reward'] for card in cards]
    r_min = min(rewards)
    r_max = max(rewards)
    r_range = r_max - r_min if r_max != r_min else 1.0
    for i, card in enumerate(cards):
        card['ucb_raw'] = ucb_scores[i]
        card['ucb_norm'] = 0.5 + 0.5 * (card['avg_reward'] - r_min) / r_range
else:
    ucb_min = min(ucb_scores)
    ucb_max = max(ucb_scores)
    ucb_range = ucb_max - ucb_min if ucb_max != ucb_min else 1.0
    for i, card in enumerate(cards):
        card['ucb_raw'] = ucb_scores[i]
        card['ucb_norm'] = (ucb_scores[i] - ucb_min) / ucb_range

# 计算时间衰减 + 混合评分（对所有卡片）
for card in cards:
    card['decay_weight'] = compute_decay(
        card.get('last_used', ''),
        card.get('created', ''),
        decay_lambda
    )
    
    card['alpha_contribution'] = alpha * card['ucb_norm']
    card['beta_contribution'] = beta * card['semantic_sim']
    base_score = card['alpha_contribution'] + card['beta_contribution']
    
    # transfer_mode adjustment
    if card['transfer_mode'] == 'direct':
        card['transfer_bonus'] = 1.2
    elif card['transfer_mode'] == 'forbidden':
        card['transfer_bonus'] = 0.5
    else:
        card['transfer_bonus'] = 1.0
    
    card['final_score'] = card['decay_weight'] * base_score * card['transfer_bonus']

# ===== 过滤 forbidden 卡 + 排序 + 输出 =====

# Filter out forbidden cards (unless ALL are forbidden)
non_forbidden = [c for c in cards if c['transfer_mode'] != 'forbidden']
if non_forbidden:
    cards_to_rank = non_forbidden
else:
    # All cards are forbidden — return them anyway to avoid empty results
    cards_to_rank = cards

cards_to_rank.sort(key=lambda x: x['final_score'], reverse=True)
results = cards_to_rank[:top_k]

output = {
    "results": [],
    "metadata": {
        "total_cards": len(cards),
        "filtered_cards": len(results),
        "query": query,
        "task_type_filter": task_type or None,
        "params": {
            "alpha": alpha,
            "beta": beta,
            "c": c,
            "lambda": decay_lambda,
            "N_total": N_total
        }
    }
}

for card in results:
    result = {
        "id": card['id'],
        "title": card['title'],
        "type": card['type'],
        "task_types": card['task_types'],
        "transfer_mode": card['transfer_mode'],
        "final_score": round(card['final_score'], 4),
        "score_breakdown": {
            "ucb_raw": round(card['ucb_raw'], 4),
            "ucb_norm": round(card['ucb_norm'], 4),
            "semantic_sim": round(card['semantic_sim'], 4),
            "decay_weight": round(card['decay_weight'], 4),
            "alpha_contribution": round(card['alpha_contribution'], 4),
            "beta_contribution": round(card['beta_contribution'], 4),
            "transfer_bonus": card['transfer_bonus']
        },
        "avg_reward": card['avg_reward'],
        "usage_count": card['usage_count'],
        "last_used": card.get('last_used'),
        "status": card['status']
    }
    output["results"].append(result)

print(json.dumps(output, ensure_ascii=False, indent=2))

if verbose:
    print("\n===== 详细评分过程 =====", file=sys.stderr)
    for card in results:
        print(f"\n[{card['id']}] {card['title']}", file=sys.stderr)
        print(f"  avg_reward={card['avg_reward']}, usage_count={card['usage_count']}", file=sys.stderr)
        print(f"  ucb_raw={card['ucb_raw']:.4f}, ucb_norm={card['ucb_norm']:.4f}", file=sys.stderr)
        print(f"  semantic_sim={card['semantic_sim']:.4f}", file=sys.stderr)
        print(f"  decay_weight={card['decay_weight']:.4f}", file=sys.stderr)
        print(f"  α×ucb={card['alpha_contribution']:.4f}, β×sem={card['beta_contribution']:.4f}", file=sys.stderr)
        print(f"  final_score={card['final_score']:.4f}", file=sys.stderr)

PYTHON_SCRIPT
