---
name: linkedin-jobs
description: LinkedIn领英海外/远程求职搜索。用于找海外Remote/Worldwide的AI Engineer/AI Agent岗位，或用户提到领英/LinkedIn找工作时使用。双线搜索（上海国内+全球远程），关键词覆盖AI Builder/Vibe Coding/AI Native/Agentic AI，自动过期检测，比对简历评分，输出带筛选器的HTML投递列表。海外/远程/英文/LinkedIn = 这个skill；国内/中文/城市/BOSS直聘 = zhipin skill。
metadata: {"openclaw":{"emoji":"💼","requires":{"bins":["python","chrome"]},"os":["win32"]}}
---

# /linkedin-jobs — LinkedIn 领英求职搜索

## 触发决策：linkedin-jobs vs zhipin

```
用户提到找工作/求职/搜岗位
├── 领英/LinkedIn → linkedin-jobs
├── 海外/远程/Remote/Worldwide/全球 → linkedin-jobs
├── 英文岗位名(AI Engineer/AI Agent/Full Stack)→ linkedin-jobs
├── 硅谷/旧金山/湾区/远程工作 → linkedin-jobs
├── 国内城市(上海/北京/深圳...) → zhipin
├── BOSS直聘 → zhipin
└── 模糊(如"找AI工作") → 根据上下文判断：
    - 英文环境/远程偏好 → linkedin-jobs
    - 中文环境/国内城市 → zhipin
    - 无法判断 → 两个都跑
```

## 简历关联

> ⚠️ **2026-09-10 核实：下面这个简历路径已失效**（`C:\Users\Lucas\Desktop\525\领英自动化职位搜索\` 目录不存在）。
> 当前有效简历：`C:\Users\Lucas\WorkBuddy\<工作区>\徐伟_RunningHub_求职材料.pdf`。
> 注意：`search.py` 的评分是**按硬编码关键词**（`CORE_SKILLS` / `AI_BUILDER_BONUS` / `PENALTY_TITLES`）算的，**不读简历文件**，所以路径失效不影响搜索，只影响人工比对。

核心方向: AI Agent 开发 / AI 应用开发 / 自动化系统 / 前端
技能栈: Python, TypeScript, React/Next.js, FastAPI/Node.js, LLM, RAG, Multi-Agent, n8n, Docker, LoRA/QLoRA, ComfyUI, AIGC
求职状态: 离职，随时到岗，独立开发经验

## 执行方式

> **⚠️ 必须用 PowerShell 执行**。Bash 工具（Git Bash）无法解析反斜杠路径（`D:\Conda`），且 `--output-dir` 参数中的中文会因 UTF-8→GBK 编码不一致导致乱码。PowerShell 原生支持 Windows 路径和 Unicode，无此问题。

### 完整流水线 (搜索 + 过期检测 + HTML)

```powershell
D:\Conda\python.exe "C:\Users\Lucas\.claude\skills\linkedin-jobs\pipeline.py"
```

### 仅搜索 (不生成HTML，快速查看)

```powershell
D:\Conda\python.exe "C:\Users\Lucas\.claude\skills\linkedin-jobs\search.py"
```

### 跳过搜索 (使用缓存结果生成HTML)

```powershell
D:\Conda\python.exe "C:\Users\Lucas\.claude\skills\linkedin-jobs\pipeline.py" --skip-search
```

### 自定义输出目录

```powershell
D:\Conda\python.exe "C:\Users\Lucas\.claude\skills\linkedin-jobs\pipeline.py" --output-dir "C:\Users\Lucas\Desktop\525\领英自动化职位搜索"
```

## 数据流

```
cookies.txt ──→ search.py ──→ matched_jobs.json
                                    │
                check_expired.py ← li_at cookie (requests)
                                    │
                                    ▼
                             expired_ids.json
                                    │
                gen_html.py ───────┘
                         │
                         ▼
           职位投递列表_{日期}.html  → 桌面目录
