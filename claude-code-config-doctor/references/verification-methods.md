# Verification Methods — 可执行验证手段（Windows 优先）

原则：**优先用当前机器实际可用的方法**；"文件存在"≠"配置正确"；"HTTP 200"≠"链路正常"。每条验证标注它证明了什么。

## 1. 版本与基础

```powershell
claude --version          # 确认真实版本（模型目录行为随版本变化）
```

## 2. 配置文件

```powershell
# JSON 语法（settings*.json）
python -c "import json,sys;json.load(open(r'path\settings.local.json',encoding='utf-8-sig'))"
# 或 PowerShell
Get-Content settings.json -Raw | ConvertFrom-Json
# YAML 语法（litellm config）
python -c "import yaml;yaml.safe_load(open(r'path\litellm_config.yaml'))"
```
→ 验证的是 **K 类（语法）**，不是语义正确。

## 3. 环境变量（Windows 五层级）

```powershell
# 系统级 / 用户级 / 进程级
[System.Environment]::GetEnvironmentVariable('VAR','Machine')
[System.Environment]::GetEnvironmentVariable('VAR','User')
$env:VAR                       # 当前 shell
# 启动脚本内立即回显
Write-Host "KILO_API_KEY=$env:KILO_API_KEY"
```
→ 验证 **J 类**："配置文件里有 key 但进程没拿到"。

## 4. 端口与进程

```powershell
netstat -ano | findstr :4008     # LISTENING？PID？
tasklist | findstr litellm
tasklist | findstr <PID>
# 杀残留（危险，先确认 PID 身份）
taskkill /F /PID <pid>
```

## 5. LiteLLM 健康

```bash
curl -s http://127.0.0.1:4008/health/liveliness   # 进程就绪
curl -s http://127.0.0.1:4008/health              # healthy_count>0 = 上游探测通过
curl -s http://127.0.0.1:4008/v1/models            # 暴露的模型名（key 是否注入成功的最快信号）
```

## 6. 最小请求阶梯（模型验证核心）

用 curl 打端点（`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`），逐步加压：

```
① 非流式最小请求          → 证明端点+模型+key 通
② 流式最小请求            → 证明 SSE 基础格式
③ 单工具调用（非流式）    → 证明 tool_use 块
④ 单工具调用（流式）      → 证明 input_json_delta 等
⑤ 多轮 tool_result 回传   → 证明多轮上下文
⑥ 并行工具调用（一次响应多个工具）← 重灾区，专门抓 SSE index
```

每步失败即定位到该层（H 类 12 子类隔离）。

**SSE 检查要点**（对 ⑥ 抓原始事件）：
- 每个 `content_block_stop(index=N)` 必须有对应 `content_block_start(index=N)`
- start 的 index 序列必须 0,1,2... 连续，不得跳号
- 出现"未 start 的 index 的 stop"或"start 跳号" = 转译层 index 错乱 → `Content block not found`
- `message_delta.stop_reason` 应为 `end_turn`/`tool_use`，异常/缺失 = 截断

## 7. 实测未知模型窗口（不瞎填）

```
- 查模型卡/官方文档（Preview 版 vs 生产版可能不同）
- 端点 /v1/models 通常只有名字没有窗口 → 查不到就不填 MAX_CONTEXT_TOKENS，只用 DISABLE_ENFORCEMENT=1
```

## 8. 实测 `[1m]` 后缀是否被接受

```bash
curl ... 请求 body 里 model 写 "<name>[1m]"
# 接受 → 正常出 token；404 model_not_found → 端点透传，改用 MAX_CONTEXT_TOKENS=1000000
```

## 9. 验证 Claude Code 侧

- 改完 settings 必须**重启会话**（env 变化才进进程）。
- 重启后原 DEBUG 警告是否消失。
- 原报错场景复测（原报错是并行工具触发的就专门测并行工具）。

## 10. 结果记录

每个验证结果记为 **Confirmed / Likely / Needs Verification**，写进最终报告的 Evidence + Confidence 段。

## 反面清单（禁止的验证）

- ❌ 文件存在 = 配置正确
- ❌ 单条 curl 200 = 完整链路正常（必须走阶梯到 ⑥）
- ❌ 未查证的窗口值填进 MAX_CONTEXT_TOKENS 当事实
- ❌ 把 `[1m]` 后缀默认写进所有模型名（逐端点实测）
- ❌ 非交互管道跑 `.bat` 的 `timeout /t` / `start /min` 卡住就判定 bat 坏了（先排除脚手架问题）
