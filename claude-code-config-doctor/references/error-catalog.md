# Error Catalog — 统一错误分类（Category A–M）

每个 Category 列出：典型报错 → 候选根因（按可能性排序）→ 关键验证手段 → 常见误区。
**所有结论必须按 Confirmed / Likely / Needs Verification 三级标注，禁止把推断当事实。**

## Category A — Claude Code 版本
- 典型：同一配置在旧版本正常、新版本报错（或反之）；`model catalog` 行为变化。
- 候选根因：版本间模型目录内置列表不同；某版本引入/移除的环境变量（如窗口强制校验开关）。
- 验证：`claude --version`；对照报错文案中提到的变量名在该版本是否仍有效（以实际重启测试为准，不要凭记忆）。
- 误区：把版本差异当成配置问题反复改文件。

## Category B — Model Catalog（重点）
- 典型：`"<model>" isn't described by this version's model catalog`；"Until then auto-compact keeps the session within 200k tokens"。
- 机制理解：
  - **已验证事实**（参考案例中实测确认）：Claude Code 对不在其内置目录的第三方模型，按 200k 窗口假设做 auto-compact 决策；报错文案本身给出了两条官方提示路径：给模型名追加 `[1m]` 后缀、或设置 `CLAUDE_CODE_MAX_CONTEXT_TOKENS` 为真实窗口。
  - **高可信推断**：报错文案提到的 `behavesAs` / `modelPicker` / `modelOverrides` 是某版本提供的映射机制（具体语义随版本变化，未逐版本验证——使用前需实测该版本行为）。
- 决策矩阵（不要假定所有未知模型用同一种解法）：
  | 条件 | 推荐方案 |
  |---|---|
  | 模型名确实拼错 / 与端点暴露名不一致 | 修名（Category C） |
  | 端点确实暴露 1M 且客户端语法被端点接受 | `[1m]` 后缀（需实测，见 Category D） |
  | 窗口已知但 <1M（如 262144） | `CLAUDE_CODE_MAX_CONTEXT_TOKENS` = 真实值 |
  | 窗口不确定 | 只用 `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1`（等 API 报错再压缩，最安全，不需要知道窗口） |
  | 端点透传模型名导致上游 404 | 加中间映射层（LiteLLM `model_name` vs `model`），不改客户端模型名 |
- 误区：把 "模型支持 1M" 直接等同于 "客户端可以安全按 1M 处理"——端点可能不识别 `[1m]` 后缀（实测：某 One-API 风格分发器把 `<model>[1m]` 整名透传给后端渠道 → `model_not_found`，因为后端渠道不认识带后缀的名字）。是否接受 `[1m]` 必须逐端点实测。

## Category C — Model Mapping
- 典型：404 / `model_not_found` / "No available channel for model X"。
- 候选根因（排序）：① 客户端请求的模型名与端点暴露名不一致；② 中间层映射丢失/错配；③ 端点分组（group）未开放该模型；④ 上游真的没有该模型。
- 验证：请求端点 `/v1/models`（OpenAI 兼容）列出可用名；再逐个名发最小请求确认 200。
- 误区：看到 404 直接改客户端模型名而不确认端点实际暴露什么。

## Category D — Context Window（200K / 262K / 1M）
- 候选根因排序：① 客户端对未知模型按 200k 假设（见 Category B）；② `MAX_CONTEXT_TOKENS` 填的值与真实窗口不符（过大导致上游 400，过小导致提前压缩）；③ 窗口值猜的而非实测/查证的。
- 已知值参考（仅参考，非事实）：官方 Claude 模型 200K；某模型 Preview 版 262,144 vs 生产/API 版 1M 的区分需以该模型自己的文档+实测为准。
- **Never** 把 "DeepSeek-flash 真实窗口" 这类未查证值当 262000 填进配置而不标注 Needs Verification（案例中 deepseek/grok/Kilo 三个项目的 262000 均为沿用值，未各自查证）。

## Category E — Provider / Endpoint
- 典型：connection refused（本地代理没起）；超时（上游慢/健康探测等上游）；TLS 错误。
- 候选根因：① `ANTHROPIC_BASE_URL` 指向的端口无监听（本地 LiteLLM 没启动——settings 里的 URL 不保证有服务）；② 脚本的等待门槛等上游探测而非等本地进程就绪；③ 网络/代理。
- 验证：`netstat -ano | findstr :<port>` 确认 LISTENING；health/liveliness 接口区分"进程就绪"与"上游可用"。

