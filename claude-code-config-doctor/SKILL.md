---
name: claude-code-config-doctor
description: Diagnoses and fixes Claude Code configuration and model-connection errors across the full chain: Claude Code settings / environment variables, third-party model endpoints, LiteLLM / API gateways / proxies, providers, and Windows environments. Use when Claude Code shows unknown-model catalog warnings, context-window errors (200k/1M), "Content block not found", or 401/403/404/429/500/502/503 errors; when LiteLLM config.yaml, model mapping, ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, startup scripts (.bat/.ps1), or environment-variable propagation are involved; or when the user asks to debug / align / trim settings.json, settings.local.json, or a LiteLLM proxy.
---

# Claude Code Configuration Doctor

通用诊断与修复 Skill：处理 **Claude Code 项目/全局配置与模型接入报错**。
围绕一条完整调用链定位故障，而不是对某条报错做临时补丁：

```
Claude Code
   ↓
Claude Code Settings / 环境变量
   ↓
Anthropic / OpenAI-compatible 端点
   ↓
LiteLLM / Gateway / Proxy
   ↓
Provider
   ↓
Actual Model ID
   ↓
Model Capability (context / tool calling / reasoning)
```

任何报错都尽量定位到**具体层级**；遇到完全不同的 Provider 也按同一方法论走。

---

## 1. 适用范围

- Claude Code 启动/运行中的模型目录警告、上下文窗口报错、流式/SSE/工具调用解析错误、HTTP 4xx/5xx
- `settings.json` / `settings.local.json` / 全局 `~/.claude/settings.json` 的查看、修改、精简、对齐
- `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL` / 模型映射
- LiteLLM `config.yaml`（`model_list`、`model_name`、`litellm_params`、`api_base`、`api_key`、`drop_params`、fallback、retry）
- Windows 启动脚本（`.bat` / `.ps1` / 快捷方式）、环境变量传播、端口/进程残留
- 第三方 Provider（DeepSeek / Qwen / GLM / MiniMax / MiMo / Grok / Stepfun / Gemini / One-API / New-API / 本地模型 / 其它 OpenAI-compatible 与 Anthropic-compatible Gateway）

## 2. 不适用场景

- 纯代码 bug 调试（走普通调试流程，不是本 Skill）
- 修改其它已有 Skill（提示词明确禁止）
- 修改 Claude Code 全局配置中**与本故障无关**的部分（最小修改原则）
- 用户只要一份纯理论说明而不希望实际执行 → 只输出分析，不动任何文件

## 3. 核心原则

1. **Root Cause First**（绝不"看到 X 直接改 Y"）：
   - 看到 404 ≠ 改模型名；看到 200K ≠ 改成 1M；看到 401 ≠ 重写 API Key；看到 LiteLLM 报错 ≠ 重写 config.yaml。
   - 先区分 **Primary Root Cause** 与 **Secondary / Cascading 症状**。
   - 范例级联：`Unknown Model → 客户端拿不到模型元数据 → Context Window 按 200k 假设 → Auto-Compact 提前发生`。此时 Auto-Compact 是**症状**，不是独立根因。
2. **事实 / 推断 / 假设三级标注**（第十二节机制）：
   每个诊断结论标注 **Confirmed**（日志/配置/实测证实）、**Likely**（现象+配置高度推断）、**Needs Verification**（证据不足，需再测）。
   **禁止把未经验证的推断写成绝对规则。** 用户记录里的"推测"不能直接当事实。
3. **最小修改**（第十三节安全协议）：只改必要字段；保留其它 Provider、其它模型、权限配置；不覆盖无关环境变量；不重写整个文件。
4. **不硬编码当前案例**（第十四节）：`agnes-3.0-flash` / `deepseek-flash` / `step-3.7-flash` 只能作为 examples，不得写成固定模型。泛化到任意 Provider，**不预设某 Provider 一定用某种协议**——必须实测。
5. **逐层真实验证**（第十五节）："文件存在" ≠ "配置正确"；"HTTP 200" ≠ "完整链路正常"。必须沿调用链逐层用**当前机器实际可用**的方法验证。

