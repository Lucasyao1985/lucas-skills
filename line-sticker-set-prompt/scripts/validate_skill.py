#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate a skill folder against "The Complete Guide to Building Skills for Claude".

Usage:
    python validate_skill.py <path-to-skill-folder>
    python validate_skill.py .            # validate the current folder

Exits non-zero if any BLOCKING check fails.
"""
import os
import re
import sys

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("claude", "anthropic")

# (condition, message, blocking)
def run(root):
    root = os.path.abspath(root)
    name = os.path.basename(root)
    results = []

    def chk(cond, msg, blocking=True):
        results.append((bool(cond), msg, blocking))

    # --- packaging ---
    chk(os.path.isdir(root), "skill folder exists")
    chk(KEBAB.match(name), "folder name is kebab-case (%s)" % name)
    skill_md = os.path.join(root, "SKILL.md")
    chk(os.path.exists(skill_md), "SKILL.md exists with exact casing")
    chk(not os.path.exists(os.path.join(root, "README.md")),
        "no README.md inside the skill folder")

    if not os.path.exists(skill_md):
        return results

    txt = open(skill_md, encoding="utf-8").read()

    # --- frontmatter ---
    chk(txt.startswith("---\n"), "frontmatter opens with --- on line 1")
    m = re.match(r"---\n(.*?)\n---\n", txt, re.S)
    chk(m is not None, "frontmatter closes with ---")
    if not m:
        return results
    fm = m.group(1)

    # A YAML block-scalar indicator ("description: >" / "description: |") is legitimate
    # YAML, not an XML tag — strip those lines before looking for angle brackets.
    fm_for_brackets = "\n".join(
        line for line in fm.split("\n")
        if not re.match(r"^\s*[A-Za-z0-9_-]+:\s*[>|][-+0-9]*\s*$", line)
    )
    chk("<" not in fm_for_brackets and ">" not in fm_for_brackets,
        "no angle brackets anywhere in frontmatter (YAML block scalars exempt)")

    nm = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
    chk(nm is not None, "frontmatter has a name field")
    if nm:
        chk(nm.group(1) == name, "name matches folder name (%s)" % nm.group(1))
        chk(KEBAB.match(nm.group(1)) is not None, "name is kebab-case")
        chk(not any(r in nm.group(1).lower() for r in RESERVED),
            "name does not use a reserved word")

    dm = re.search(r"^description:\s*(.+?)(?=\n[a-z][a-z0-9_-]*:|\Z)", fm, re.S | re.M)
    chk(dm is not None, "frontmatter has a description field")
    if dm:
        desc = " ".join(dm.group(1).split())
        chk(len(desc) <= 1024, "description is under 1024 chars (actual %d)" % len(desc))
        chk("use when" in desc.lower() or "when the user" in desc.lower(),
            "description states WHEN to use it")
        chk(len(desc) > 80, "description is specific, not a one-liner")

    # --- body ---
    body = txt[m.end():]
    chk(len(body.split()) > 100, "SKILL.md body has real instructions")
    chk(len(txt.split()) < 5000, "SKILL.md is under 5000 words (actual %d)" % len(txt.split()))
    chk("## " in body, "body uses section headings")

    return results


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    results = run(root)
    fails = [r for r in results if not r[0] and r[2]]
    warns = [r for r in results if not r[0] and not r[2]]

    print("Validating: %s\n" % os.path.abspath(root))
    for ok, msg, blocking in results:
        print("  %s %s%s" % ("PASS" if ok else "FAIL", msg,
                             "" if blocking else "  (advisory)"))
    print("\n%d passed, %d failed" % (len(results) - len(fails) - len(warns), len(fails) + len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
