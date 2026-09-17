# Diagnostic Cases — 案例（仅示例，不是规则）

> **用法**：这些案例展示方法论在真实环境中的落点。其中出现的模型名
> （`agnes-3.0-flash`、`deepseek-flash`、`step-3.7-flash`、`grok-4.6` 等）
> 只是当时环境的产物——**不要把它们写成 Skill 的固定模型或结论**。
> 遇到新 Provider 时，按 SKILL.md 的 24 步流程 + 决策树重新走一遍。

---

## Case 1：并行工具调用时 `API Error: Content block not found`（Category H）

**现象**：纯文本 ✅、单工具调用 ✅，对话中模型一次性发多个工具调用时必现。

**诊断路径（方法论落点）**：
1. 最小请求阶梯 ①–⑤ 全绿 → 基础链路没问题，定位到 ⑥ 并行工具。
2. 抓原始 SSE，发现转译层事件 index 错乱：`content_block_start` 从 index 0 跳到 3、
   出现了"从未 start 过的 index 2 的 stop"。客户端按 index 追踪 block → 解析失败。
3. 重跑 2 次同样复现 → 排除偶发，锁定中间层（OpenAI→Anthropic 协议转译）bug。

**结论分层**：
- Confirmed：客户端解析错误由 SSE index 不连续触发（实测 2 次复现）。
- Likely：根因在中间层并行 tool calls 转译，客户端本身无责。
- Needs Verification：需服务端确认转译实现（用户侧只能提供复现序列）。

**处理**：客户端配置无需改动；临时用 `/continue` 或重发绕过；根治需服务端修复。
**经验**：报错出现在"对话中"而非"启动时"，本身就是定位线索（并行工具调用是
agent 工作流中后段才出现的形态）。

## Case 2：未知模型 200k 警告与窗口补丁（Category B/D）

**现象**：`"<model>" isn't described by this version's model catalog ... auto-compact
keeps the session within 200k tokens`。

**诊断路径**：
1. 模型在端点 `/v1/models` 存在 → 不是 404 类问题。
2. 窗口查证：模型卡写 Preview 版 262,144、生产/API 版 1M（不同 checkpoint，
   不能混用数值）→ 填 `CLAUDE_CODE_MAX_CONTEXT_TOKENS` 必须填**查证值**。
3. 实测 `[1m]` 后缀：该端点把整名透传给后端渠道 → `model_not_found`，后缀不可用
   → 改用 `MAX_CONTEXT_TOKENS`（或窗口未知时只用 `DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1`）。

**归属决策**：针对第三方未知模型的窗口补丁放**项目级** settings.local.json（跟模型走），
全局保持干净；与供应商无关的运行时参数才考虑全局。

**教训**：
- 沿用的 262000 若不等于该模型查证值，属于 Needs Verification，不能当事实写进报告。
- 把窗口补丁删干净后，原来靠它兜底的其它未知模型项目会重新出现警告——
  删全局 key 前必须梳理"哪些项目还在依赖它"。

## Case 3：LiteLLM 启动慢 + key 环境变量注入（Category F/L/J）

**现象**：每次启动都要 kill 旧代理 + Python 冷启动（10–30s）+ 等上游健康探测（healthy_count>0，
外网往返，上游一抖动就卡 30s+）。

**修复（热路径复用 + 门槛降级 + 计时）**：
1. 先探 `/health/liveliness`（3s 超时），活着就跳过 kill+冷启动 → 秒进。
2. 冷启动等待门槛从"上游探测成功"降为"进程就绪"（liveliness）；设 90s 总超时，
   超时打 WARN 不阻断（首请求会暴露真实错误）。
3. 打印就绪耗时，区分"本地启动慢"与"上游探测慢"。

**连锁修改（F×J 交叉）**：把 `api_key` 从 YAML 明文改为 `os.environ/VENDOR_KEY` 后，
`.ps1` 和 `.bat` 两个孪生入口**都**要注入该变量；只改一个，另一个入口的代理起不来
（key 缺失 → 表面 401/加载失败）。验证信号：重启后 `/v1/models` 能列出模型 + 最小请求出 token。

**测试陷阱（J 类特殊点）**：非交互/后台管道里跑 `.bat`，`timeout /t` 行为异常、
`start /min` 派生进程共享句柄可致外层 `cmd /c` 挂住——那是**测试脚手架问题**，
不要据此判定 bat 本身坏了；验证 bat 用"交互窗口"或拆分 proxy 段单独测。

## Case 4：权限白名单精简（Category K/维护）

**方法论落点（四类判断）**：
1. 纯重复字符串 → 删；2. 被更宽泛条目包含（`Bash(npx skills *)` ⊂ `Bash(npx *)`）→ 删窄的；
3. 本机永不会命中（Windows 本机的 Linux/WSL 路径、`sudo`/`apt`/`dpkg`、拼错变量名
   `CLAU_CODE_...`、shell 内建误批 `Bash(break)`）→ 删；
4. 疑似误批但可能有效（一次性命令、`Bash(rm *)` 等危险项）→ **标注给用户拍板**，不擅自删。
保留：用户点名的（如 `mcp__n8n-mcp__*`）、本机有效常用命令、项目专属 env 补丁。
**注意**：`settings.local.json` 只增不删是 Claude Code 自动行为，精简后仍会随"始终允许"再膨胀；
防膨胀靠审批时不勾 always，或在 settings.json（非 local）里做权限排除
（排障记录中提到的键名是 `excludePermissions`——**Needs Verification**：该键是否真实存在、
在你的 Claude Code 版本中生效，使用前先加一条排除再观察弹窗行为确认，别当已证实的键名写进配置）。

---

## 反例清单（这些做法在案例中被证明是错的，禁止复制）

- 看到 404 直接改客户端模型名（应先 `/v1/models` 对照端点暴露名，映射在中间层做）
- 窗口未知时把别处沿用的 262000 当事实填进 `MAX_CONTEXT_TOKENS`
- 把 `ANTHROPIC_API_KEY: ""` 空值留着（废值，应删）
- 给"示例模型"占位填进全局 env（没有项目级覆盖的目录会真去调它并报错）
- 改了 YAML 的 `os.environ/` 注入却只补了 `.ps1` 没补 `.bat`
- 非交互管道跑 bat 挂住 → 误判 bat 坏（先排除脚手架）
- 备份存成"改动后"内容再删原件（回滚源失效）
