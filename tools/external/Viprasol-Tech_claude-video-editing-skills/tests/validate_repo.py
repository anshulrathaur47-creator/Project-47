#!/usr/bin/env python3
"""Repo validator: every skill is installable and every data file parses.

  python tests/validate_repo.py

Checks: SKILL.md front matter (name == folder, description present and <= 1024 chars), skin theme.json parses
and names an existing scene recipe, genres.json parses, plugin/marketplace manifests parse and the plugin
version matches the newest CHANGELOG entry, every Python file compiles, and the shared text helpers work.
Exits non-zero with a list of problems.
"""
import glob, json, os, py_compile, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "plugins", "video-studio", "skills")
CORE = os.path.join(SKILLS, "video-studio-core")
errors = []


def front_matter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if v:
            fm[k.strip()] = v.strip().strip('"')
    return fm


skills = sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))
recipes = {os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(CORE, "scripts", "recipes", "*.py"))} | {"ribbon"}
for s in skills:
    md = os.path.join(SKILLS, s, "SKILL.md")
    if not os.path.exists(md):
        errors.append(f"{s}: missing SKILL.md"); continue
    fm = front_matter(md)
    if not fm:
        errors.append(f"{s}: SKILL.md has no front matter"); continue
    if fm.get("name") != s:
        errors.append(f"{s}: front matter name '{fm.get('name')}' != folder name")
    desc = fm.get("description", "")
    if not desc:
        errors.append(f"{s}: empty description")
    elif len(desc) > 1024:
        errors.append(f"{s}: description is {len(desc)} chars (max 1024)")
    th = os.path.join(SKILLS, s, "theme.json")
    if os.path.exists(th):
        try:
            t = json.load(open(th, encoding="utf-8"))
        except ValueError as e:
            errors.append(f"{s}: theme.json does not parse: {e}"); continue
        if t.get("name") not in (None, s):
            errors.append(f"{s}: theme.json name '{t.get('name')}' != folder name")
        if t.get("sequence") and t["sequence"] not in recipes:
            errors.append(f"{s}: theme.json sequence '{t['sequence']}' has no recipe")
        if not os.path.exists(os.path.join(SKILLS, s, "theme.css")):
            errors.append(f"{s}: theme.json without theme.css")

for f in [os.path.join(CORE, "scripts", "genres.json"), os.path.join(ROOT, ".claude-plugin", "marketplace.json"),
          os.path.join(ROOT, "plugins", "video-studio", ".claude-plugin", "plugin.json")]:
    try:
        json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError) as e:
        errors.append(f"{os.path.relpath(f, ROOT)}: {e}")

plugin = json.load(open(os.path.join(ROOT, "plugins", "video-studio", ".claude-plugin", "plugin.json"), encoding="utf-8"))
top = re.search(r"^## v(\d+\.\d+\.\d+)", open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read(), re.M)
if not top or top.group(1) != plugin["version"]:
    errors.append(f"plugin.json version {plugin['version']} != newest CHANGELOG entry {top and top.group(1)}")

for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"compile: {e.msg.strip()}")

sys.path.insert(0, os.path.join(CORE, "scripts"))
import vs_common  # noqa: E402  (runs its own asserts)
assert vs_common.norm("राशि,") == "राशि" and vs_common.SENT_END.search("बरगी।")

print(f"{len(skills)} skills, {len(recipes)} scene recipes checked")
if errors:
    print("\n".join("FAIL " + e for e in errors))
    sys.exit(1)
print("OK")
