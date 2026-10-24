#!/usr/bin/env python3
"""把 src/ 里的源稿构建成 book/、appendix/、docs/、README.md 和 index.html。

源稿约定：
  - 章节文件 src/NN-名称.md，第一行是 "# 第X章　标题"。
  - 条目标题写成 "## @slug　标题"，构建时按出现顺序编号为 001、002……
  - 正文里用 {{slug}} 引用某一条，构建时替换成可点击的 "第 NNN 条"。
  - src/序言.md、救急卡.md、场景速查.md 输出到 book/；src/appendix/ 输出到 appendix/；
    src/docs/ 输出到 docs/；src/README.tpl.md 生成根目录 README.md。
  - tools/config.json 里填 "repo": "用户名/仓库名"，README 就会带上在线阅读地址。

用法：python3 tools/build.py        （只需要 Python 3，不依赖任何第三方库）
"""
import re, os, glob, json, html, sys, collections, shutil, datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
BOOK_TITLE = "不吃哑巴亏指南——男性婚恋护身之书"
SUB = "恋爱转账、彩礼、婚前协议、婚后财产、离婚官司、抚养权、刑事红线。写给那些愿意付出，却总是吃了亏说不出口的男人。"
CHECK_DATE = "2026 年 10 月"
SHORT_TITLE = "不吃哑巴亏指南"
CFG = json.load(open(os.path.join(ROOT, "tools", "config.json"), encoding="utf-8"))
REPO = (CFG.get("repo") or "").strip()
BRANCH = CFG.get("branch", "main")

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

# ---------- 1. 解析章节、分配编号 ----------
chapters = []
slug2num, slug2title, slug2file = {}, {}, {}
n = 0
for path in sorted(glob.glob(os.path.join(SRC, "[0-9][0-9]-*.md"))):
    fn = os.path.basename(path)
    text = read(path)
    m = re.search(r"^# (.*)$", text, re.M)
    title = m.group(1) if m else fn
    parts = re.split(r"^(?=## @)", text, flags=re.M)
    head, entry_parts = parts[0], parts[1:]
    entries = []
    for ep in entry_parts:
        hm = re.match(r"## @([a-z0-9\-]+)　(.*)\n", ep)
        if not hm:
            sys.exit(f"{fn}: 条目标题格式错误: {ep[:40]!r}")
        slug, t = hm.group(1), hm.group(2).strip()
        if slug in slug2num:
            sys.exit(f"重复的 slug: {slug}")
        n += 1
        slug2num[slug], slug2title[slug], slug2file[slug] = n, t, fn
        entries.append(dict(slug=slug, num=n, title=t, body=ep[hm.end():], file=fn))
    chapters.append(dict(file=fn, title=title, head=head, entries=entries))
TOTAL = n

def resolve(s, where, mode="plain", base=""):
    """mode: plain 纯文本 / md 带文件链接 / site 网页内锚点。"""
    def r(m):
        k = m.group(1)
        if k not in slug2num:
            sys.exit(f"{where}: 未知引用 {{{{{k}}}}}")
        num = f"{slug2num[k]:03d}"
        if mode == "site":
            return f"[第 {num} 条](#/e/{num})"
        if mode == "md":
            return f"[第 {num} 条]({base}{quote(slug2file[k])}#e{num})"
        return f"第 {num} 条"
    return re.sub(r"\{\{([a-z0-9\-]+)\}\}", r, s)

# ---------- 2. 清理并输出 ----------
for d in ("book", "appendix", "docs", "site"):
    shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)

grades = collections.Counter()
pending = n_script = n_case = 0
for ci, ch in enumerate(chapters):
    out = [resolve(ch["head"], ch["file"], "md", "").rstrip() + "\n"]
    for e in ch["entries"]:
        body = e["body"]
        e["body_md"] = resolve(body, ch["file"] + ":" + e["slug"], "md", "")
        e["body_plain"] = resolve(body, e["slug"])
        g = re.search(r"\*\*把握度\*\*：([ABC])", body)
        e["grade"] = g.group(1) if g else "?"
        grades[e["grade"]] += 1
        pending += body.count("待核实")
        n_script += "**可以这样" in body
        n_case += "附录 O" in body
        out.append(f'<a id="e{e["num"]:03d}"></a>\n\n## {e["num"]:03d}　{e["title"]}\n{e["body_md"].rstrip()}\n')
    prev = chapters[ci - 1] if ci else None
    nxt = chapters[ci + 1] if ci + 1 < len(chapters) else None
    nav = ["---", ""]
    nav.append(" · ".join(filter(None, [
        f"[← {prev['title'].split('　')[0]}]({quote(prev['file'])})" if prev else "[← 序言](00-序言.md)",
        "[目录](README.md)",
        f"[{nxt['title'].split('　')[0]} →]({quote(nxt['file'])})" if nxt else "[附录 →](../appendix/)"])))
    out.append("\n".join(nav) + "\n")
    write(os.path.join(ROOT, "book", ch["file"]), "\n".join(out))