## Category F — LiteLLM（独立诊断模块）
- 核心概念（必须区分）：
  - `model_name`：**客户端暴露名**（Claude Code 请求时用的名字）。
  - `litellm_params.model`：**真实上游模型**（可能带前缀如 `openai/<vendor>/<model>` 表示"走 OpenAI 兼容协议伪装"）。
  - 两者承担不同角色，404 常出在二者映射错。
  - `api_base` / `api_key` / `drop_params`（丢弃 LiteLLM 不支持的参数避免上游 400）/ `os.environ/<VAR>` 注入 key（YAML 不落明文，但**所有**启动入口必须注入该环境变量）。
- 候选根因：key 未注入到实际进程（见 Category J）；`os.environ/` 漏改某个启动脚本（.bat/.ps1 只改了一个）；端口写死在 YAML 里但实际由命令行 `--port` 决定（YAML 里的 `port:` 可能是废配置）；单模型无 fallback，限流/断供直接报错。
- 完整诊断步骤见 `litellm-diagnostic-chain.md`。

## Category G — Authentication
- 典型：401 / 403 / `invalid_api_key` / `permission_denied`。
- 候选根因排序：① 环境变量未进入目标进程（Windows 多层级变量，见 Category J）；② key 本身过期/无该模型权限；③ 空值占位 key（如 `ANTHROPIC_API_KEY: ""`）残留；④ 端点要求 token 但客户端发的是 Bearer 之外的头。
- 验证：用同进程上下文（启动脚本内 / settings env 里）实测一次最小请求；检查 JWT 类 key 的 exp 字段。
- 误区：看到 401 就"重新写 API Key"——先确认 key 是否真的到达了端点。

## Category H — Streaming / SSE / Tool Calling（重点）
- 典型：`API Error: Content block not found`（**注意：这是 Claude Code 客户端的解析错误，不等于上游返回异常**）。
- 必须先区分的 12 个子类（按诊断顺序）：
  1. 客户端解析问题（客户端 bug / 版本）
  2. Gateway 转换问题（OpenAI→Anthropic 协议转译）
  3. Anthropic SSE 格式问题（事件字段缺失）
  4. OpenAI → Anthropic 转换问题（tool_calls 字段映射）
  5. Tool Calling 问题（单个工具调用）
  6. **Parallel Tool Calling 问题（一次响应多个工具）** ← 案例实测根因所在
  7. `content_block_start` 缺失/乱序
  8. `content_block_delta` 与 start 的 block type 不一致
  9. `content_block_stop` 闭合了从未 start 的 index
  10. block `index` 非 0,1,2... 连续
  11. Streaming 截断（超时/断流，stop_reason 异常或缺失）
  12. 上游模型本身返回异常（偶发空 content、高负载残缺响应）
- **已验证事实（案例实测，可作为方法论而非固定结论）**：并行工具调用时，某 OpenAI→Anthropic 转译层的 SSE `index` 错乱（start 跳到 3、出现未 start 的 index 2 的 stop），客户端按 index 追踪 block 失败 → "Content block not found"。纯文本、单工具调用均正常。
- **高可信推断**：触发时机规律——纯文本对话 ✅、单工具 ✅、并行工具必现（客户端工作流中并行工具调用很常见，所以"对话中才出现"而非"启动即出现"）。
- 验证手段：构造"一次让模型同时调两个工具"的请求，抓原始 SSE，检查 index 序列；重跑 2 次确认可复现。只有证据支持时才判定"上游协议转换问题而非客户端问题"。
- 绕过：`/continue` 或重发（下一轮正常响应即恢复）；根治在服务端。

## Category I — Reasoning / Thinking
- 候选根因：客户端发送的 thinking/effort 相关参数被中间层丢弃或误解；上游不支持 reasoning 返回格式。
- 验证：最小请求带 thinking 参数与非 thinking 对比；看返回中 reasoning 字段是否完整。