## 4. 标准诊断流程（24 步，按序执行）

```
 1  发现错误
 2  读取完整错误日志（不要只看一行）
 3  确认 Claude Code 版本（claude --version）
 4  确认当前项目目录
 5  定位项目级配置（.claude/settings.json / settings.local.json）
 6  定位全局配置（~/.claude/settings.json）
 7  检查环境变量（系统级/用户级/进程级/Shell 临时级/启动脚本内 set）
 8  识别 Model（ANTHROPIC_MODEL 及各 DEFAULT_* 当前值）
 9  识别 Provider（端点域名→推断厂商，用实测验证而非猜测）
 10 识别 Endpoint（ANTHROPIC_BASE_URL / OPENAI_BASE_URL）
 11 识别 Gateway / LiteLLM（是否有 127.0.0.1:xxxx 本地代理）
 12 建立完整调用链（画出当前环境实际经过的层，去掉不存在的层）
 13 分类错误（Category A–M，见 references/error-catalog.md）
 14 寻找 Primary Root Cause
 15 区分 Secondary / Cascading 症状
 16 提出最小修改方案（先给方案，经用户确认再动手）
 17 创建备份（<file>.bak，备份的是修改前内容）
 18 修改配置（只改必要字段）
 19 验证配置格式（JSON/YAML 解析）
 20 验证环境变量（是否真正进入目标进程）
 21 验证 Endpoint（health / /v1/models）
 22 验证 Model（最小请求阶梯：非流式→流式→工具→并行工具）
 23 验证 Claude Code（重启会话后原报错是否消失）
 24 输出诊断报告（固定格式，见第 12 节）
```

## 5. 决策树（错误关键词 → 分类 → 读哪份参考）

```
报错关键词
├─ "isn't described by this version's model catalog" / "within 200k tokens"
│      → B / D  → references/model-mapping.md + context-window.md
├─ "Content block not found" / 流式中断 / 工具调用后报错
│      → H       → error-catalog.md §H（先分 12 个子类，抓原始 SSE）
├─ 401 / 403 / invalid_api_key
│      → G / E   → configuration-matrix.md（key 实际进了哪个进程）
├─ 404 / model_not_found / "No available channel"
│      → C / E   → model-mapping.md（model_name vs 上游 model）
├─ 429 / rate limit
│      → M       → 限流是服务商行为，配置通常修不了；只减并发或加 fallback
├─ 500 / 502 / 503 / connection refused
│      → E / L   → 代理存活？端口？进程残留？
├─ LiteLLM 起不来 / 启动慢 / 热冷路径
│      → F / L   → litellm-diagnostic-chain.md
├─ JSON / YAML 解析失败
│      → K       → 先修语法再谈语义
└─ "配置里明明有 key 但进程拿不到"
       → J       → configuration-matrix.md §Windows 环境变量
```

## 6. 工具使用规则

- `claude --version` 先确认真实版本——模型目录行为随版本变化，先问版本再给结论。
- curl 打端点做隔离测试，按 **最小请求阶梯** 逐层加压：非流式 → 流式 → 带 tools 非流式 → 带 tools 流式 → **并行工具调用（一次响应多个工具）**。哪层失败就定位到哪层。
- 抓 SSE 时关注：`content_block_start/delta/stop` 的 `index` 是否从 0 连续、每个 stop 是否有对应 start、`message_delta` 的 `stop_reason`。
- Windows 环境变量必须区分 系统级/用户级/进程级/Shell 临时级/启动脚本内 set；"配置里有 key 但进程没拿到"是独立一类故障（Category J）。
- 端口与进程：`netstat -ano | findstr :<port>`、`tasklist | findstr <name>`。
- 检查命令优先用当前机器实际可用的（Windows：PowerShell + Git Bash 均可）；不假设 curl 一定可用。

## 7. 修改配置规则（安全协议，改前 11 条）

