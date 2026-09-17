# runninghub-workflow-extractor

Claude Skill：自动分析 RunningHub（runninghub.ai / runninghub.cn）AI 应用页面，提取其内部隐藏的 ComfyUI 工作流 JSON。

> 安装说明：本 README 供人类阅读 / GitHub 分发用。按 Anthropic 规范，上传到 Claude.ai 的 skill 包内不需要 README.md，核心文档都在 `SKILL.md` 与 `references/` 中。

## 它解决什么问题

RunningHub 的「AI App」是套在 ComfyUI 工作流外面的一层表单封装：

- 页面 URL 形如 `/ai-detail/<webappId>`，只有表单界面，没有画布；
- 底层 `workflowId` 被服务端私有化——匿名和普通登录用户调 `/api/webapp/detail` 都拿到 `workflowId: null`；
- 工作流内容接口（getContent 等）匿名访问返回 `TOKEN_MISSION`。

本 Skill 固化了从实战案例中验证过的完整提取路径，包括黄金通道 `/api/workflow/copy`（复制公开工作流时直接返回完整 workflowContent）和 workflowId 隐藏时的**节点指纹匹配法**。

## 目录结构

```
runninghub-workflow-extractor/
├── SKILL.md                        # 主指令文件（frontmatter + 执行流程）
├── scripts/
│   ├── rh_extract.py               # 端到端提取流水线（探测→匹配→copy→校验→保存）
│   ├── rh_probe.py                 # 单接口调试器（带认证头）
│   ├── rh_validate.py              # 工作流 JSON 校验 + 指纹比对
│   └── fix_mojibake.py             # UTF-8 双重编码乱码修复（纯本地无损）
└── references/
    ├── api-endpoints.md            # 全部已确认端点、参数、错误语义
    ├── auth-and-cookies.md         # Rh-Accesstoken / Bearer / Cookie 凭证体系
    ├── frontend-analysis.md        # 前端 chunk 下载与 grep 模式
    ├── fingerprint-matching.md     # workflowId 隐藏时的指纹匹配方法
    └── case-study-minimax-h3.md    # 完整实战案例复盘
```

## 快速使用（对话触发）

对 Claude 说：

- 「下载这个工作流 https://www.runninghub.ai/zh-cn/ai-detail/xxxx」
- 「帮我提取这个 RunningHub AI App 的隐藏工作流」
- 「分析这个页面是 AI App 还是普通工作流，并把 JSON 拿出来」

需要你提供登录凭证之一（自动化登录会被风控拦截）：

- F12 Console 执行 `localStorage.getItem('Rh-Accesstoken')` 把 JWT 发给 Claude；或
- 用 Cookie 导出插件导出整包 Cookie JSON 文件。

## 命令行直接使用脚本

```bash
# 端到端提取（AI App）
python scripts/rh_extract.py https://www.runninghub.ai/ai-detail/<id> \
  --token <JWT> --owner-user-id <发布者userId> --out ./out --report

# 公开工作流直接复制
python scripts/rh_extract.py https://www.runninghub.ai/workflow-detail/<id> --out ./out

# 单接口调试
python scripts/rh_probe.py /api/webapp/detail '{"webappId":"<id>"}' --token <JWT>

# 校验 + 指纹比对
python scripts/rh_validate.py out/工作流.json --fingerprint 14,118,129,142,86,79

# 修复提取结果中的中文乱码
python scripts/fix_mojibake.py out/工作流.json
```

## 安全边界

- 运行类操作（立即运行等）会消耗账户额度，Skill 会先征求同意；
- token/Cookie 只用于调用接口，不会写入报告或明文存盘；
- copy 操作会在你的工作流空间留下测试副本，记得清理。
