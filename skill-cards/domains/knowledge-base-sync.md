---
id: sc-20260429-001
type: domain
category: domains
task_types:
  - 知识库管理
  - 论文阅读
  - 文档同步
  - 飞书集成
avg_reward: 0.80
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
sources:
  - memory/2026-04-29.md
planning_hints:
  common_failures:
    - pattern: "飞书 API 报 folder locked"
      hint: "飞书知识空间同一 folder 不支持并发写，必须串行操作 + 2-3 秒间隔"
    - pattern: "增量同步检测不到文件变更"
      hint: "macOS 的 shasum 默认 SHA-1，必须显式指定 shasum -a 256 用 SHA-256"
    - pattern: "中文文件名导致编码错误"
      hint: "避免在 shell 中直接传中文文件名给 Python，改用 stdin 管道传参"
  typical_approach: "本地先构建验证，再同步飞书；增量同步 + hash 校验只同步变更部分"
  caveats:
    - "飞书知识空间 API 有并发写锁限制，串行 + 间隔是必须的"
    - "映射文件 .wiki-feishu-map.json 是本地与飞书双向同步的关键，不要丢失"
---

# 知识库构建与飞书同步工作流

## ✅ 成功经验 (e_success)

### 有效的策略
- **论文阅读后立即提炼**：读完论文立刻做 PRD 映射分析，不拖延
- **本地先构建，再同步飞书**：先在本地 wiki-agent-system/ 完成实体和素材页，验证 lint 通过后再同步
- **增量同步 + hash 校验**：用 SHA-256 检测文件变更，只同步有变化的部分，避免重复写入
- **映射文件维护**：`.wiki-feishu-map.json` 记录本地路径 ↔ 飞书 doc_id 的双向映射

### 关键决策
- **技术选择**：llm-wiki-skill v3.6.2 替代旧版本（功能更完整，脚本测试全过）
- **同步策略**：串行操作 + 2-3 秒间隔，避免飞书 API 并发锁（"folder locked"）
- **Hash 算法**：使用 `shasum -a 256`（SHA-256），而非默认 SHA-1

### 验证过的工具/方法
- llm-wiki-skill v3.6.2（install.sh, init-wiki, validate-step1, cache, source-registry, create-source-page, lint-runner）
- sync-to-feishu.sh（增量同步脚本）
- 飞书知识空间 API（space_id: 7633663431479954370）

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- **飞书 API 并发锁**：同时写同一个 folder 会报 "folder locked"，必须串行 + 间隔
- **shasum 默认算法**：macOS 的 `shasum` 默认 SHA-1，需要 `-a 256` 才是 SHA-256
- **中文文件名编码**：shell 嵌 Python 处理中文文件名有编码风险，改用 stdin 传参

### 错误模式
- **飞书并发锁**：症状（"folder locked" 报错）→ 根因（同一 folder 并发写）→ 修复（串行 + 间隔 2-3s）
- **Hash 不匹配**：症状（增量同步检测不到变更）→ 根因（SHA-1 vs SHA-256）→ 修复（`shasum -a 256`）

### 需要避免的做法
- 不要并发写入同一个飞书 folder
- 不要依赖 `shasum` 默认算法（macOS 上是 SHA-1）
- 不要在 shell 脚本中直接传中文文件名给 Python

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. **素材收集** — 保存论文/文章原始素材到 `raw/articles/`
2. **知识库 ingest** — 使用 llm-wiki 的 `create-source-page` 生成 source + entity 页
3. **Lint 验证** — 运行 `lint-runner` 确保结构正确
4. **增量同步** — 运行 `sync-to-feishu.sh` 同步到飞书
5. **导航更新** — 更新飞书导航页（08号文档）
6. **映射记录** — 更新 `.wiki-feishu-map.json`

### 触发条件
- 阅读完一篇新论文
- 需要将本地知识更新到飞书
- 知识库结构变更

### 前置条件
- llm-wiki-skill 已安装
- wiki-agent-system/ 已初始化
- 飞书知识空间有写权限

### 预期结果
- 本地 wiki 目录结构完整（overview, index, sources, entities, log）
- Lint 检查通过
- 飞书知识空间与本地同步

### 回退方案
- Lint 失败 → 检查 entity 的 frontmatter 格式
- 同步失败 → 检查 `.wiki-feishu-map.json` 映射
- 飞书并发锁 → 增加间隔时间或改为单线程同步
