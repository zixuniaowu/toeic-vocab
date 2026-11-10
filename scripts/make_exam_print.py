#!/usr/bin/env python3
"""Make A4 print-ready PDFs for the exam warmup and Days 39-44."""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path("/workspace/toeic-vocab")
DATA = json.loads((ROOT / "data/exam_sprint.json").read_text(encoding="utf-8"))
OUT = ROOT / "print"
OUT.mkdir(exist_ok=True)

LETTERS = "ABCD"


def E(s) -> str:
    return html.escape("" if s is None else str(s))


def fmt(s) -> str:
    if s is None:
        return ""
    text = str(s)
    text = html.escape(text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = text.replace("\n", "<br>")
    text = re.sub(
        r"-{3,}(?:\((\d+)\))?",
        lambda m: (
            f'<span class="blank">({m.group(1)})</span>'
            if m.group(1)
            else '<span class="blank">&nbsp;</span>'
        ),
        text,
    )
    return text


def render_docs(docs: list) -> str:
    parts = []
    for i, doc in enumerate(docs or []):
        blocks = doc if isinstance(doc, list) else [doc]
        extra = f'<div class="docn">文章 {i + 1}</div>' if len(docs) > 1 else ""
        body = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            t = b.get("t")
            if t == "title":
                body.append(f'<h3 class="dtitle">{fmt(b.get("x"))}</h3>')
            elif t == "p":
                body.append(f"<p>{fmt(b.get('x'))}</p>")
            elif t == "meta":
                rows = []
                for row in b.get("rows") or []:
                    if isinstance(row, (list, tuple)) and len(row) >= 2:
                        rows.append(
                            f"<tr><th>{fmt(row[0])}</th><td>{fmt(row[1])}</td></tr>"
                        )
                body.append(f'<table class="meta">{"".join(rows)}</table>')
            elif t == "list":
                items = "".join(f"<li>{fmt(x)}</li>" for x in (b.get("items") or []))
                body.append(f"<ul>{items}</ul>")
            elif t == "sign":
                body.append(f'<div class="sign">{fmt(b.get("x"))}</div>')
            elif b.get("x"):
                body.append(f"<p>{fmt(b.get('x'))}</p>")
        parts.append(f'<div class="doc">{extra}{"".join(body)}</div>')
    return f'<div class="docs">{"".join(parts)}</div>'


def render_options(options: list) -> str:
    bits = []
    for i, opt in enumerate(options or []):
        letter = LETTERS[i] if i < 4 else str(i + 1)
        bits.append(f'<div class="opt"><b>({letter})</b> {fmt(opt)}</div>')
    return f'<div class="opts">{"".join(bits)}</div>'


def render_question(q: dict, show_stem=True) -> str:
    label = E(q.get("label") or f"Q{q.get('no', '')}")
    stem = q.get("q")
    stem_html = f'<div class="stem">{fmt(stem)}</div>' if stem and show_stem else ""
    return (
        f'<div class="q"><div class="ql">{label}</div>'
        f"{stem_html}{render_options(q.get('options'))}</div>"
    )


def answer_line(q: dict) -> str:
    label = E(q.get("label") or f"Q{q.get('no', '')}")
    ans = (q.get("answer") or "").strip().upper()
    options = q.get("options") or []
    idx = LETTERS.find(ans)
    chosen = options[idx] if 0 <= idx < len(options) else ""
    tip = q.get("tip_zh") or ""
    exp = q.get("exp_zh") or ""
    detail = exp or tip
    text = f'<div class="akey"><b>{label}</b>　({E(ans)}) {fmt(chosen)}</div>'
    if detail:
        text += f'<div class="aexp">{fmt(detail)}</div>'
    return f'<div class="ans">{text}</div>'


def render_set(s: dict, kind: str) -> tuple[str, str]:
    """Return (questions_html, answers_html)."""
    label = E(s.get("label") or s.get("id") or "")
    intro = s.get("intro") or ""
    qs = s.get("questions") or []
    tag = {"part6": "Part 6", "reading": "Part 7", "grammar": "Part 5"}.get(kind, "")
    head = f'<div class="sethead"><span class="tag">{E(tag)}</span> {label}</div>'
    intro_h = f'<p class="intro">{fmt(intro)}</p>' if intro else ""
    docs_h = render_docs(s.get("docs") or [])
    qh = "".join(render_question(q) for q in qs)
    ah = "".join(answer_line(q) for q in qs)
    q_block = f'<section class="set">{head}{intro_h}{docs_h}{qh}</section>'
    a_block = f'<section class="aset"><div class="sethead">{label}</div>{ah}</section>'
    return q_block, a_block


def render_grammar_items(items: list) -> tuple[str, str]:
    qh = ['<section class="set"><div class="sethead"><span class="tag">Part 5</span> 语法真题</div>']
    ah = ['<section class="aset"><div class="sethead">Part 5 语法真题</div>']
    for q in items:
        qh.append(render_question(q))
        ah.append(answer_line(q))
    qh.append("</section>")
    ah.append("</section>")
    return "".join(qh), "".join(ah)


CSS = """
@page { size: A4; margin: 12mm 12mm 16mm 12mm; }
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  font: 10.6pt/1.45 "Noto Sans CJK SC", "Source Han Sans SC", "Noto Sans CJK JP",
        "Noto Sans", "DejaVu Sans", sans-serif;
  color: #111; background: #fff;
}
header {
  display: flex; justify-content: space-between; align-items: flex-end;
  border-bottom: 2.5px solid #111; padding-bottom: 8px; margin-bottom: 12px;
}
header h1 { font-size: 16pt; margin: 0 0 3px; }
header .sub { color: #333; font-size: 10pt; }
header .right { text-align: right; font-size: 9.5pt; color: #333; }
h2 { font-size: 12pt; margin: 16px 0 8px; border-left: 4px solid #111; padding-left: 8px; }
.set { margin: 0 0 14px; page-break-inside: auto; }
.sethead { font-weight: 700; font-size: 11pt; margin: 10px 0 6px; }
.tag {
  display: inline-block; border: 1px solid #111; padding: 0 6px;
  font-size: 8.5pt; margin-right: 6px; vertical-align: middle;
}
.intro { color: #333; font-size: 9.5pt; margin: 0 0 8px; }
.docs { margin-bottom: 8px; }
.doc {
  border: 1px solid #222; padding: 8px 10px; margin: 0 0 8px;
  background: #fafafa;
}
.docn { font-size: 8.5pt; font-weight: 700; margin-bottom: 4px; letter-spacing: .04em; }
.dtitle { font-size: 11.5pt; margin: 0 0 6px; }
.doc p { margin: 0 0 7px; }
.doc ul { margin: 4px 0 8px 1.2em; padding: 0; }
.doc li { margin: 2px 0; }
table.meta { border-collapse: collapse; margin: 0 0 8px; width: 100%; font-size: 10pt; }
table.meta th, table.meta td { border: 1px solid #444; padding: 3px 6px; text-align: left; }
table.meta th { width: 32%; background: #eee; }
.sign { white-space: pre-wrap; margin-top: 8px; font-family: inherit; }
.blank {
  display: inline-block; min-width: 3.2em; border-bottom: 1.4px solid #111;
  text-align: center; font-weight: 700; padding: 0 3px; margin: 0 2px;
}
.q { margin: 8px 0 10px; page-break-inside: avoid; }
.ql { font-weight: 700; margin-bottom: 3px; }
.stem { margin: 0 0 4px; }
.opts { margin-left: 0.4em; }
.opt { margin: 1px 0; }
.answers { page-break-before: always; }
.ans { margin: 0 0 9px; page-break-inside: avoid; }
.akey { font-size: 10.8pt; }
.aexp { color: #222; font-size: 10pt; margin: 2px 0 0; }
footer.note {
  margin-top: 14px; font-size: 8.5pt; color: #444;
  border-top: 1px solid #999; padding-top: 6px;
}
.toc { margin: 8px 0 16px; }
.toc li { margin: 4px 0; }
"""


def page(title: str, subtitle: str, right: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{E(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <div>
    <h1>{E(title)}</h1>
    <div class="sub">{fmt(subtitle)}</div>
  </div>
  <div class="right">{fmt(right)}</div>
</header>
{body}
<footer class="note">打印时请选 A4、实际大小，不要“缩放到可打印区域”。答案在后面单独几页，不想看见解析可以只打印前面的题目。</footer>
</body>
</html>
"""


def write_and_print(html_path: Path, pdf_path: Path, html: str) -> None:
    html_path.write_text(html, encoding="utf-8")
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def build_warmup() -> Path:
    w = DATA["warmup"]
    q_parts, a_parts = [], []
    for s in w.get("part6") or []:
        q, a = render_set(s, "part6")
        q_parts.append(q)
        a_parts.append(a)
    for s in w.get("reading") or []:
        q, a = render_set(s, "reading")
        q_parts.append(q)
        a_parts.append(a)
    body = (
        "<h2>题目</h2>"
        + "".join(q_parts)
        + '<div class="answers"><h2>答案与解析</h2>'
        + "".join(a_parts)
        + "</div>"
    )
    html = page(
        "TOEIC 考前加餐 · 11月10日",
        "15 题：Test 1 的 8 道 Part 6，加上两组阅读（Q147–148、Q181–185）",
        "约 20 分钟\n先做题，再看后面的答案",
        body,
    )
    pdf = OUT / "考前加餐_11月10日.pdf"
    write_and_print(OUT / "考前加餐_11月10日.html", pdf, html)
    return pdf


def build_day(n: str) -> Path:
    day = DATA["days"][n]
    date = day.get("date") or ""
    focus = day.get("focus_zh") or ""
    q_parts, a_parts = [], []
    if day.get("grammar"):
        q, a = render_grammar_items(day["grammar"])
        q_parts.append(q)
        a_parts.append(a)
    if day.get("part6"):
        for s in day["part6"]:
            q, a = render_set(s, "part6")
            q_parts.append(q)
            a_parts.append(a)
    if day.get("reading"):
        for s in day["reading"]:
            q, a = render_set(s, "reading")
            q_parts.append(q)
            a_parts.append(a)
    n_g = len(day.get("grammar") or [])
    n_p6 = sum(len(s.get("questions") or []) for s in (day.get("part6") or []))
    n_r = sum(len(s.get("questions") or []) for s in (day.get("reading") or []))
    total = n_g + n_p6 + n_r
    bits = [f"Part 5 {n_g} 题"]
    if n_p6:
        bits.append(f"Part 6 {n_p6} 题")
    bits.append(f"阅读 {n_r} 题")
    subtitle = f"{focus}　·　{'，'.join(bits)}，共 {total} 题"
    md, dd = date[5:7], date[8:10] if len(date) >= 10 else ("", "")
    title = f"TOEIC 考前复习 · 第{n}天 · {int(md)}月{int(dd)}日" if md else f"TOEIC 考前复习 · 第{n}天"
    body = (
        "<h2>题目</h2>"
        + "".join(q_parts)
        + '<div class="answers"><h2>答案与解析</h2>'
        + "".join(a_parts)
        + "</div>"
    )
    html = page(title, subtitle, "先做题，再看后面的答案\nA4 直接打印", body)
    safe = f"第{n}天_{int(md)}月{int(dd)}日.pdf" if md else f"第{n}天.pdf"
    html_name = safe.replace(".pdf", ".html")
    pdf = OUT / safe
    write_and_print(OUT / html_name, pdf, html)
    return pdf


def main() -> None:
    paths = [build_warmup()]
    for n in ["39", "40", "41", "42", "43", "44"]:
        paths.append(build_day(n))
    for p in paths:
        print(p, p.stat().st_size)
        subprocess.run(["pdfinfo", str(p)], check=False)


if __name__ == "__main__":
    main()
