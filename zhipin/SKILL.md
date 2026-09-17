---
name: zhipin
description: BOSS直聘国内求职搜索。用于在中国招聘平台搜技术岗位（AI Agent/全栈/自动化/前端），或用户提到国内城市+找工作（上海/北京/深圳/杭州求职）。Playwright浏览器自动化绕过反爬，支持经验/学历/薪资筛选，自动比对简历评分，输出与LinkedIn一致的HTML投递列表。国内/中文/城市 = 这个skill；海外/远程/英文/LinkedIn = linkedin-jobs skill。
user-invocable: true
---

# /zhipin — BOSS直聘国内求职

## 触发决策：zhipin vs linkedin-jobs

```
用户提到找工作/求职/搜岗位
├── 国内城市(上海/北京/深圳/杭州/广州/成都...) → zhipin
├── BOSS直聘/BOOS直聘/直聘 → zhipin
├── 海外/远程/Remote/Worldwide/全球 → linkedin-jobs
├── LinkedIn/领英 → linkedin-jobs
├── 英文岗位/外企/硅谷/远程工作 → linkedin-jobs
└── 模糊(如"找AI工作") → 根据上下文判断，国内场景默认zhipin，或两个都跑
```

## 简历关联

简历文件: `C:\Users\Lucas\Desktop\525\领英自动化职位搜索\简历_中文.txt`

核心方向: **AI Agent 开发 / AI 应用开发 / 自动化系统 / 前端**
技能栈: Python, TypeScript, React/Next.js, FastAPI/Node.js, LLM, RAG, Multi-Agent, n8n, Docker, LoRA/QLoRA
背景: 大专学历, 3年独立开发, 离职随时到岗

匹配加分: AI Agent, 自动化, Python, TypeScript, 全栈, LLM/RAG, n8n, Dify, Prompt Engineering
匹配减分: 销售, 客服, Java, 硕士/博士, 传统IT运维

## 执行流程

> **注意**: 以下命令优先用 PowerShell 执行，避免 Bash 下中文参数编码异常。Node 在两种 shell 下均可运行，但关键词含中文时 PowerShell 更可靠。

### Step 0: 验证 Cookie (优先执行)

```powershell
node "C:\Users\Lucas\.claude\skills\zhipin\verify_cookie.js"
```

- ✅ 有效 → 继续搜索
- ❌ 失效 → 告知用户在弹出Chrome中登录 zhipin.com，登录后自动保存

### Step 1: 搜索职位

```powershell
node "C:\Users\Lucas\.claude\skills\zhipin\search.js" "<关键词>" "<城市代码>" <数量> <页码> <经验> <学历> <薪资>
```

默认值: 数量=20, 页码=1, 其他筛选留空=不限
脚本输出标准JSON（code=0表示成功），自动保存更新的cookie

### Step 2: 解析结果 + 比对简历

从JSON提取关键字段:
- `jobName` / `brandName` / `salaryDesc` / `cityName` / `areaDistrict`
- `jobExperience` / `jobDegree` / `skills` / `brandIndustry` / `brandScaleName`
- `bossName` / `bossTitle` / `bossOnline` / `encryptJobId`

按简历方向打分（满分约40，>=25 高匹配，15-24 中等，<15 低匹配）:
- +10: Agent/智能体
- +8: AI/大模型/LLM/RAG/微调/Dify/Native
- +8: 全栈
- +7: 前端/React/TypeScript
- +9: 自动化/n8n/Workflow
- +5: 开发/工程师
- +3: 学历不限/大专
- +3: 经验不限/1-3年
- +3~5: 薪资 > 15K
- -15: 销售/客户/商务/产品经理
- -5: manager/lead/总监/硕士以上
- -4: 5-10年/10年以上

### Step 3: 生成 HTML 投递列表

输出到: `C:\Users\Lucas\Desktop\525\领英自动化职位搜索\Boss直聘\职位投递列表_{YYYYMMDD}.html`

风格与 linkedin-jobs 的HTML保持一致: 深色GitHub主题、分数色标、技能标签、筛选器(高匹配/中匹配/AI Agent/学历友好/已投递)、搜索框、投递按钮。每个岗位链接: `https://www.zhipin.com/job_detail/{encryptJobId}.html`

HTML模板参考 linkedin-jobs 的 gen_html.py 输出格式。

### Step 4: 汇总报告

告知用户:
- 搜索关键词和城市
- 总命中数 → 筛除无关 → 最终保留数
- Top 3-5 高匹配岗位概要
- HTML文件路径
- 提醒: BOSS直聘网页版用"立即沟通"而非"投递简历"

## 参数速查