1. 读取原始文件全文；2. 确认文件用途（project/global/local）；3. 创建备份（**修改前**内容）；
4. 只改必要字段；5. 保留其它 Provider；6. 保留其它模型；7. 保留权限配置；8. 不覆盖无关环境变量；
9. 修改后重新读取核对；10. 验证（格式+环境变量+端点+模型）；11. 失败提供回滚。

**特别规则**：把 LiteLLM `api_key` 改成 `os.environ/XXX` 注入时，**所有**启动该 YAML 的入口（`.ps1`/`.bat`/快捷方式/常驻服务）都必须注入该变量——漏一个入口，该入口就废。

## 8. 验证规则

- "HTTP 200" 只证明端点可达，不证明协议转换正确；必须走"最小请求阶梯"到工具调用层。
- 修完必须复测**原报错场景**（原报错是并行工具触发的就专门测并行工具）。
- 修改 settings 需**重启会话**才生效时，明确告知用户。
- 每个验证结果记为 Confirmed / Likely / Needs Verification。

## 9. 回滚规则

- 每次修改前的备份是唯一回滚源；回滚后重跑最小验证确认恢复。
- 若备份误存了"改动后"而非"改动前"（顺序错误），必须明确告知回滚能力不完整，并提供重建路径。

## 10. 何时读取 references（渐进式披露，别全塞进 SKILL.md）

| 场景 | 读取 |
|---|---|
| 不确定错误分类 / 需要候选根因清单 | `references/error-catalog.md` |
| 读/改 settings、环境变量、Windows 变量层级 | `references/configuration-matrix.md` |
| 模型名映射、unknown model、`[1m]`、LiteLLM model_name vs model | `references/model-mapping.md` |
| 上下文窗口 200K/262K/1M、auto-compact、MAX_CONTEXT_TOKENS | `references/context-window.md` |
| LiteLLM / Gateway 链路诊断 | `references/litellm-diagnostic-chain.md` |
| 需要具体验证命令模板 | `references/verification-methods.md` |
| 找相似案例（仅作 example，不是规则） | `examples/diagnostic-cases.md` |

## 11. Skill 自检清单（创建/更新后过一遍）

- **Claude Code**：Model Catalog / `behavesAs` / `modelPicker` / `modelOverrides` / Model ID / 版本兼容 — 是否都覆盖且标注了"随版本变化需实测"？
- **Context**：200K / 262K / 1M / `[1m]` / `CLAUDE_CODE_MAX_CONTEXT_TOKENS` / `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT` — 是否区分了"模型支持 1M"与"客户端可安全设 1M"？
- **LiteLLM**：`model_list` / `model_name` / `litellm_params` / `model` / `api_base` / `api_key` / Provider / `drop_params` / Streaming / Tool Calling / Fallback / Retry — 是否作为独立模块？
- **Windows**：CMD / PowerShell / `.bat` / `.ps1` / 环境变量五层级 / 子进程继承 / 端口 / 路径 — 是否覆盖"配置有 key 但进程没拿到"？
- **API**：400/401/403/404/429/500/502/503 — 每码是否给了候选根因而非唯一解？
- **安全**：Backup / Minimal Change / Verification / Rollback — 是否写进协议？
- **无硬编码**：当前模型名只出现在 examples，正文无固定模型？
- **无未验证推断当事实**：每条 Confirmed 是否都有对应证据来源？

## 12. 最终诊断报告格式（每次诊断后统一输出）

```markdown
### Error
实际错误与日志（原文引用关键行）。

### Classification
Category（A–M，可多个，标明主分类）。

### Root Cause
根本原因 + 一级/二级症状链（标 Primary vs Secondary）。

### Evidence
支持判断的日志、配置片段、测试结果。

### Confidence
Confirmed / Likely / Needs Verification（逐条标注）。

### Configuration Chain
Claude Code → 各层 → Provider → Model（当前环境实际链路）。

### Affected Configuration
涉及的配置文件、环境变量、进程或服务。

### Fix
具体修复内容（改了什么、为什么）。

### Verification
执行了什么测试。

### Result
实际验证结果（成功/失败 + 输出摘录）。

### Rollback
如果失败如何恢复（备份位置）。

### Next Step
如果仍未解决，下一步检查什么。
```
