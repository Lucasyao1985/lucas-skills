# -*- coding: utf-8 -*-
import io, re

s = io.open(r"C:\Users\Lucas\.claude\skills\zhipin\_company.html", encoding="utf-8", errors="replace").read()

print("=== 远程/弹性 相关关键词命中 ===")
keys = ["远程", "居家", "在家", "弹性", "不打卡", "分布式团队", "remote", "Remote",
        "可远程", "接受远程", "接受外地", "线上办公", "异地"]
hit = False
for k in keys:
    c = s.count(k)
    if c:
        hit = True
        print(f"  {k}: {c} 次")
if not hit:
    print("  （无任何命中）")

print()
print("=== 各岗位标签 jobLabels ===")
segs = re.findall(r'jobName:"([^"]{2,30})"[^}]{0,500}?jobLabels:\[([^\]]*)\]', s)
seen = set()
for name, labels in segs:
    if name in seen:
        continue
    seen.add(name)
    print(f"  {name}: [{labels}]")

print()
print("=== 是否有 '远程办公' 类筛选项/运营位文案 ===")
for m in re.finditer(r'.{60}(远程|居家办公).{60}', s):
    print("  ...", re.sub(r"\s+", " ", m.group(0)), "...")
