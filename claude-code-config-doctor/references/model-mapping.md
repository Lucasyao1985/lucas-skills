# Model Mapping — 模型名识别与映射

## 三个层面的"模型名"（必须区分，404 常出在混淆）

```
客户端请求名（ANTHROPIC_MODEL 值）
   ↓ 可能经过
中间层暴露名（LiteLLM model_name / Gateway model alias）
   ↓ 可能经过
真实上游模型（LiteLLM litellm_params.model / Provider 的 model id）
```

**已验证事实（机制，案例佐证见 examples/diagnostic-cases.md）**：LiteLLM `model_name` 与 `litellm_params.model` 分别承担"客户端暴露名"与"真实上游模型"。形式如 `model_name: "<vendor>/<model>:<tag>"`（客户端用），`model: openai/<vendor>/<model>:<tag>`（`openai/` 前缀表示走 OpenAI 兼容协议伪装）。

## Claude Code 的未知模型机制

| 机制 | 状态 | 说明 |
|---|---|---|
| 内置模型目录 | 已验证事实 | 不在目录的模型按 200k 窗口假设 auto-compact；启动打 DEBUG 警告 |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | 已验证事实 | 报错文案直接给出；需填**查证过**的真实窗口 |
| `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1` | 已验证事实 | 恢复"等 API 报错再压缩"旧行为；不确定窗口时最安全的单变量解 |
| 模型名追加 `[1m]` | 待验证假设（逐端点） | 报错文案提及；**端点是否接受该后缀必须实测**（案例中某端点直接把整个名字透传导致 404 model_not_found） |
| `behavesAs` / `modelPicker` / `modelOverrides` | 高可信推断 | 仅出现在报错文案中（"map it with behavesAs on a modelPicker row"），语义随版本变化，用前实测该版本 |

## 决策矩阵（禁止一种解法套所有模型）

```
模型报错/警告
├─ 先确认：这个名在端点 /v1/models 里存在吗？
│  ├─ 不存在 → Category C：客户端名与端点暴露名不一致 → 中间层加映射，不改端点不改客户端
│  └─ 存在 → 继续
├─ 窗口已知且 ≠200k/1M → MAX_CONTEXT_TOKENS=查证值（项目级）
├─ 窗口未知 → 只加 DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1（不瞎填值）
├─ 窗口=1M 且想按 1M 处理 →
│  ├─ 先实测 `[1m]` 后缀（最小请求）
│  │  ├─ 端点接受 → 用后缀
│  │  └─ 端点 404/透传 → 改用 MAX_CONTEXT_TOKENS=1000000
└─ 官方模型 + 官方登录态 → 以上全都不需要，相关变量是废补丁（应删）
```

## 通用 Provider 覆盖清单（方法论，非固定规则）

DeepSeek / Qwen / GLM / MiniMax / MiMo / Grok / Stepfun / Gemini / 其它 OpenAI-compatible / 其它 Anthropic-compatible Gateway / LiteLLM / One-API / New-API / 本地模型（Ollama 等）。
对每个新 Provider 只假定三件事需要实测：① 暴露的模型名集合；② 支持的窗口；③ 协议转换质量（工具调用/并行工具/SSE index）。不预设协议。

## 映射配置示例（LiteLLM，最小形式）

```yaml
model_list:
  - model_name: "exposed-name-for-client"     # 客户端用这个名字
    litellm_params:
      model: "openai/<vendor>/<real-model>"    # 真实上游 + 协议前缀
      api_base: "https://<gateway>/v1"
      api_key: "os.environ/VENDOR_KEY"         # 不落明文；所有启动入口必须注入该变量
      drop_params: true                        # 避免 LiteLLM 不支持的参数打到上游 400
```
