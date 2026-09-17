# Chinese Lottery Analysis Tools
<p align="center">
  <a href="https://github.com/Lucasyao1985/lottery-skills">GitHub</a> | <a href="https://github.com/Lucasyao1985/lottery-skills/issues">Report Issue</a>
</p>
<p align="center">
  <a href="https://github.com/Lucasyao1985/lottery-skills"><img alt="Release version" src="https://img.shields.io/github/v/release/Lucasyao1985/lottery-skills?color=2da44e&label=Latest&style=for-the-badge" /></a>
  <a href="https://www.python.org/downloads/"><img alt="Python version" src="https://img.shields.io/badge/Python-3.8%2B-0969da?style=for-the-badge" /></a>
  <a href="https://github.com/Lucasyao1985/lottery-skills/commits"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Lucasyao1985/lottery-skills?color=0969da&label=Last%20commit&style=for-the-badge" /></a>
  <a href="README.zh-CN.md"><img alt="中文" src="https://img.shields.io/badge/中文-da3633?style=for-the-badge" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-2da44e?style=for-the-badge" /></a>
</p>

---

**Chinese Lottery Analysis Tools is a collection of Python tools for analyzing China lottery draw data.** Covers SSQ (双色球), Da Le Tou (大乐透), PL3 (排列3), and PL5 (排列5) — all powered by official API sources.

<table>
<tr><td><b>Official data source</b></td><td>All tools use official lottery APIs (500.com, webapi.sporttery.cn). No third-party scraping.</td></tr>
<tr><td><b>Multi-dimensional analysis</b></td><td>Omission values, hot/cold numbers, odd/even ratios, spans, sums, and more.</td></tr>
<tr><td><b>Smart recommendations</b></td><td>Generates number recommendations based on statistical patterns.</td></tr>
<tr><td><b>Review & compare</b></td><td>Compare past predictions against actual results to evaluate strategy.</td></tr>
</table>

---

## Quick Install

```bash
git clone https://github.com/Lucasyao1985/lottery-skills.git
cd lottery-skills
pip install requests beautifulsoup4
```

## Usage

Run any tool with the `all` command for a full pipeline (fetch + analyze + recommend):

```bash
python ssq/scripts/ssq.py all      # 双色球
python daletou/scripts/dlt.py all   # 大乐透
python pl3/scripts/pick3.py all     # 排列3
python pl5/scripts/pick5.py all     # 排列5
```

### Available Commands

| Command | Description |
|---|---|
| `fetch` | Download latest draw data |
| `analyze` | Run statistical analysis |
| `recommend` | Generate number recommendations |
| `review` | Compare predictions against results |
| `all` | Full pipeline (fetch + analyze + recommend) |

## Project Structure

```
lottery-skills/
├── README.md                # This file (English)
├── README.zh-CN.md          # Chinese documentation
├── ssq/                     # 双色球 (SSQ)
├── daletou/                 # 大乐透 (Da Le Tou)
├── pl3/                     # 排列3 (PL3)
├── pl5/                     # 排列5 (PL5)
├── _reviews/                # Prediction review data
```

## License

MIT — see [LICENSE](LICENSE).

Built with [opencode](https://github.com/anomalyco/opencode).