---
name: claude-code-upgrade
description: Upgrade Claude Code CLI to the latest version. Diagnoses installation method (native vs npm-global), applies the correct upgrade command, and handles common pitfalls like CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC blocking updates. Triggers on: 升级 claude code, 更新 claude code, upgrade claude code, update claude code, claude update, 升级版本, update claude.
metadata:
  author: Lucas
  version: 1.1.0
compatibility: 需要已安装 Claude Code CLI 与 claude 命令（PATH 或 C:\Users\Lucas\.local\bin\claude）。
  npm-global 安装方式需要 Node.js/npm。
---

# Claude Code Upgrade Skill

Upgrade Claude Code CLI by first diagnosing the installation method, then applying the correct upgrade path.

## Core Principle

**Diagnose first, upgrade second.** Never assume the installation method — always run `claude doctor` before choosing an upgrade command.

## Instructions

### Step 1: Diagnose Installation Method

```bash
claude doctor
```

Key output line: `Running: native` or `Running: npm-global`.

### Step 2: Choose Upgrade Path

| Install Method | Upgrade Command | Fallback |
|---------------|----------------|----------|
| native | `claude update` | Download `claude-win32-x64.zip` from GitHub Releases |
| npm-global | `npm update -g @anthropic-ai/claude-code` | `npm install -g @anthropic-ai/claude-code@latest` |

Expected output: `Successfully updated to <新版本号>`（或等价信息）。

### Step 3: Handle CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC

If the workspace has `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` set (common in relay/proxy workspaces), both auto-updates and manual `claude update` are blocked. Override it temporarily:

```bash
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=0 claude update
```

Check `settings.local.json` for this variable before upgrading.
Expected output: 覆盖后更新正常执行；若无此变量则跳过本步。

### Step 4: Verify

```bash
claude --version
```

Expected output: `2.x.x` 版本号。与升级前对比，确认新版本号更高。

## Common Pitfalls

1. **Skipping `claude doctor`**: Running `npm update -g` on a native install does nothing. Root cause recorded on 2026-07-17.
2. **CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1**: Silently blocks `claude update`. Always check `settings.local.json` env block first.
3. **Wrong executable path**: In WSL/Git Bash, use `/c/Users/Lucas/.local/bin/claude` (not `C:\Users\...` or `/mnt/c/...`).

## Examples

**Example 1: Standard native upgrade**
```
User: 升级 claude code
Actions:
1. Run claude doctor → Running: native (2.1.215)
2. Run claude update → Successfully updated to 2.1.216
3. Run claude --version → 2.1.216
```

**Example 2: Relay workspace with traffic disabled**
```
User: 更新 claude code
Actions:
1. Run claude doctor → Running: native
2. Check settings.local.json → CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
3. Run CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=0 claude update
4. Verify with claude --version
```

## Safety

- `claude update` is reversible: old versions available on GitHub Releases
- Never `npm uninstall` a native installation
- Do not mix npm and native installations on the same machine
