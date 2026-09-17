# Lucas Skills

个人 Claude / Agent 技能（Skills）合集。每个目录是一个独立 skill，入口文件为 `SKILL.md`，可整体拷贝到 `~/.claude/skills/`（或对应 agent 的 skills 目录）使用。

## 目录总览（50 个 skills）

### 媒体下载与处理

| Skill | 说明 |
|---|---|
| `youtube-video-downloader` | 用 yt-dlp 下载 YouTube 视频/Shorts 最高画质 MP4 |
| `youtube-desc-downloader` | 批量下载 YouTube 视频简介/描述到本地 txt |
| `tiktok-video-downloader` | 无水印下载 TikTok 视频（解析 playAddr + 浏览器指纹绕反爬） |
| `x-video-downloader` | 下载 X/Twitter 帖子中的视频、图片、GIF、长文配图与文档 |
| `xiaohongshu-note-downloader` | 下载小红书笔记：原图、无水印 MP4（最高 4K）、文本元数据 |
| `instagram-downloader` | curl_cffi 绕反爬，分页下载 Instagram 用户全部帖子图片/视频 |
| `wechat-article-downloader` | 下载微信公众号文章 |
| `youvibe-downloader` | 下载 youvibe.run 项目页图片与文件（自动处理 PoW 防护） |
| `m3u8-to-mp4` | 将 .m3u8 + .ts 分段视频（如迅雷保存的 HLS）无损合并为 MP4 |
| `to-jpg` | 高质量批量转换任意图片格式为 JPG（WEBP/PNG/GIF/BMP/TIFF/JXL/AVIF/HEIC） |
| `png-sequence-to-gif` | 图片序列 / 视频转 GIF |
| `crop-to-9x16` | 按任意宽高比居中裁切图片（默认 9:16），不压缩分辨率 |

### MiniMax H3 视频 / 图像提示词

| Skill | 说明 |
|---|---|
| `minimax-h3-prompt-writing` | 撰写 H3 视频提示词（T2VA/I2VA/FL2VA/L2VA/Ref2VA 全模式） |
| `minimax-seedance-h3-prompt-converter` | 将即梦 Seedance 2.0/2.5 提示词转写为 H3 提示词 |
| `minimax-video-prompt-template` | 一键生成「生视频提示词生成器设定」模板（H3 官方格式） |
| `minimax-image-prompt-template` | 一键生成「生图提示词生成器设定」模板（105 个官方 skill 提炼） |
| `h3-prompt-formatter` | 将原始内容整理为【原始输入】+【生成结果】统一 H3 格式 |
| `h3-prompt-journal` | H3 提示词写作日志/素材沉淀 |
| `minimax-h3-character-replacement` | 参考图人物替换到参考视频（Ref2VA 提示词生成） |
| `funny-face-doll` | 鬼脸娃娃风格 I2VA 提示词（表情变化 + 大道具跳剪短视频） |
| `minimax-cface` | 可爱脸病毒短视频提示词（角色 IP 二创、Meme 风格） |
| `text-orbit-mv` | 文字环绕风格时尚 MV 完整英文提示词生成 |
| `minimax-papercraft-stop-motion` | 纸艺定格动画科普视频制作方案与提示词 |
| `minimax-brand-promo-video` | 品牌/产品宣传短视频全流程（叙事、分镜、素材、成片审查） |
| `minimax-coop-game-intro` | 双人合作游戏开场菜单动画提示词 |
| `minimax-3d-animation-short` | 3D 动画短片提示词 |
| `minimax-handdrawn-live-video` | 手绘风实景视频提示词 |
| `minimax-minimalist-product-ad` | 极简风产品广告视频提示词 |
| `minimax-music-video-subtitle` | 音乐 MV + 字幕视频提示词 |
| `minimax-paper-collage-explainer` | 纸拼贴风格讲解视频提示词 |
| `sprite-gen` | 像素 sprite / 序列帧生成 |
| `line-sticker-set-prompt` | 单角色图 → 16 张 LINE 风格表情包贴纸（4x4 网格）提示词 |

### 工作流提取 / 发布

| Skill | 说明 |
|---|---|
| `runninghub-workflow-extractor` | 从 RunningHub AI App 页提取隐藏的 ComfyUI 工作流 JSON |
| `libtv-workflow-toolkit` | 下载/导入 LibTV（LiblibAI 视频画布）工作流与全部素材 |
| `openart-prompt-extractor` | 提取 OpenArt 模板页内藏的提示词文本（RSC flight payload 解析） |
| `civitai-publisher` | Civitai 全自动发布：API 创建模型/版本 + 浏览器自动上传 ZIP 与预览图 |

### 求职 / 数据 / 信息

| Skill | 说明 |
|---|---|
| `linkedin-jobs` | LinkedIn 海外/远程 AI 岗位搜索，输出 HTML 投递列表 |
| `zhipin` | BOSS 直聘国内技术岗位搜索（Playwright 绕反爬），同格式投递列表 |
| `imdb-movie-discovery` | IMDB 电影/剧集/演员/导演查询与推荐 |
| `kaggle-competitions` | Kaggle 竞赛查询、价值评估与参赛规划 |
| `shanghai-weather` | 上海天气（上海市气象局官网接口）：观测/预报/预警/生活指数 |
| `jd-price` | 京东商品价格分析、对比、监控与 HTML 报告 |
| `x-post-analyzer` | 抓取并结构化分析 X/Twitter 帖子（文本/媒体/互动数据） |
| `reddit-seed-user-research` | 为指定项目在 Reddit 找目标用户并起草推广回复 |
| `reddit-deal-closer` | Reddit 销售/成交话术 |
| `crypto-signal-agent` | 多资产加密货币方向信号引擎（14 因子加权评分，Binance+Bybit 双源） |

### 彩票走势分析

| Skill | 说明 |
|---|---|
| `lottery-skills` | 彩票技能包总入口 |
| `lottery-ssq` | 双色球：多窗口走势、特征画像推荐、蓝球独立预测 |
| `lottery-daletou` | 大乐透：体彩官方 API，遗漏/冷热号/奇偶比等多维分析 |
| `lottery-pl3` | 排列3 走势分析与号码推荐 |
| `lottery-pl5` | 排列5 五位数据分析 |

### Claude Code 工具

| Skill | 说明 |
|---|---|
| `claude-code-upgrade` | 升级 Claude Code CLI（诊断安装方式并处理常见坑） |
| `claude-code-config-doctor` | 诊断修复 Claude Code 配置与模型连接全链路错误 |

## 使用方法

将本仓库克隆或拷贝到 skills 目录即可：

```bash
git clone https://github.com/Lucasyao1985/lucas-skills.git
# Claude Code:
cp -r lucas-skills/* ~/.claude/skills/
# 其他 agent（如 ZCode）:
cp -r lucas-skills/* ~/.agents/skills/
```

各 skill 通过 `SKILL.md` 中的 `description` 触发词自动匹配；也可在对话中显式调用。部分 skill 依赖外部工具（yt-dlp、curl_cffi、Playwright、ComfyUI 等），详见对应目录内说明。

## 许可

个人技能合集，供学习与参考。各 skill 中涉及的第三方服务（ComfyUI、RunningHub、MiniMax 等）版权归原作者所有。
