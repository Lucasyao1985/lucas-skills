# LiteLLM 诊断链 — 独立诊断模块

## 调用链（本 Skill 必须能处理完整链路）

```
Claude Code
    ↓ (Anthropic 协议, ANTHROPIC_BASE_URL)
LiteLLM Proxy (本地, e.g. 127.0.0.1:4008)
    ↓ (OpenAI / Anthropic 兼容, api_base)
Gateway / Provider
    ↓
Actual Model
```

## 配置解剖（`litellm_config.yaml` / `config.yaml`）

| 字段 | 角色 | 易错点 |
|---|---|---|
| `model_list[].model_name` | **客户端暴露名** | 必须与 Claude Code 侧 ANTHROPIC_MODEL 一致，否则 404 |
| `model_list[].litellm_params.model` | **真实上游模型**（可带 `openai/` 等前缀） | 前缀决定协议伪装；与 `model_name` 是两层，别混淆 |
| `litellm_params.api_base` | 上游地址 | 写错 provider 的端点 |
| `litellm_params.api_key` | 上游 key | 明文联机泄密；推荐 `os.environ/VAR` |
| `litellm_settings.drop_params` | 丢不支持参数 | 缺它 → 上游 400（thinking/caching 等参数） |
| `litellm_settings.port` | **常是废配置** | 实际端口由命令行 `--port` 决定；YAML 里写了不一定生效 |
| `litellm_settings.set_completed_requests_to_idle` | 内部调度 | 单模型单通道无收益，可删 |

## 环境变量注入的连锁规则（J 类 + F 类交叉）

一旦把 `api_key` 改成 `os.environ/VENDOR_KEY`：
- **所有**启动该 YAML 的入口都必须注入该变量：`.ps1`（`$env:`）、`.bat`（`set`，写在 `start` 前）、快捷方式、常驻服务。
- 漏一个入口 → 该入口下 LiteLLM 解析不到 key，模型加载失败（表面是 401/5xx，实际是 key 缺失）。
- 验证：`/v1/models` 能列出模型名 = key 注入成功的最快信号（案例实测：重启后最小请求出 token 即证明）。

## 常见故障模式

| 现象 | 候选根因 | 验证 |
|---|---|---|
| 代理起来但模型 404 | `model_name` 与客户端请求名不一致 | 对照两侧名字 |
| 上游 400（参数不识别） | 缺 `drop_params` | 加 `drop_params: true` |
| 上游 401 | key 没到进程（见上） | 最小请求 + 看 key 在不在 |
| 启动卡 30s+ | 等待门槛是"上游探测 healthy_count>0"而非本地进程就绪 | 改等 `/health/liveliness`（见 L 类） |
| 限流 429 | `:free` 档配额紧、多开客户端互抢 | 服务商行为，配置修不了；加付费 fallback |
| 单模型无 fallback | 断供直接全挂 | 加付费/别家通道做 fallback（可选） |
| OpenAI→Anthropic 转换坏 | 并行工具调用时 SSE index 错乱（Category H） | 抓原始 SSE 看 index 序列 |

## 验证阶梯（真实可执行）

1. 语法：`python -c "import yaml;yaml.safe_load(open('config.yaml'))"`
2. 起得来：`/health/liveliness` 200
3. key 到了：`/v1/models` 列出目标 `model_name`
4. 能出 token：最小非流式请求（`/v1/messages` 走 Anthropic 兼容，或 `/v1/chat/completions` 走 OpenAI）
5. 流式正常：SSE 事件完整、index 连续
6. 工具调用正常：单工具 → 并行工具（并行是重灾区）

**"文件存在" ≠ "配置正确"；"HTTP 200" ≠ "完整链路正常"。** 逐层走，每层都有对应验证。

## 多语言/多入口注意

- 案例用 Conda 环境 `D:\Conda\envs\litellm-proxy\Scripts\litellm.exe` 启动（Windows）。
- `.bat` 与 `.ps1` 是孪生入口，改一个必改另一个（否则某入口的 key 注入缺失）。
- 非交互/后台跑 `.bat` 时 `timeout /t` 行为异常、`start /min` 子进程共享句柄致外层挂住——是测试脚手架问题，不是 bat 缺陷（J 类特殊点）。