### 城市代码
| 城市 | 代码 |
|------|------|
| 上海 | 101020100 |
| 北京 | 101010100 |
| 深圳 | 101280600 |
| 广州 | 101280100 |
| 杭州 | 101210100 |
| 成都 | 101270100 |
| 武汉 | 101200100 |
| 南京 | 101190100 |
| 西安 | 101110100 |
| 苏州 | 101190400 |
| 全国 | 100010000 |

### 筛选代码
| 参数 | 代码 |
|------|------|
| 经验 | 103=应届, 104=1-3年, 105=3-5年, 106=5-10年, 107=10年以上 |
| 学历 | 203=大专, 204=本科, 205=硕士, 206=博士 |
| 薪资 | 403=3-5K, 404=5-10K, 405=10-20K, 406=20-50K, 407=50K+ |

## 常见搜索组合

```powershell
# 上海 AI Agent
node search.js "AI Agent" 101020100 20 1 "" "" ""

# 上海 AI应用 + 学历友好(大专)
node search.js "AI应用" 101020100 20 1 "" 203 ""

# 上海 全栈开发 1-3年
node search.js "全栈" 101020100 20 1 104 "" ""

# 高薪AI岗(20-50K)
node search.js "AI" 101020100 20 1 "" "" 406

# 北京 AI前端
node search.js "AI前端" 101010100 20 1 "" "" ""
```

## 公司定向抓取（看某家公司全部在招岗位）

用户给的是一个公司职位页链接（形如 `https://www.zhipin.com/gongsi/job/<公司ID>.html`）时用这个，不要用关键词搜索。

```powershell
# 1. 抓公司职位页（默认海马云，可传任意公司页 URL）
node company_jobs.js
node company_jobs.js "https://www.zhipin.com/gongsi/job/<公司ID>.html?ka=company-jobs"

# 2. 抓每个职位的详细 JD（慢，15 个岗位约 10 分钟）
node company_job_details.js
```

产出：`_company.html`（服务端渲染原始 HTML）、`_jobs.json`（职位列表）、`_jobs_detail.json`（含 JD）。

**解析要点（踩过的坑）**：

1. **职位列表要解析渲染好的 DOM，不要解析压缩 JS**。服务端返回的是 IIFE 压缩代码（`window.__BOSSCOMPANY__=(function(a,b,c...){...})(...)`），字段值全是变量引用（`salaryDesc:a`），解不出来。DOM 里直接有渲染好的卡片。
2. **切块必须用 `class="job-card-box` 做分隔，不能用 `<li>...</li>` 正则**——`tag-list` 里有嵌套 `<li>`，非贪婪正则会提前截断。
3. **页面底部 `class="similar-job-card"` 是"相似职位"推荐，属于其他公司**（微创软件、可可等），必须剔除，否则会把别家的 golang 岗位当成目标公司的。
4. 每岗位技能标签在压缩 JS 的 `skills:[...]` 数组里，字符串字面量可以直接取——这是唯一值得从 JS 里捞的东西。

**数据可得性**（实测）：

| 字段 | 是否可拿到 |
|---|---|
| 岗位名 / 地点 / 经验 / 学历 / 技能标签 / 招聘人 | ✅ 服务端渲染里都有 |
| 详细 JD 正文 | ⚠️ 只能逐个开详情页，且易被限流 |
| 薪资 | ❌ 未完整登录时不返回，`job-salary` 是空标签 |

## Cookie 维护

- 运行 `verify_cookie.js` 检查状态
- 失效时: Chrome打开 zhipin.com → 手动登录 → 删除 `cookies.json` → 重新搜索自动保存
- 有效期约7天，长期不用需重新登录

**两个必须知道的坑**：

1. **浏览器插件导出的 cookie 不含 httpOnly 字段**。Cookie-Editor 这类插件导不出 `wt2` / `zp_at` / `bst`（服务端标记了 httpOnly），所以导出的 cookie 只能让页面加载，**拿不到薪资、也容易触发安全验证**。要完整登录态得从浏览器开发者工具或 Chrome profile 里取。
2. **插件导出的 JSON 直接喂给 Playwright 会崩**：`sameSite: null` 不合法，报 `expected one of (Strict|Lax|None)`。必须先用清洗函数（`verify_cookie.js` 里的 `normalizeCookies`，或 `company_jobs.js` 顶部同名函数）转换成 `{name,value,domain,path,expires}` 形式：`expirationDate` → `expires`，丢掉 `storeId/hostOnly/session`，`sameSite` 只保留合法的三个值。

## 限流警告

BOSS直聘对同 IP 高频访问会直接封禁（页面提示"您的 IP 存在异常行为"，约 2 天自动恢复）。

- 批量抓详情页务必加间隔（≥2s）并限制并发，不要多进程同时跑
- 被封后 `m.zhipin.com` 和 `www.zhipin.com` 一并失效，WebFetch 也拿不到
- 公司职位页（列表）比职位详情页（JD）宽容得多，优先保住列表

