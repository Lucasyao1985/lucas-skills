---
name: sprite-gen
description: |
  2D 游戏精灵与动画图集生成：一张底图 → 透明精灵图集(atlas + manifest.json) / 透明循环动图；也支持抠图、切图、调色板换色、分层合成、Aseprite/Phaser/Flame 导出、curation 网页挑选。
  触发词：sprite、精灵、精灵图、游戏素材、像素角色、sprite sheet、atlas、图集、帧动画、抠图、去背景、chroma key、调色板换色、recolor、palette swap、动画循环、transparent GIF、Aseprite 导出、game asset、2D 角色动画。
---

# sprite-gen（本地已安装版）

> 执行前先完整读完本文件再动手。项目源码在 `D:\sprite-gen`（v2.1.0，Apache-2.0），本文件只是调用契约。

## 环境（Windows，必须照此调用）

| 项 | 值 |
|---|---|
| 项目根目录 | `D:\sprite-gen` |
| 解释器 | `D:\sprite-gen\.venv\Scripts\python.exe` |
| CLI | `D:\sprite-gen\.venv\Scripts\sprite-gen.exe` |

**规则：**
1. 一律用上表的绝对路径调用，**不要**用系统 `python`/`python3`，也不要自己新建 venv —— 依赖只装在这个 venv 里（Pillow + NumPy）。
2. 项目文档里的 `$SPRITE_GEN_ROOT/.venv/bin/sprite-gen` 是 Unix 写法，Windows 实际是 `.venv\Scripts\sprite-gen.exe`。
3. venv 缺失就报错，禁止回退到任意全局 Python。
4. 等价形式：`D:\sprite-gen\.venv\Scripts\python.exe -m sprite_gen.cli <tool>`。

先看全貌：

```powershell
D:\sprite-gen\.venv\Scripts\sprite-gen.exe --help
D:\sprite-gen\.venv\Scripts\sprite-gen.exe <tool> --help
```

## 两条用户入口

1. **做精灵 / 做动画** → 先跑 `workflow --kind sprite`，它检查访问状态 + 结合已保存默认值，只返回还缺的问题，并指导下一步。
2. **只是出一张图 / 改图** → 先跑 `workflow --kind image`，再直接 `gen --provider codex`。

```powershell
sprite-gen.exe workflow --kind sprite
sprite-gen.exe workflow --kind image
sprite-gen.exe defaults show        # 查看已保存的默认选择
```

用户明确同意后才 `defaults save`；一次性请求不要覆盖默认值。用户已说过的选择直接传进去，别重复问。

## 路由表

| 任务 | 入口 |
|---|---|
| 底图 → 精灵图集（A 管线） | `prepare` → `gen-set --provider codex` → `extract` → `compose-atlas`（可选 `curation` 后再 compose） |
| 底图 → 透明循环动图（B 管线） | `video-set`（内部 video-canvas → video → video-frames → video-loop） |
| 单张出图 / 改图 | `gen --provider codex`（或 `grok`，但本机未装） |
| 方向锚点 | `anchor` |
| 已有图 / 已有图集做挑选 | `curation`、`unpack-atlas --pngs-dir` |
| 抠图、切网格图 | `cutout`、`slice-sheet` |
| 换色 | `recolor-palette` → `recolor` |
| 分层 rig 合成 | `compose-layers` |
| 引擎导出 | `export-aseprite`、`export-pngs` |
| QA | `preview`、`inspect`、`score`、`correction-loop` |

**不要用临时裁剪脚本冒充管线输出**，也不要让用户自己挑脚本跑。

## 常用命令

```powershell
# A · 底图 → 可用图集
sprite-gen.exe prepare --out-dir <run> --character-id <id> --base-image base.png
sprite-gen.exe gen-set --run-dir <run> --provider codex
sprite-gen.exe extract --run-dir <run>
sprite-gen.exe compose-atlas --run-dir <run>
sprite-gen.exe curation --run-dir <run>          # 可选，网页挑选/微调

# C · 单独工具
sprite-gen.exe cutout icon.png --white-check
sprite-gen.exe slice-sheet --sheet sheet.png --chroma-key magenta --grid 3x2
sprite-gen.exe unpack-atlas --atlas sheet.png

# D · 后处理
sprite-gen.exe recolor-palette --base <run>\sprite-sheet-alpha.png --out palette.draft.json
sprite-gen.exe recolor --run-dir <run> --spec recolor.spec.json
sprite-gen.exe export-aseprite --run-dir <run>
```

产物：`sprite-sheet-alpha.png`（真透明、无 chroma 残留）+ `manifest.json` 的 `frame_layout`（绝对帧矩形、每状态 fps、loop 标记）。交付前先跑检查，把结果文件给用户。

## 本机能力边界（重要）

| 依赖 | 状态 | 影响 |
|---|---|---|
| `codex` CLI | ✅ 已装并已登录 | `gen --provider codex` / `gen-set --provider codex` 可直接用 —— **当前默认走这条** |
| `ffmpeg` | ✅ `C:\ffmpeg\bin\ffmpeg` | video-frames / video-set 可用 |
| `grok` CLI | ❌ 未装 | `--provider grok` 出图、以及视频生成**不可用** |
| `img2webp` | ❌ 未装 | video-loop 的 WebP（精确 alpha）输出不可用；GIF/strip 仍可 |
| `XAI_API_KEY` | 未设置 | 可作为 grok 视频的替代凭据 |

所以：**A 管线（codex 出图 + 本地抠图/合成/导出）完全可用；B 管线（视频）需要用户先装 grok CLI 或设 XAI_API_KEY、再装 img2webp。** 缺依赖就直说并给安装指引，不要假装跑通、不要静默降级。

## 文档（按需精读，绝对路径）

- 用户流程与默认值：`D:\sprite-gen\docs\user-workflow.md`
- 图集工作流：`D:\sprite-gen\docs\atlas-workflow.md`
- 运行契约（目录布局、原子发布）：`D:\sprite-gen\docs\run-contract.md`
- 视频管线：`D:\sprite-gen\docs\video-pipeline.md`、`docs\video.md`
- 抠图/切图：`D:\sprite-gen\docs\sheet-slicing.md`
- 呼吸 idle：`D:\sprite-gen\docs\breathing.md`
- 换色：`D:\sprite-gen\docs\recolor.md`
- 导出：`D:\sprite-gen\docs\engine-export.md`
- 排障：`D:\sprite-gen\docs\troubleshooting.md`
- 全部索引：`D:\sprite-gen\docs\README.md`

## 更新与维护

本机 git 连不上 github.com（代理 502），源码来自 codeload tarball，**`D:\sprite-gen` 没有 `.git`**。需要升级时重新拉取并覆盖：

```bash
curl -sL -o /tmp/sg.tar.gz https://codeload.github.com/aldegad/sprite-gen/tar.gz/refs/heads/main
tar -xzf /tmp/sg.tar.gz --strip-components=1 -C /d/sprite-gen
D:/sprite-gen/.venv/Scripts/python.exe -m pip install -e D:/sprite-gen
```