## Category J — Windows Environment（独立一类）
- 典型："配置文件里有 API Key，但实际启动代理/客户端的进程没拿到"。
- 变量层级（必须逐一区分）：
  - 系统级 / 用户级（`setx` / GUI，**已打开的进程不会自动拿到新值**，需重启进程或新开 shell）
  - 进程级（启动脚本内 `set` / PowerShell `$env:`，只在该进程树内）
  - Shell 临时级（当前终端 session）
  - 子进程继承（父进程导出后子进程才拿得到；`start`/`Start-Process` 派生的代理进程看的是父进程当时的环境）
- 特殊点：
  - `.bat` 的 `set VAR=...` 写在 `start` 之前才生效于子进程；写在之后无效。
  - `.ps1` 中 `$env:VAR` 在 `Start-Process` 之前设置；被 start 派生进程的读取行为需实测。
  - WSL / Git Bash / 原生路径混用：`/mnt/d/...` 在 Git Bash 与 WSL 里含义不同；权限白名单里 Linux/WSL 路径条目在纯 Windows 本机永远不命中（噪音）。
  - **进程残留**：端口被旧进程占着但配置已改 → 新配置不生效；启动脚本若不 kill 旧进程，永远跑旧实例。
  - **非交互环境差异**：`timeout /t` 在无交互控制台的后台管道中行为异常（可能立即失败或卡住）；`start /min` 派生的进程共享控制台句柄时，外层 `cmd /c` 捕获输出可能挂住——测试脚手架问题，不是 bat 本身问题。

## Category K — JSON / YAML Configuration
- 典型：启动即报 "settings.json 解析失败" / LiteLLM 起不来。
- 候选根因：语法错误（重复 key、缺逗号、尾逗号）；**编辑过程中插入重复行**（案例中编辑 settings 时一次插入导致同一 key 出现两行）；编码问题（UTF-8 BOM）。
- 验证：修改后立即用解析器校验（`python -c "import json;json.load(open(...))"` / `python -c "import yaml;yaml.safe_load(open(...))"`）再谈语义。

## Category L — Process / Port / Startup
- 典型：启动慢（"每次 kill+冷启动"是最大元凶——Python 解释器冷启动 10–30s）；端口占用；代理起不来。
- 标准修法（案例实测有效）：
  1. **热路径复用**：启动前先探 `/health/liveliness`（短超时），活着就跳过 kill+冷启动 → 秒进。
  2. **等待门槛降级**：等"进程就绪（liveliness）"而非等"上游探测成功（healthy_count>0）"——后者依赖外网往返，上游抖动会把启动卡死；首请求自然会激活上游。
  3. **计时日志**：打印就绪耗时，区分"本地启动慢"与"上游探测慢"。
  4. 设总超时（如 90s），超时打 WARN 但不阻断（首请求会暴露真实错误）。

## Category M — Fallback / Retry / Rate Limit
- 典型：429；`:free` 档并发紧，多开客户端互抢配额。
- 注意：限流是服务商行为，配置通常修不了（drop_params 不管用）；只减并发、加付费/别家 fallback 通道、或接受透传错误。
- 候选根因：单通道无 fallback；retry 参数配置与上游 429 语义不匹配。

## 报告用统一分类速查

| Category | 主题 | 第一反应 |
|---|---|---|
| A | 版本 | 先 `claude --version` |
| B | Model Catalog | 看报错自带建议（[1m]/MAX_CONTEXT_TOKENS/映射） |
| C | Model Mapping | `/v1/models` + 最小请求逐名确认 |
| D | Context | 别猜窗口值，查证或只用 DISABLE_ENFORCEMENT |
| E | Provider/Endpoint | netstat + health 分层确认 |
| F | LiteLLM | model_name vs model 对照 |
| G | Auth | 先确认 key 到达端点再怀疑 key 本身 |
| H | Streaming/Tool | 12 子类隔离测试，抓原始 SSE |
| I | Reasoning | 带/不带 thinking 参数对比 |
| J | Windows Env | 变量五层级 + 进程残留 + 非交互差异 |
| K | 语法 | 解析器校验先行 |
| L | 启动 | 热路径 + 门槛降级 + 计时 |
| M | 限流 | 接受服务商限制，只加 fallback |
