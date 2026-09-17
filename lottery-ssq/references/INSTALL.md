# 安装指南

## 系统要求

- Python 3.6 或更高版本
- pip 包管理器
- 网络连接（访问开奖数据 API）

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install requests beautifulsoup4
```

### 2. 验证安装

运行测试脚本验证环境：

```bash
python -c "import requests; import bs4; print('✅ 依赖安装成功')"
```

如果看到 `✅ 依赖安装成功`，说明环境配置正确。

### 3. 首次使用

```bash
# 抓取数据
python ~/.claude/skills/ssq-lottery-analysis/scripts/fetch_data.py

# 分析走势
python ~/.claude/skills/ssq-lottery-analysis/scripts/analyze.py

# 推荐号码
python ~/.claude/skills/ssq-lottery-analysis/scripts/recommend.py
```

## 故障排查

### 问题 1: ModuleNotFoundError

**错误**:
```
ModuleNotFoundError: No module named 'bs4'
```

**解决方案**:
```bash
pip install beautifulsoup4
```

### 问题 2: 网络连接失败

**错误**:
```
ConnectionError: Failed to connect
```

**解决方案**:
1. 检查网络连接
2. 检查防火墙设置
3. 尝试使用代理（如有）

### 问题 3: Python 版本过低

**错误**:
```
SyntaxError: invalid syntax
```

**解决方案**:
```bash
# 检查Python版本
python --version

# 升级Python到3.6+
# Windows: 从python.org下载安装
# Linux: sudo apt install python3
# macOS: brew install python3
```

## 卸载

如果需要移除skill：

```bash
rm -rf ~/.claude/skills/ssq-lottery-analysis
```

## 更新

从GitHub拉取最新代码（如果有仓库）：

```bash
cd ~/.claude/skills/ssq-lottery-analysis
git pull origin main
```

或手动替换文件。