special_raw = {}
for path in sorted(glob.glob(os.path.join(SRC, "*.md"))):
    fn = os.path.basename(path)
    if re.match(r"\d\d-", fn) or fn == "README.tpl.md":
        continue
    special_raw[fn] = read(path)
# ---- 自动汇总：口诀卡、话术手册（以 {{slug}} 引用的原始 Markdown 形式生成） ----
card = ["# 口诀卡：一页纸，把全书背下来", "",
        "> 先背这四句：**先分性质，先留痕，人身优先，冲动不决。** 详见 {{four-rules}}。", "",
        "| 章 | 这一章想让你想明白的事 | 口诀 |", "|---|---|---|"]
for ch in chapters:
    mt = re.search(r"> \*\*这一章想让你想明白的事\*\*：(.*)", ch["head"])
    mk = re.search(r"> \*\*口诀\*\*：(.*)", ch["head"])
    if mt and mk:
        card.append(f"| {ch['title'].split('：')[0].replace('　', ' ')} | {mt.group(1)} | {mk.group(1)} |")
card += ["", "背不下来也没关系。遇到事，先翻[救急卡](救急卡.md)。"]
special_raw["口诀卡.md"] = "\n".join(card) + "\n"

scripts = ["# 话术手册：可以直接说、直接写的话", "",
           "> 这是全书所有\"可以这样说\"的汇总，按章排列，每段后面标了出处。照着说，别照着念：把名字、金额、日期换成你自己的。",
           "> 话术只是一个起点。对方情绪激动、涉及威胁或人身安全的时候，先保证安全，再谈话术。", ""]
n_scripts = 0
for ch in chapters:
    block = []
    for e in ch["entries"]:
        m = re.search(r"\*\*可以这样(?:说|写)\*\*[^\n]*\n+((?:[-*] [^\n]*\n?)+)", e["body"])
        if m:
            txt = m.group(1).strip()
            if txt:
                block.append(f"#### {e['title']}（{{{{{e['slug']}}}}}）\n\n{txt}\n")
                n_scripts += 1
    if block:
        scripts.append(f"## {ch['title']}\n")
        scripts.extend(block)
special_raw["话术手册.md"] = "\n".join(scripts) + "\n"

OUTNAME = {"序言.md": "00-序言.md"}
for fn, raw in special_raw.items():
    write(os.path.join(ROOT, "book", OUTNAME.get(fn, fn)), resolve(raw, fn, "md", ""))

apps = []
for path in sorted(glob.glob(os.path.join(SRC, "appendix", "*.md"))):
    fn = os.path.basename(path)
    raw = read(path)
    write(os.path.join(ROOT, "appendix", fn), resolve(raw, "appendix/" + fn, "md", "../book/"))
    apps.append((fn, raw))

for path in sorted(glob.glob(os.path.join(SRC, "docs", "*.md"))):
    fn = os.path.basename(path)
    write(os.path.join(ROOT, "docs", fn), resolve(read(path), "docs/" + fn, "md", "../book/"))

# ---------- 3. book/README.md（完整目录） ----------
toc = ["# 目录", "",
       "- [序言：吃了亏，为什么总是说不出口](00-序言.md)",
       "- [救急卡：八种紧急情况，先看这个](救急卡.md)",
       "- [场景速查：我现在遇到的是……](场景速查.md)",
       "- [口诀卡：一页纸，把全书背下来](口诀卡.md)",
       "- [话术手册：可以直接说、直接写的话](话术手册.md)", ""]
for ch in chapters:
    toc.append(f"## [{ch['title']}]({quote(ch['file'])})\n")
    for e in ch["entries"]:
        toc.append(f"- [{e['num']:03d}　{e['title']}]({quote(ch['file'])}#e{e['num']:03d}) `{e['grade']}`")
    toc.append("")
toc.append("- [后记](后记.md)\n")
toc.append("## 附录\n")
for fn, raw in apps:
    t = re.search(r"^# (.*)$", raw, re.M).group(1)
    toc.append(f"- [{t}](../appendix/{quote(fn)})")
