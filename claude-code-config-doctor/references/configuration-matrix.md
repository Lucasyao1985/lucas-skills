# Configuration Matrix — 配置文件与环境变量

## 三层 settings 文件（优先级与生效规则）

| 层 | 路径 | 作用域 | 典型内容 |
|---|---|---|---|
| 项目提交版 | `<project>/.claude/settings.json` | 该项目，随仓库 | 团队共享的 env、权限 |
| 项目本地版 | `<project>/.claude/settings.local.json` | 该项目，不入 git | 本机 token、`permissions.allow` 白名单 |
| 用户全局 | `~/.claude/settings.json`（Windows：`C:\Users\<u>\.claude\settings.json`） | 所有目录 | `autoUpdatesChannel`、全局 env、插件 |

**已验证事实（案例中实测确认）**：
- `env` 是**按 key 合并**的，优先级：项目 local > 项目 > 全局。不是整文件覆盖。
- 项目里没设的 key（如 `CLAUDE_CODE_SUBAGENT_MODEL`）会继续从全局生效——"我不用全局"不等于全局 key 全部失效。
- `settings.local.json` 由 Claude Code **自动追加**：权限弹窗选"始终允许"会写入 `permissions.allow`；启用 MCP 会写 `enabledMcpjsonServers`。文件只增不删，跨环境累积（如 Linux/WSL 路径条目出现在 Windows 项目的白名单里）。
- 程序自动更新由全局 `autoUpdatesChannel`（`latest`/`stable`）与 `autoUpdates` 控制，与项目级文件无关。

## 关键环境变量速查

| 变量 | 作用 | 何时需要 | 何时多余 |
|---|---|---|---|
| `ANTHROPIC_BASE_URL` | 指向兼容端点 | 用第三方端点 | 走官方 API 时 |
| `ANTHROPIC_AUTH_TOKEN` | Bearer 头 token | 第三方端点要求 token | 走 OAuth 订阅登录 |
| `ANTHROPIC_API_KEY` | 另一种鉴权头 | 部分端点要求 x-api-key | **空字符串 `""` 是废值，应删** |
| `ANTHROPIC_MODEL` | 主模型名 | 必须与端点暴露名一致 | — |
| `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` | 各档位映射 | 想让所有档位走同一第三方模型 | 官方模型 + 订阅登录 |
| `CLAUDE_CODE_SUBAGENT_MODEL` | 子代理（Agent 工具）模型 | 子代理也要走第三方模型 | 子代理可走官方档时 |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | 告知客户端未知模型的窗口 | 窗口已查证且非 200k/1M | 官方已知模型（内置窗口） |
| `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT` | 未知模型不再按假设窗口硬切，等 API 报错 | 未知模型 + 不确定窗口 | 官方模型 |
| `CLAUDE_CODE_EFFORT_LEVEL` | 推理努力档位（用户偏好） | 用户明确要 | 与任何故障无关，删它不解决报错 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 关非必要流量（遥测等） | 代理场景隐私考量（用户自选） | 与报错无关 |
| `CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK` | 禁止流式失败回退非流式 | 端点对非流式有已知 bug 时 | 无证据不要加（案例中仅在 deepseek 端点加了，agnes 未加） |

## Windows 环境变量五层级（诊断 J 类必查）

1. **系统级**：`[System.Environment]::GetEnvironmentVariable($n,'Machine')`
2. **用户级**：`[System.Environment]::GetEnvironmentVariable($n,'User')`
3. **当前 Shell 临时级**：`$env:VAR`（新开 shell 才继承 1/2；1/2 修改后已开进程拿不到）
4. **进程级（启动脚本内 set / `$env:`）**：只对脚本及其子进程树有效
5. **settings.json 的 `env` 块**：由 Claude Code 注入到其自身进程（不是 OS 变量）

**经典故障**："配置文件里有 API Key，但启动 LiteLLM 的进程没拿到"——key 写在 YAML/脚本 A 里，但实际启动用的是脚本 B（.bat 与 .ps1 孪生入口只改了一个）或 GUI 快捷方式（不继承 shell 变量）。

**诊断手段（Windows 没有直接读取"某进程环境"的内置 API，用以下替代，按可靠性排序）**：
```powershell
# 1) 三层级各查一遍，看 key 到底落在哪层
[System.Environment]::GetEnvironmentVariable('VAR','Machine')   # 系统级
[System.Environment]::GetEnvironmentVariable('VAR','User')      # 用户级
$env:VAR                                                        # 当前 shell

# 2) 启动脚本内 set/赋值后立刻回显（最直接）
cmd: set VAR | findstr VAR
ps:  Write-Host "$env:VAR"

# 3) 端点行为终验（最快信号）：LiteLLM 的 /v1/models 能列出模型 = key 确实被代理拿到
```
判断逻辑：key 只在 YAML/脚本文本里、而 2) 的回显为空或 3) 的端点报 401/模型加载失败 → 确认"配置有 key 但进程没拿到"。

## 清理判断框架（案例验证过的方法）

精简 `permissions.allow` / `env` 时按四类处理：
1. **纯重复项**（同字符串出现两次）→ 直接删。
2. **被更宽泛条目包含**（`Bash(npx skills *)` 被 `Bash(npx *)` 覆盖）→ 删窄的。
3. **本机永不会命中的**（Windows 本机的 Linux/WSL 路径、`sudo`/`apt`/`dpkg`、拼错变量名的条目如 `CLAU_CODE_WORKFLOWS`、shell 内建关键字误批如 `Bash(break)`）→ 删。
4. **疑似误批但可能有效的**（一次性命令、危险命令如 `Bash(rm *)`）→ 标注给用户拍板，不擅自删。
**保留**：用户点名的（如 `mcp__n8n-mcp__*`）、本机有效的常用命令、项目专属 env 补丁。

## 改全局 vs 改项目（归属判断）

- 针对**第三方未知模型**的补丁（MAX_CONTEXT_TOKENS、DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT）→ 放**项目级** settings.local.json，跟模型走，全局保持干净（案例最终结论）。
- 全局只留与供应商无关的运行时参数（如 EFFORT_LEVEL）或用户明确要全局的开关。
- 删掉全局 ANTHROPIC_* 的连锁影响：其它无项目配置的目录回退到官方登录态；未登录会提示 `/login`。改前必须确认用户有可用登录态或项目级覆盖。