```

## 脚本说明

| 脚本 | 功能 | 关键技术 |
|------|------|----------|
| `pipeline.py` | 编排完整流水线 | 串联三步 |
| `search.py` | Playwright搜索LinkedIn | 仅最近7天，每次全新不累积 |
| `check_expired.py` | requests批量检测过期 | www归一化 + job ID去重 |
| `gen_html.py` | 去重 + 评分 + HTML生成 | URL/公司去重 + 过期过滤 |

## 搜索关键词覆盖

| 区域 | 覆盖 |
|------|------|
| 🇨🇳 上海 | AI Agent开发, 大模型AI开发, AI应用开发, 自动化开发, 前端React |
| 🌍 Worldwide | AI Agent Engineer Remote, AI Builder Product Engineer, AI Native Full Stack, AI Automation Engineer, Vibe Coding AI Developer, Generative AI Engineer, Claude AI Developer, Cursor AI Engineer 等 |
| 🌉 硅谷/美国 | AI Agent Engineer, AI Builder Product Engineer, AI Native Full Stack, AI Automation Engineer, Generative AI Engineer 等 |

## 评分规则 (与zhipin对齐)

- AI Builder 信号 → +25分: ai native, ai builder, product engineer, vibe coding, claude, cursor, copilot, founding engineer
- 核心技能命中 → +10分: ai agent, n8n, react, python, llm, full stack, typescript, next.js, automation, workflow
- 传统门槛 → -15分: senior, 5+ years, bachelor required, master required
- 排除公司: PwC, Deloitte, Accenture, Infosys, IBM, SAP, 埃森哲等传统咨询/外包

## 去重策略 (三层)

1. **URL去重**: 相同URL(忽略query string)只保留一条
2. **公司去重**: 相同公司只保留最高分岗位(归一化后比较，忽略Inc/Ltd/LLC后缀)
3. **过期过滤**: requests请求URL，检测 `"no longer accepting applications"`

## 关键设计决策

- **7天过滤**: `f_TPR=r604800` 只搜最近一周
- **www归一化**: 过期检测统一用 `www.linkedin.com` 避免子域名CDN缓存差异
- **requests检测过期**: LinkedIn渲染页面无法用Playwright `inner_text()` 捕获过期标记，用requests + li_at直接读HTML源码 → 100%检测率
- **不累积**: 每次全新搜索，避免历史过期数据越积越多

## HTML 输出功能

- 筛选器: 高匹配 / 中匹配 / AI Builder / 国内 / 远程 / 美国 / 已投递
- 搜索框: 按公司/职位/技能实时过滤
- 技能标签: 🔑 绿色高亮AI Builder关键技能
- 投递按钮: 点击新标签页打开LinkedIn
- 深色GitHub Dark主题
- 输出路径: `C:\Users\Lucas\Desktop\525\领英自动化职位搜索\职位投递列表_{YYYYMMDD}.html`

## Cookie 维护

- `cookies.txt` 位于skill目录下（**当前缺失，2026-09-10 核实**，跑之前需先放一份）
- 关键Cookie: `li_at`(认证token，有效期约1年)
- 导出方式: Chrome → F12 → Application → Cookies → 全选复制
- 格式: `name\tvalue\tdomain\tpath\texpires`(制表符分隔)；解析按 9 列切，第 8 列 `httpOnly`、第 9 列 `secure`
  （`parse_cookies()` 里 `expires` 列若是中文「会话」按 session 处理，日期格式 `YYYY-MM-DD HH:MM:SS`）
- ⚠️ Cookie-Editor 导出的 **JSON 格式不被识别**，见下方「Cookie 格式坑」

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 浏览器跳转login | Cookie过期**或被风控注销** | 重新导出；导出后立刻用，别反复重试 |
| `curl` 302 到 linkedin.cn | 本机 CN IP 被地理重定向 | 免登录接口不可用，改走服务端抓取 |
| `addCookies` 报 sameSite 错误 | 用了 Cookie-Editor JSON 格式 | 做归一化：`no_restriction`→`None`，`null`→丢弃 |
| 搜索结果0 | LinkedIn UI更新选择器 | 检查search.py中CSS选择器 |
| expired检测全0 | 用了Playwright | 用 check_expired.py (requests版) |
| HTML打开无变化 | 浏览器缓存 | Ctrl+Shift+R 刷新 |
| li_at过期 | 超1年 | 重新导出Cookie |

---

## 公司定向查询（不看岗位，只查某家公司）— 2026-09-10 新增

场景：「LinkedIn 上有没有 XX 公司？」「帮我查 XX 公司在领英的岗位」。
**这种情况不要跑 search.py 全流水线**，直接用下面的免登录路径，快且不消耗 cookie。

### ⚠️ 前置认知：本机直连领英会被地理重定向

本机在中国大陆，`curl` 直连 `www.linkedin.com/jobs-guest/...` 会返回：

```
HTTP 302  Location: https://www.linkedin.cn/incareer/home
```

**linkedin.cn（领英职场 InCareer）已于 2023 年停运**，域名解析不了 → 请求全部失败。
所以：**游客接口（`jobs-guest`、免登录搜索页）从本机不可用。**

### ✅ 可用路径一：服务端抓取（推荐，无需 cookie）

`WebFetch` 工具在服务端执行，出口 IP 不在中国，**能正常拿 LinkedIn 公开页**。实测可用：

| 目标 | URL 模板 | 是否可抓 |
|---|---|---|
| 公司公开页 | `https://www.linkedin.com/company/<slug>/` | ✅ 可抓（含行业/总部/官网/关联员工数/前 4 位员工） |
| 岗位搜索页 | `https://www.linkedin.com/jobs/search?keywords=<kw>&location=Worldwide` | ✅ 可抓（约 60 条/页） |
| 按公司 ID 过滤岗位 | `https://www.linkedin.com/jobs/search?f_C=<companyId>&location=Worldwide` | ✅ 可抓（**判断「这家公司有没有在招」最权威**） |
| 公司 `/jobs/` 子页 | `.../company/<slug>/jobs/` | ❌ 登录墙 |
| 公司人员全量页 | `.../company/<slug>/people/` | ❌ 登录墙 |
| 个人主页 | `https://www.linkedin.com/in/<slug>` | ❌ 登录墙 |
| 公司名搜索 | `https://www.linkedin.com/search/results/companies/?keywords=<kw>` | ❌ 登录墙 |