write(os.path.join(ROOT, "book", "README.md"), "\n".join(toc) + "\n")

# ---------- 4. 根目录 README.md ----------
tpl = read(os.path.join(SRC, "README.tpl.md"))
if REPO:
    owner, name = REPO.split("/")
    pages = f"https://{owner}.github.io/{name}/"
    pages_btn = f"[**网页阅读版**]({pages})"
    pages_line = f"在线阅读：{pages}"
    repo_url = f"https://github.com/{REPO}"
else:
    pages_btn = "[**网页阅读版**](#自己跑一份)"
    pages_line = "启用 GitHub Pages 后，在线阅读地址是 `https://你的用户名.github.io/仓库名/`"
    repo_url = ""
def badge(label, value, color):
    return f"![{label}](https://img.shields.io/badge/{quote(label)}-{quote(str(value), safe='')}-{color}?style=flat-square)"
badges = " ".join([badge("篇数", TOTAL, "0f6b6b"), badge("把握度 A", f"{grades['A']} 篇", "1d7a46"),
                   badge("最高法案例", 13, "5a6270"), badge("文书与附录", len(apps), "5a6270"),
                   badge("法条核对", "2026.10", "a56a00"), badge("许可", "CC BY 4.0", "3451b2")])
clone = f"https://github.com/{REPO}.git" if REPO else "https://github.com/你的用户名/仓库名.git"
repo_dir = REPO.split("/")[1] if REPO else "仓库名"
tokens = {"BADGES": badges, "REPO_CLONE": clone, "REPO_DIR": repo_dir,
          "REPO_URL_OR_NAME": repo_url or "仓库地址", "ISSUES_URL": (repo_url + "/issues/new/choose") if repo_url else "CONTRIBUTING.md", "BOOK_TITLE": BOOK_TITLE, "SUB": SUB, "TOTAL": TOTAL, "NCH": len(chapters), "NAPP": len(apps),
          "CHECK_DATE": CHECK_DATE, "GA": grades["A"], "GB": grades["B"], "GC": grades["C"], 
          "PENDING": pending, "NSCRIPTS": n_scripts, "NSCRIPT": n_script, "NCASE": n_case,
          "PAGES_BTN": pages_btn, "PAGES_LINE": pages_line, "REPO_URL": repo_url}
tpl = re.sub(r"\{\{num:([a-z0-9\-]+)\}\}", lambda m: f"{slug2num[m.group(1)]:03d}", tpl)
readme = resolve(tpl, "README.tpl.md", "md", "book/")
for k, v in tokens.items():
    readme = readme.replace("{{" + k + "}}", str(v))
write(os.path.join(ROOT, "README.md"), readme)

# ---------- 5. og.html（横幅图的源，用 tools/make_og.sh 渲染成 og.png） ----------
og = read(os.path.join(ROOT, "tools", "og.tpl.html"))
for k in ("TOTAL", "GA", "NAPP"):
    og = og.replace("{{" + k + "}}", str(tokens[k]))
write(os.path.join(ROOT, "tools", "og.html"), og)

# ---------- 6. 简易 Markdown -> HTML（只覆盖本书用到的语法） ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    return s

def md2html(md):
    lines = md.split("\n")
    out, stack, para = [], [], []
    i = 0
    def close_lists(to=0):
        while len(stack) > to:
            out.append(f"</li></{stack.pop()[0]}>")
    def flush_para():
        if para:
            cls = ""
            if para[0].startswith("**说句实在话**"): cls = ' class="talk"'
            elif para[0].startswith("**道理**"): cls = ' class="why"'
            out.append(f"<p{cls}>" + "<br>".join(inline(x) for x in para) + "</p>")
            para.clear()
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            flush_para(); close_lists(); i += 1; continue
        if ln.startswith("<a id="):
            i += 1; continue
        if ln.startswith("|"):
            flush_para(); close_lists()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            hdr = cells(rows[0]); body = [cells(r) for r in rows[2:]]
            t = "<div class='tw'><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in hdr) + "</tr></thead><tbody>"
            for r in body:
                t += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,6}) (.*)$", ln)
        if m:
            flush_para(); close_lists()
            lv = min(len(m.group(1)) + 1, 6)
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>"); i += 1; continue
        if ln.startswith("> "):
            flush_para(); close_lists()
            q = []
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i][1:].strip()); i += 1
            out.append("<blockquote>" + "<br>".join(inline(x) for x in q) + "</blockquote>"); continue
        if re.match(r"^-{3,}$", ln.strip()):
            flush_para(); close_lists(); out.append("<hr>"); i += 1; continue
        lm = re.match(r"^(\s*)([-*]|\d+\.) (.*)$", ln)
        if lm:
            flush_para()
            indent = len(lm.group(1))
            tag = "ol" if lm.group(2)[0].isdigit() else "ul"
            txt = re.sub(r"^\[ \] ", "☐ ", lm.group(3)); txt = re.sub(r"^\[x\] ", "☑ ", txt)
            if not stack or indent > stack[-1][1]:
                out.append(f"<{tag}><li>{inline(txt)}")
                stack.append((tag, indent))
            else:
                while len(stack) > 1 and indent < stack[-1][1]:
                    out.append(f"</li></{stack.pop()[0]}>")
                out.append(f"</li><li>{inline(txt)}")
            i += 1; continue
        if stack and ln.startswith("  "):
            out.append("<br>" + inline(ln.strip())); i += 1; continue
        close_lists()
        para.append(ln.strip()); i += 1
    flush_para(); close_lists()
    return "\n".join(out)

