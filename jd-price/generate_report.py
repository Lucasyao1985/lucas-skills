#!/usr/bin/env python3
"""
京东价格分析报告生成器
用法: python generate_report.py --data product_data.json
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 模板路径
TEMPLATE_PATH = Path(__file__).parent / "report_template.html"
REPORTS_DIR = Path(__file__).parent / "reports"


def load_template():
    """加载HTML模板"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def generate_product_card(product):
    """生成单个商品卡片HTML"""
    price_html = f'<span class="current-price">¥{product["price"]}</span>'
    if product.get("original_price"):
        price_html += f' <span class="original-price">¥{product["original_price"]}</span>'
    if product.get("discount"):
        price_html += f' <span class="discount-tag">{product["discount"]}</span>'

    coupons_html = ""
    if product.get("coupons"):
        coupons_html = '<div style="margin-top: 8px;">'
        for coupon in product["coupons"]:
            coupons_html += f'<span class="coupon-tag">{coupon}</span>'
        coupons_html += '</div>'

    rating_html = ""
    if product.get("rating"):
        stars = "★" * int(product["rating"]) + "☆" * (5 - int(product["rating"]))
        rating_html = f'''
        <div class="rating">
            <span class="stars">{stars}</span>
            <span class="rating-count">{product.get("rating_count", 0)}条评价</span>
        </div>'''

    badge_class = product.get("analysis_badge", "badge-watch")
    badge_text = product.get("analysis_text", "可观望")

    return f'''
    <div class="product-card">
        <img class="product-image" src="{product.get('image', '')}" alt="{product['name']}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 200 200%22><rect fill=%22%23f0f0f0%22 width=%22200%22 height=%22200%22/><text x=%22100%22 y=%22100%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22 font-size=%2214%22>暂无图片</text></svg>'">
        <div class="product-info">
            <div class="product-name">{product["name"]}</div>
            <div class="price-row">
                {price_html}
            </div>
            {coupons_html}
            <div style="margin-top: 12px;">
                <span class="analysis-badge {badge_class}">{badge_text}</span>
            </div>
            {rating_html}
            <div class="shop-info">
                🏪 {product.get("shop", "未知店铺")}
            </div>
        </div>
    </div>'''


def generate_comparison_table(products):
    """生成对比表HTML"""
    if len(products) < 2:
        return ""

    headers = "".join([f"<th>{p['name'][:15]}...</th>" for p in products])

    rows = ""
    # 价格行
    prices = "".join([f"<td>¥{p['price']}</td>" for p in products])
    rows += f"<tr><td>当前价格</td>{prices}</tr>"

    # 优惠后价格
    final_prices = "".join([f"<td>¥{p.get('final_price', p['price'])}</td>" for p in products])
    rows += f"<tr><td>优惠后价格</td>{final_prices}</tr>"

    # 店铺
    shops = "".join([f"<td>{p.get('shop', '-')}</td>" for p in products])
    rows += f"<tr><td>店铺</td>{shops}</tr>"

    # 评分
    ratings = "".join([f"<td>{p.get('rating', '-')}</td>" for p in products])
    rows += f"<tr><td>评分</td>{ratings}</tr>"

    # 评论数
    counts = "".join([f"<td>{p.get('rating_count', '-')}</td>" for p in products])
    rows += f"<tr><td>评论数</td>{counts}</tr>"

    return f'''
    <div class="card">
        <div class="card-title">⚖️ 商品对比</div>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>项目</th>
                    {headers}
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>'''


def generate_trend_bars(prices):
    """生成价格趋势柱状图"""
    if not prices:
        return ""

    max_price = max(prices)
    bars = ""
    for i, price in enumerate(prices):
        height = int((price / max_price) * 150)
        bars += f'<div class="trend-bar" style="height: {height}px;" title="¥{price}"></div>'

    return bars


def generate_report(data):
    """生成完整HTML报告"""
    template = load_template()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 生成商品卡片
    product_cards = ""
    for product in data.get("products", []):
        product_cards += generate_product_card(product)

    # 生成分析内容
    analysis_content = ""
    for product in data.get("products", []):
        analysis_content += f'''
        <div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
            <strong>{product["name"][:30]}...</strong><br>
            <span style="color: var(--text-secondary);">{product.get("analysis", "暂无分析")}</span>
        </div>'''

    # 生成对比表
    comparison_section = generate_comparison_table(data.get("products", []))

    # 生成趋势图
    trend_bars = generate_trend_bars(data.get("price_history", []))

    # 生成推荐结论
    recommendations = ""
    for rec in data.get("recommendations", []):
        recommendations += f'''
        <div class="recommendation-item">
            <div class="label">{rec["label"]}</div>
            <div class="value">{rec["value"]}</div>
        </div>'''

    # 替换模板变量
    html = template
    html = html.replace("{{DATE}}", now)
    html = html.replace("{{PRODUCT_CARDS}}", product_cards)
    html = html.replace("{{ANALYSIS_CONTENT}}", analysis_content)
    html = html.replace("{{COMPARISON_SECTION}}", comparison_section)
    html = html.replace("{{TREND_BARS}}", trend_bars)
    html = html.replace("{{RECOMMENDATIONS}}", recommendations)

    # 保存报告
    report_dir = REPORTS_DIR / datetime.now().strftime("%Y-%m-%d")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "jd_price_report.html"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    return str(report_path)


def main():
    """主函数"""
    import argparse
    import sys

    # 设置stdout编码为UTF-8（Windows兼容）
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="京东价格分析报告生成器")
    parser.add_argument("--data", required=True, help="商品数据JSON文件路径")
    parser.add_argument("--output", help="输出文件路径（可选）")

    args = parser.parse_args()

    # 加载数据
    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 生成报告
    report_path = generate_report(data)

    print(f"[OK] 报告已生成: {report_path}")


if __name__ == "__main__":
    main()