**拿 `companyId` 的办法**：先抓公司公开页，HTML 里搜 `facetCurrentCompany%3D%255B<数字>%255D`，那串数字就是。

### 可用路径二：Playwright + cookie（能拿登录态内容，但脆弱）

**LinkedIn 会主动注销被非浏览器环境使用的 `li_at`。** 实测：

```
第 1 次运行：[1] 登录态检查  url=.../feed/          → 可访问搜索页（约 2-3 次页面加载后失效）
第 2 次运行：[1] 登录态检查  url=.../login/?session_redirect=... → 登录墙
```

原因：同机出口是 CN IP + headless Chromium 指纹与导出 cookie 的浏览器不一致 → 风控 kill 掉会话。
**不是账号问题。**

**因此：拿到新 cookie 后必须「单次运行、最小请求」**——一次跑完，页面加载控制在 3 次以内（如：公司人员页 → 岗位页 → 目标人档案页）。不要反复重试。

### ⚠️ Cookie 格式坑（两种格式，必须分清）

| 来源 | 格式 | 本 skill 是否认 |
|---|---|---|
| Cookie-Editor 扩展「导出 JSON」 | JSON 数组，字段 `expirationDate` / `sameSite:"no_restriction"` / `hostOnly` / `storeId` / `session` | ❌ **`parse_cookies()` 不认**，它按 TAB 分行解析 |
| 手工从 F12 复制 | TAB 分隔：`name\tvalue\tdomain\tpath\texpires` | ✅ 认 |

**JSON 转 Playwright 合法格式**必须做这些归一化，否则 `addCookies` 直接抛错：

```python
ss = c.get("sameSite")
if ss == "no_restriction": ss = "None"   # 关键！不是 "None" 就是非法值
if ss in ("Strict","Lax","None"):
    item["sameSite"] = ss
    if ss == "None": item["secure"] = True  # sameSite=None 必须配 secure
# expirationDate → expires（float 秒）；丢弃 hostOnly / storeId / session
```

否则报：`addCookies: cookies[N].sameSite: expected one of (Strict|Lax|None)`。
（同一个坑在 `zhipin` skill 的 `verify_cookie.js` 里也踩过，那边有 `normalizeCookies()` 可参考。）

### 关键词搜索的假阳性

**用公司名搜岗位会返回大量无关结果。** 例：搜「海马云」→ 返回 1000+ 条 Google/AWS/NVIDIA/阿里云 的岗位，因为 LinkedIn 按「云」字联想匹配。
**判断「某公司有没有在招」必须用 `f_C=<companyId>` 过滤，不要用关键词搜索。**

## 注意事项

- search.py期间不要操作Chrome窗口
- 搜索间隔1.5秒，过期检测0.3秒
- **不要自动投递**: LinkedIn对Apply有最强反自动化保护，会被challenge-dialog拦截
- Easy Apply岗位过期极快(1-2天~70%失效)，建议每天运行