# ---------- 7. 网页阅读版 index.html ----------
data = dict(title=BOOK_TITLE, sub=SUB, total=TOTAL, check=CHECK_DATE, chapters=[], pages=[], apps=[])
for ch in chapters:
    head_site = resolve(ch["head"], "", "site")
    c = dict(title=ch["title"], intro=md2html(head_site.split("\n", 1)[1] if "\n" in head_site else ""), entries=[])
    for e in ch["entries"]:
        plain = re.sub(r"[#*`>|\-]", "", e["body_plain"])
        lm = re.search(r"^> (.*)$", e["body_plain"], re.M)
        c["entries"].append(dict(num=f"{e['num']:03d}", title=e["title"], grade=e["grade"],
                                 lead=lm.group(1) if lm else "",
                                 html=md2html(resolve(e["body"], e["slug"], "site")),
                                 text=e["title"] + " " + plain))
    data["chapters"].append(c)
for fn, label in (("序言.md", "序言"), ("救急卡.md", "救急卡"), ("场景速查.md", "场景速查"), ("口诀卡.md", "口诀卡"), ("话术手册.md", "话术手册"), ("后记.md", "后记")):
    if fn in special_raw:
        data["pages"].append(dict(id=fn[:-3], label=label,
                                  html=md2html(resolve(special_raw[fn], fn, "site")),
                                  text=resolve(special_raw[fn], fn)))
for fn, raw in apps:
    t = re.search(r"^# (.*)$", raw, re.M).group(1)
    data["apps"].append(dict(id=fn[:-3], title=t, html=md2html(resolve(raw, fn, "site")), text=resolve(raw, fn)))
tpl_site = read(os.path.join(ROOT, "tools", "site.tpl.html"))
blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
write(os.path.join(ROOT, "index.html"), tpl_site.replace("/*__DATA__*/null", blob))
write(os.path.join(ROOT, ".nojekyll"), "")

# ---------- 8. 链接检查 ----------
bad = []
def check(mdfile):
    base = os.path.dirname(mdfile)
    s = read(mdfile)
    for m in re.finditer(r"\]\(([^)#\s][^)\s]*?)(#[^)\s]*)?\)", s):
        tgt, frag = m.group(1), m.group(2)
        if re.match(r"[a-z]+:", tgt):
            continue
        from urllib.parse import unquote
        p = os.path.normpath(os.path.join(base, unquote(tgt)))
        if not os.path.exists(p):
            bad.append((os.path.relpath(mdfile, ROOT), tgt)); continue
        if frag and p.endswith(".md"):
            if f'id="{frag[1:]}"' not in read(p):
                bad.append((os.path.relpath(mdfile, ROOT), tgt + frag))
for f in [os.path.join(ROOT, "README.md")] + glob.glob(os.path.join(ROOT, "book", "*.md")) + \
         glob.glob(os.path.join(ROOT, "appendix", "*.md")) + glob.glob(os.path.join(ROOT, "docs", "*.md")):
    check(f)
if bad:
    for b in bad[:20]:
        print("坏链接:", b)
    sys.exit(f"共 {len(bad)} 个坏链接")

print(f"构建完成：{len(chapters)} 章，{TOTAL} 条，{len(apps)} 份附录；"
      f"把握度 A/B/C = {grades['A']}/{grades['B']}/{grades['C']}；带话术 {n_script}，提到官方案例 {n_case}；待核实 {pending} 处")
