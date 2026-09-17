# Context Window — 200K / 1M / 未知模型窗口

## 要区分的 7 件事（一条链路 7 个断点）

| 项 | 含义 | 验证方式 |
|---|---|---|
| A | Claude Code 对**未知模型**的上下文认知 | 不在内置目录 → 默认 200k 假设（auto-compact 提前触发） |
| B | 上游模型**真实** Context Window | 查官方文档/模型卡；区分 Preview 与生产版（案例：某模型 262,144 vs 1M 是不同 checkpoint） |
| C | Gateway 是否**接受**该模型名 | `/v1/models` + 最小请求 |
| D | Gateway 是否**原样透传**模型名 | 测 `[1m]` 后缀名：被 404 说明透传（案例实测） |
| E | `[1m]` 是否被上游识别 | 与 D 联动；接受才可用，否则走 MAX_CONTEXT_TOKENS |
| F | 环境变量是否**真正进入** Claude Code 进程 | 改 settings.json 后**重启会话**才生效；用报错是否消失做终验 |
| G | 配置影响**项目还是全局** | 项目级 settings.local.json 只对本项目；全局影响所有目录 |

## 核心不等式

> "模型支持 1M" **≠** "Claude Code 可以安全设置 1M"。
> 必须验证完整链路（A→G）。

## 三个数值语义

| 值 | 语义 | 何时用 |
|---|---|---|
| 200k（200000） | 官方标准模型内置窗口；未知模型的默认假设 | 官方模型无需设置 |
| 262144 | 某模型 Preview 版窗口（查证值） | 用查证到的真实数字，别沿用别处的 262000 |
| 1000000 | 1M 版 | 仅当查证上游确为 1M 且 C/D/E 都通过 |

**原则：填 `CLAUDE_CODE_MAX_CONTEXT_TOKENS` 前先查证窗口；查不到就只用 `DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1`，不瞎填数字。**（案例教训：deepseek/grok/Kilo 三处的 262000 是沿用值，各自窗口未查证——属于 Needs Verification，不能当事实。）

## 精确性细节

- 模型卡写 262,144 就填 `262144`；填 `262000` 差 44 个 token 无实际影响（案例中确认可接受，但精确值更对）。
- 1M 版：改法优先 `CLAUDE_CODE_MAX_CONTEXT_TOKENS=1000000`，而不是在模型名上硬加 `[1m]`（端点可能不认后缀）。

## 窗口错误的级联链（Root Cause First 范例）

```
Unknown Model（客户端不认识）
  → 拿不到正确模型元数据
  → Context Window 按 200k 假设
  → Auto-Compact 提前发生
```
**Auto-Compact 提前是症状，不是根因**——修根因（MAX_CONTEXT_TOKENS / DISABLE_ENFORCEMENT / 映射）而非调压缩阈值。
