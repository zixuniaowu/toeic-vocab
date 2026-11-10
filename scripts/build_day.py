#!/usr/bin/env python3
"""Build the TOEIC daily vocabulary site from data/dayN.json.

Usage:
  python3 scripts/build_day.py 2          # validate data/day2.json, make audio, render day2.html + index.html
  python3 scripts/build_day.py --all      # re-render every day (audio only for missing files)
  python3 scripts/build_day.py 2 --no-audio   # render only (skip edge-tts)
  python3 scripts/build_day.py 2 --check      # validate only, write nothing

What it does (in order):
  1. validate the day JSON (schema, 60 words, no Hangul, no duplicate words across days,
     warns about overlap with the podcast list /workspace/toeic_podcast/used_words.txt)
  2. cross-check the hand-written IPA against CMUdict (warnings only, needs `pip install cmudict`)
  3. generate missing pronunciation MP3s with edge-tts (en-US-AriaNeural, the same voice as
     the toeic800 podcast site): audio/dayN/<slug>.mp3 (word) and <slug>_ex.mp3 (example)
  4. render dayN.html (static HTML, works without JS except the study helpers), index.html,
     data/days.json, used_words.txt; optional exam-sprint self-tests: data/exam_sprint.json["days"]["N"]
     (Part 5 "grammar", "part6", Part 7 "reading") is merged into dayN.html, and exam-sprint.html +
     exam-warmup.html are rendered (regenerate the JSON with scripts/make_exam_sprint.py)
  5. final checks: no Hangul in any output, every referenced MP3 exists
"""
import argparse, asyncio, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUDIO = ROOT / "audio"
SITE_TITLE = "TOEIC 800 · 毎日背单词"
SITE_SUB_JA = "毎日60語・語根でまとめて覚える TOEIC 頻出単語（目標 800 点）"
SITE_SUB_ZH = "每天 60 词 · 按词根和主题记忆 · 音标 + 拼写 + 发音 + 中日双语释义"
COUNTER_ID = "toeic-vocab"
PODCAST_USED = Path("/workspace/toeic_podcast/used_words.txt")
DEFAULT_VOICE = "en-US-AriaNeural"
VIDEO_BASE = "media"  # compact MP4 served by GitHub Pages (iOS cannot play Release assets)
HANGUL = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uAC00-\uD7AF\uD7B0-\uD7FF\uFFA0-\uFFDC]")
WEEK_ZH = "一二三四五六日"
WEEK_JA = "月火水木金土日"

E = lambda s: html.escape(str(s), quote=True)


def slug(w):
    return re.sub(r"[^a-z0-9]+", "-", w.lower()).strip("-") or "word"


def spell(w):
    return " ".join("-".join(ch.upper() for ch in part if ch.isalpha()) for part in re.split(r"[\s]+", w) if part)


def words_of(day):
    return [w for g in day["groups"] for w in g["words"]]


def publish_date(n):
    """Actual publish date (Asia/Tokyo) of day n: the JST date of the git commit that first
    added dayN.html; if not yet committed, today's date in Asia/Tokyo (the daily build)."""
    import datetime as dt, subprocess, os
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ad", "--date=format-local:%Y-%m-%d",
                              "--", f"day{n}.html"], cwd=ROOT, capture_output=True, text=True,
                             env={**os.environ, "TZ": "Asia/Tokyo"}).stdout.split()
        if out:
            return out[-1]
    except Exception:
        pass
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()


def load_day(n):
    p = DATA / f"day{n}.json"
    if not p.exists():
        sys.exit(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def all_days():
    out = []
    for p in DATA.glob("day*.json"):
        m = re.fullmatch(r"day(\d+)\.json", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)

# ------------------------------------------------------------------ validation

REQ_WORD = ["w", "pos", "ipa", "zh", "ja", "ex", "ex_zh", "ex_ja", "parts", "forms"]


def validate(n, day, strict_count=True):
    errs, warns = [], []
    raw = json.dumps(day, ensure_ascii=False)
    if HANGUL.search(raw):
        errs.append("Hangul characters found in day JSON: " + ", ".join(sorted(set(HANGUL.findall(raw)))))
    if day.get("day") != n:
        errs.append(f'"day" field is {day.get("day")!r}, expected {n}')
    for k in ["date", "title_zh", "title_ja", "roots", "groups"]:
        if not day.get(k):
            errs.append(f"missing day field {k!r}")
    ws = words_of(day)
    if strict_count and len(ws) != 60:
        warns.append(f"day {n} has {len(ws)} words (target 60)")
    seen = set()
    for w in ws:
        for k in REQ_WORD:
            if k not in w or (k not in ("parts", "forms") and not str(w[k]).strip()):
                errs.append(f"{w.get('w')}: missing {k}")
        key = w["w"].lower()
        if key in seen:
            errs.append(f"duplicate word in day: {w['w']}")
        seen.add(key)
        if not (w["ipa"].startswith("/") and w["ipa"].endswith("/")):
            errs.append(f"{w['w']}: ipa must look like /.../")
        if not w["parts"] and not w.get("note"):
            errs.append(f"{w['w']}: no parts -> a note explaining 'no meaningful root breakdown' is required")
        for p in w["parts"]:
            if len(p) != 3:
                errs.append(f"{w['w']}: part {p} must be [piece, zh, ja]")
        if not (2 <= len(w["forms"]) <= 3):
            warns.append(f"{w['w']}: {len(w['forms'])} related forms (2-3 expected)")
        for f in w["forms"]:
            if len(f) != 3:
                errs.append(f"{w['w']}: form {f} must be [en, zh, ja]")
        if not find_hl(w):
            warns.append(f"{w['w']}: headword not found in example (add \"hl\": \"<form used>\")")
    known = {w["w"].lower() for w in ws}
    for r in day.get("roots", []):
        for x in r.get("examples", []):
            if x.lower() not in known:
                warns.append(f"root {r['root']}: example {x} is not a word of the day (no link)")
    # duplicates against other days of this site
    for m in all_days():
        if m == n:
            continue
        other = {w["w"].lower() for w in words_of(load_day(m))}
        dup = sorted(known & other)
        if dup:
            errs.append(f"words already used on day {m}: {', '.join(dup)}")
    if PODCAST_USED.exists():
        pod = {l.strip().lower() for l in PODCAST_USED.read_text(encoding="utf-8").splitlines() if l.strip()}
        dup = sorted(known & pod)
        if dup:
            warns.append("overlap with podcast used_words.txt (allowed, but prefer new words): " + ", ".join(dup))
    return errs, warns


def ipa_crosscheck(day):
    """Compare the hand-written IPA with CMUdict (stress/vowel sanity check). Warnings only."""
    try:
        import cmudict  # noqa
    except ImportError:
        return ["cmudict not installed: IPA cross-check skipped (pip install cmudict)"]
    d = cmudict.dict()
    V = {"AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ", "EH": "ɛ", "ER": "ɝ", "EY": "eɪ",
         "IH": "ɪ", "IY": "i", "OW": "oʊ", "OY": "ɔɪ", "UH": "ʊ", "UW": "u"}
    out = []
    for w in words_of(day):
        prons = d.get(w["w"].lower())
        if not prons:
            continue
        # primary-stressed vowel of each CMU pronunciation must appear right after the ˈ mark
        ok = False
        for pr in prons:
            prim = [p[:-1] for p in pr if p.endswith("1")]
            if not prim:
                continue
            seg = w["ipa"].split("ˈ", 1) if "ˈ" in w["ipa"] else ["", w["ipa"]]
            if len(seg) == 2 and V[prim[0]][0] in re.sub(r"[^ɑæʌɔaɛɝeɪiouʊəɚ]", "", seg[1])[:3]:
                ok = True
        if not ok:
            out.append(f"IPA check: {w['w']} {w['ipa']} vs CMU {[' '.join(p) for p in prons]}")
    return out

# ------------------------------------------------------------------ audio


async def _tts(text, path, voice):
    import edge_tts
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, voice).save(str(path))
            if path.stat().st_size > 1000:
                return
        except Exception as e:  # network hiccup: retry
            err = e
        await asyncio.sleep(2 + attempt * 3)
    raise RuntimeError(f"edge-tts failed for {path.name}: {err if 'err' in dir() else 'empty file'}")


def make_audio(n, day, force=False):
    try:
        import edge_tts  # noqa
    except ImportError:
        sys.exit("edge-tts missing: pip install edge-tts  (or run with --no-audio)")
    voice = day.get("voice") or DEFAULT_VOICE
    out = AUDIO / f"day{n}"
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for w in words_of(day):
        s = slug(w["w"])
        jobs.append((w.get("say") or w["w"], out / f"{s}.mp3"))
        jobs.append((w["ex"], out / f"{s}_ex.mp3"))
    todo = [(t, p) for t, p in jobs if force or not p.exists() or p.stat().st_size < 1000]
    print(f"audio: {len(jobs)} files, {len(todo)} to generate ({voice})")

    async def run():
        sem = asyncio.Semaphore(6)

        async def one(t, p):
            async with sem:
                await _tts(t, p, voice)
        await asyncio.gather(*(one(t, p) for t, p in todo))
    if todo:
        asyncio.run(run())

# ------------------------------------------------------------------ rendering


def bi(zh, ja, tag="span", cls=""):
    """Both languages; CSS shows only the active UI language."""
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c}><span class="z">{zh}</span><span class="j" lang="ja">{ja}</span></{tag}>'


def find_hl(w):
    if w.get("hl"):
        return w["hl"] if w["hl"] in w["ex"] else None
    head = w["w"].split()[0]
    stem = re.escape(head[:max(len(head) - 2, 4)])
    m = re.search(rf"\b{stem}[a-z]*", w["ex"], re.I)
    return m.group(0) if m else None


def ex_html(w):
    hl = find_hl(w)
    t = E(w["ex"])
    if hl:
        t = t.replace(E(hl), f"<b>{E(hl)}</b>", 1)
    return t


def part_kind(p):
    if p.endswith("-") or re.search(r"-\s*\(", p) or re.match(r"^[a-z()]+-( |$)", p):
        return "pre"
    if p.startswith("-"):
        return "suf"
    return "root"


def fmt_date(iso, lang):
    import datetime as dt
    d = dt.date.fromisoformat(iso)
    if lang == "ja":
        return f"{d.year}年{d.month}月{d.day}日（{WEEK_JA[d.weekday()]}）"
    return f"{d.year}年{d.month}月{d.day}日（周{WEEK_ZH[d.weekday()]}）"


HEAD = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#4f7cf0">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%9A%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="assets/style.css?v={v}">
<script>try{{if(localStorage.getItem('tv.lang')==='ja')document.documentElement.classList.add('ja')}}catch(e){{}}</script>
</head>
<body class="{body}">
"""

LANGSW = ('<div class="langsw" role="group" aria-label="Language"><button type="button" data-lang="zh">中文</button>'
          '<button type="button" data-lang="ja" lang="ja">日本語</button></div>')

FOOT = """<footer class="wrap">
  <div class="counter">{cnt} <img src="https://visitor-badge.laobi.icu/badge?page_id={cid}&amp;left_text=views&amp;left_color=%23555&amp;right_color=%230ea5e9" alt="visitors" referrerpolicy="no-referrer-when-downgrade"></div>
  <div>{note}</div>
  <div class="links"><a href="https://zixuniaowu.github.io/toeic800/">🎧 TOEIC 800 冲刺 · 边听边学</a> · <a href="https://zixuniaowu.github.io/toeic-ip-mock/">📝 IP 模拟考试</a></div>
</footer>
<script src="assets/app.js?v={v}"></script>
</body>
</html>
"""


def footer(v):
    return FOOT.format(cnt=bi("访问人数", "訪問数"), cid=COUNTER_ID, v=v,
                       note=bi("单词、例句均为原创 · 语音为 AI 合成（Microsoft Edge TTS）· 仅供学习使用",
                               "単語・例文はオリジナル · 音声は AI 合成（Microsoft Edge TTS）· 学習専用"))


# ------------------------------------------------------------------ exam sprint (optional grammar / Part 6 / reading)
# Optional day fields "grammar" (Part 5 items), "part6" and "reading" (sets with passages) render as self-test
# sections above the video and the 60 words. data/exam_sprint.json["days"]["N"] is merged in automatically
# (fields already present in dayN.json win). Days without these fields render exactly as before.
SPRINT_FILE = DATA / "exam_sprint.json"
BLANK = re.compile(r"-{3,}\s*(\(\d+\))?")


def load_sprint():
    if SPRINT_FILE.exists():
        return json.loads(SPRINT_FILE.read_text(encoding="utf-8"))
    return None


def merge_sprint(n, day, sp):
    d = (sp or {}).get("days", {}).get(str(n))
    if not d:
        return day
    out = dict(day)
    for k in ("grammar", "part6", "reading", "focus_zh", "focus_ja"):
        if d.get(k) and not out.get(k):
            out[k] = d[k]
    return out


def has_exam(day):
    return bool(day.get("grammar") or day.get("part6") or day.get("reading"))


def xtext(s):
    """Escape test text; mark blanks; keep line breaks."""
    t = E(s)
    t = BLANK.sub(lambda m: f'<span class="xblank">{m.group(1) or ""}</span>', t)
    return t.replace("\n", "<br>")


def x_block(b):
    t = b.get("t")
    if t == "title":
        return f'<div class="xd-title">{xtext(b["x"])}</div>'
    if t == "meta":
        rows = "".join(f"<tr><th>{xtext(r[0])}</th><td>{xtext(r[1]) if len(r) > 1 else ''}</td></tr>" for r in b["rows"])
        return f'<table class="xd-meta">{rows}</table>'
    if t == "msg":
        return f'<div class="xd-msg"><div class="xd-who"><b>{xtext(b.get("who", ""))}</b> <span>{xtext(b.get("time", ""))}</span></div><div>{xtext(b["x"])}</div></div>'
    if t == "sign":
        return f'<div class="xd-sign">{xtext(b["x"])}</div>'
    if t == "list":
        return '<ul class="xd-list">' + "".join(f"<li>{xtext(i)}</li>" for i in b["items"]) + "</ul>"
    if t == "table":
        head = "".join(f"<th>{xtext(c)}</th>" for c in b.get("cols", []))
        body = "".join("<tr>" + "".join(f"<td>{xtext(c)}</td>" for c in r) + "</tr>" for r in b.get("rows", []))
        cap = f'<caption>{xtext(b["cap"])}</caption>' if b.get("cap") else ""
        return f'<div class="xd-tw"><table class="xd-table">{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    return f'<p>{xtext(b.get("x", ""))}</p>'


def x_docs(s):
    docs = []
    for d in s.get("docs") or []:
        docs.append("".join(x_block(b) for b in d))
    for d in s.get("text_docs") or []:
        docs.append("".join(f"<p>{xtext(par)}</p>" for par in re.split(r"\n\s*\n", d) if par.strip()))
    many = len(docs) > 1
    out = []
    for i, d in enumerate(docs, 1):
        tag = f'<div class="xd-n">{bi(f"文章 {i}", f"文書 {i}")}</div>' if many else ""
        out.append(f'<div class="xdoc">{tag}{d}</div>')
    return '<div class="xdocs">' + "".join(out) + "</div>"


def x_question(q, label, topic=None, stem=True):
    ans = q["answer"]
    qid = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-")
    head = f'<span class="xlab">{E(label)}</span>'
    if topic:
        head += f'<span class="xtag">{bi(E(topic[0]), E(topic[1]))}</span>'
    st = f'<div class="xstem">{xtext(q["q"])}</div>' if stem and q.get("q") else ""
    opts = "".join(f'<button type="button" class="xo" data-k="{k}"><b>({k})</b> {xtext(o)}</button>'
                   for k, o in zip("ABCD", q["options"]))
    right = q["options"]["ABCD".index(ans)]
    body = f'<div class="xkey">✅ {bi("正确答案", "正解")} <b>({ans}) {xtext(right)}</b></div>'
    if q.get("tip_zh"):
        body += f'<div class="xtip">💡 {bi(E(q["tip_zh"]), E(q.get("tip_ja") or q["tip_zh"]))}</div>'
    if q.get("exp_zh"):
        body += '<div class="xexp">' + bi(E(q["exp_zh"]), E(q.get("exp_ja") or q["exp_zh"])) + "</div>"
    if q.get("vocab_zh"):
        body += '<div class="xvoc">📖 ' + bi(E(q["vocab_zh"]), E(q.get("vocab_ja") or q["vocab_zh"])) + "</div>"
    return (f'<div class="xq" id="x-{qid}" data-qid="{qid}" data-ans="{ans}"><div class="xqh">{head}</div>{st}'
            f'<div class="xopts">{opts}</div><details class="xans"><summary>{bi("👆 点选项作答，或点这里看答案", "👆 選択肢をタップ、またはここで答えを見る")}</summary>'
            f'<div class="xbody">{body}</div></details></div>')


def x_set(s, part):
    kind = ""
    nd = len(s.get("docs") or []) + len(s.get("text_docs") or [])
    if part == 7:
        kind = {1: ("单篇", "シングル"), 2: ("双篇", "ダブル"), 3: ("三篇", "トリプル")}.get(nd, ("多篇", "マルチ"))
        kind = f'<span class="xtag">{bi(*kind)}</span>'
    qs = "".join(x_question(q, q["label"], stem=True) for q in s["questions"])
    return (f'<article class="xset" id="x-{E(s["id"])}"><div class="xsh"><span class="xlab">{E(s["label"])}</span>{kind}</div>'
            f'<p class="xintro">{E(s["intro"])}</p>{x_docs(s)}<div class="xqs">{qs}</div></article>')


def x_section(sid, h_zh, h_ja, note_zh, note_ja, inner, nq):
    return (f'<section class="card xsec" id="{sid}" data-sec="{sid}"><h2>{bi(h_zh, h_ja)} <small>{bi(f"{nq} 题", f"{nq} 問")}</small></h2>'
            f'<p class="xnote">{bi(note_zh, note_ja)}</p>{inner}'
            f'<div class="xbar"><span class="xscore"></span><button type="button" class="tb xreset">{bi("🔄 清空重做", "🔄 リセット")}</button></div></section>')


def render_exam(day, prefix=""):
    """Self-test sections (Part 5 grammar, Part 6, Part 7 reading). Returns a list of HTML strings."""
    out = []
    g = day.get("grammar") or []
    if g:
        inner = '<div class="xqs">' + "".join(
            x_question(q, q["label"], (q.get("topic_zh"), q.get("topic_ja")) if q.get("topic_zh") else None) for q in g) + "</div>"
        out.append(x_section(f"{prefix}grammar", "✏️ 语法真题 · Part 5", "✏️ 文法の本番問題 · Part 5",
                             "先做题，再背单词。每题约 20 秒；点选项立即看答案、提示和解析。",
                             "単語の前にまず解きましょう。1問約20秒。選択肢をタップすると正解・ヒント・解説が出ます。", inner, len(g)))
    p6 = day.get("part6") or []
    if p6:
        inner = "".join(x_set(s, 6) for s in p6)
        n6 = sum(len(s["questions"]) for s in p6)
        out.append(x_section(f"{prefix}part6", "🧩 Part 6 真题复习", "🧩 Part 6 本番問題の復習",
                             "先读整篇，空格的线索在前后句：语法题先找谓语，词汇题看上下文，句子插入看前后句的指代。",
                             "まず全体を読みましょう。ヒントは前後の文にあります。文法は述語を探し、語彙は文脈、文挿入は前後の指示語を確認。", inner, n6))
    rd = day.get("reading") or []
    if rd:
        inner = "".join(x_set(s, 7) for s in rd)
        n7 = sum(len(s["questions"]) for s in rd)
        out.append(x_section(f"{prefix}reading", f"📖 阅读训练 · Part 7（{len(rd)} 组）", f"📖 読解トレーニング · Part 7（{len(rd)} セット）",
                             "先看题目再回原文找依据，每题约 1 分钟。多篇题要把日期、人名、数字在几篇之间对起来。",
                             "先に設問を読んでから本文で根拠を探しましょう。1問約1分。複数文書は日付・人名・数字を照合。", inner, n7))
    return out


def exam_toc(day):
    t = []
    if day.get("grammar"):
        t.append(f'<a href="#grammar">{bi("✏️ 语法真题", "✏️ 文法")} <small>{len(day["grammar"])}</small></a>')
    if day.get("part6"):
        t.append(f'<a href="#part6">{bi("🧩 Part 6", "🧩 Part 6")} <small>{sum(len(s["questions"]) for s in day["part6"])}</small></a>')
    if day.get("reading"):
        t.append(f'<a href="#reading">{bi("📖 阅读训练", "📖 読解")} <small>{sum(len(s["questions"]) for s in day["reading"])}</small></a>')
    return "".join(t)


def render_word(n, i, w):
    s = slug(w["w"])
    a = f"audio/day{n}/{s}.mp3"
    ax = f"audio/day{n}/{s}_ex.mp3"
    parts = ""
    if w["parts"]:
        chips = []
        for p, zh, ja in w["parts"]:
            chips.append(f'<span class="chip {part_kind(p)}"><b>{E(p)}</b><span class="cz">{E(zh)}</span><span class="cj" lang="ja">{E(ja)}</span></span>')
        parts = '<div class="chips">' + '<span class="plus">+</span>'.join(chips) + "</div>"
    note = ""
    if w.get("note"):
        note = bi(E(w["note"]["zh"]), E(w["note"]["ja"]), "div", "rnote")
    forms = "".join(f'<li><b>{E(en)}</b> <span class="pair"><span class="cz">{E(zh)}</span><span class="cj" lang="ja">{E(ja)}</span></span></li>' for en, zh, ja in w["forms"])
    tip = ""
    if w.get("tip"):
        tip = '<div class="tipbox">💡 ' + bi(E(w["tip"]["zh"]), E(w["tip"].get("ja") or w["tip"]["zh"])) + "</div>"
    return f"""<li class="wd" id="w-{s}" data-w="{E(w['w'])}">
 <div class="wh"><span class="wn">{i}</span><div class="wt"><b class="hw">{E(w['w'])}</b><span class="pos">{E(w['pos'])}</span>
  <div class="ph"><span class="ipa">{E(w['ipa'])}</span></div><div class="spell" aria-label="spelling">{E(spell(w['w']))}</div></div>
  <button type="button" class="say" data-src="{a}" aria-label="play {E(w['w'])}">🔊</button></div>
 <div class="hid">
  <div class="mean"><div class="m mz"><i>中</i>{E(w['zh'])}</div><div class="m mj" lang="ja"><i>日</i>{E(w['ja'])}</div></div>
 </div>
 <div class="ex"><button type="button" class="say sm" data-src="{ax}" aria-label="play example">🔊</button><div class="ext"><div class="en">{ex_html(w)}</div>
  <div class="hid"><div class="exzh">{E(w['ex_zh'])}</div><div class="exja" lang="ja">{E(w['ex_ja'])}</div></div></div></div>
 <div class="hid">
  <div class="sec"><div class="lbl">{bi('🧩 词根拆解', '🧩 語源分解')}</div>{parts}{note}</div>
  <div class="sec"><div class="lbl">{bi('🔗 相关形式 / 搭配', '🔗 関連語・コロケーション')}</div><ul class="forms">{forms}</ul></div>
  {tip}
 </div>
 <div class="peek">{bi('👆 点击显示释义', '👆 タップで意味を表示')}</div>
 <label class="mk"><input type="checkbox" data-w="{E(w['w'])}"> {bi('✓ 已掌握', '✓ 覚えた')}</label>
</li>"""


def render_day(n, day, prev_day, next_day, v):
    ws = words_of(day)
    known = {w["w"].lower(): w for w in ws}
    title = f"Day {n} · {day['title_zh']} | {SITE_TITLE}"
    out = [HEAD.format(title=E(title), desc=E(f"TOEIC 600–850 高频词 {len(ws)} 个：{day['title_zh']}。音标、逐字母拼写、发音、词根拆解、中日双语。"), v=v, body="dayp")]
    out.append(f'<header class="bar"><div class="wrap barin"><a href="index.html">← {E(SITE_TITLE)}</a>{LANGSW}</div></header>')
    out.append('<main class="wrap daygrid">')
    out.append(f'<h1 class="title">Day {n} · ' + bi(E(day["title_zh"]), E(day["title_ja"])) + "</h1>")
    out.append(f'<div class="meta">' + bi(f"{len(ws)} 词 · {fmt_date(day['date'], 'zh')}", f"{len(ws)} 語 · {fmt_date(day['date'], 'ja')}") + "</div>")
    if day.get("intro_zh"):
        out.append('<p class="intro">' + bi(E(day["intro_zh"]), E(day.get("intro_ja") or day["intro_zh"])) + "</p>")
    if has_exam(day):  # exam sprint: self-test before the words
        out.append('<div class="xban">' + bi(f"🎯 考前冲刺：先做下面的真题，再背 {len(ws)} 个单词" + (f"（今日重点：{E(day['focus_zh'])}）" if day.get("focus_zh") else ""),
                                            f"🎯 試験直前対策：まず下の本番問題、それから {len(ws)} 語" + (f"（今日のポイント：{E(day['focus_ja'])}）" if day.get("focus_ja") else ""))
                   + f' · <a href="exam-sprint.html">{bi("冲刺计划", "対策プラン")}</a></div>')
        out += render_exam(day)
    # explanation video: media/dayN.mp4 on Pages (made by make_day_video.py)
    vurl = f"{VIDEO_BASE}/day{n}.mp4"
    out.append('<section class="card" id="video"><h2>' + bi("🎬 讲解视频", "🎬 解説動画") + "</h2>")
    out.append(f'<video class="dayvid" controls preload="metadata" playsinline src="{vurl}">')
    out.append(bi("您的浏览器不支持 video 标签。", "お使いのブラウザは video タグに対応していません。") + "</video>")
    out.append('<p class="meta" style="margin-top:.6rem">' + bi(
        f'<a href="{vurl}" download>下载本课视频（MP4）</a>',
        f'<a href="{vurl}" download>このレッスンの動画をダウンロード（MP4）</a>') + "</p>")
    out.append("</section>")
    # sidebar (desktop: sticky right column; mobile: display:contents, so the order is unchanged)
    sp = f'<a href="day{prev_day}.html">← Day {prev_day}</a>' if prev_day else "<span></span>"
    sn = f'<a href="day{next_day}.html">Day {next_day} →</a>' if next_day else '<a href="index.html">' + bi("全部日期", "一覧へ") + "</a>"
    out.append('<aside class="side"><div class="sidein">')
    out.append(f'<div class="sidenav card"><a class="sidehome" href="index.html">' + bi("📅 全部日期", "📅 日付一覧") + f'</a><div class="nav">{sp}{sn}</div></div>')
    # root spotlight
    out.append('<section class="card spot"><h2>' + bi("🔍 今日词根", "🔍 今日の語根") + "</h2>")
    for r in day["roots"]:
        ex = []
        for x in r["examples"]:
            w = known.get(x.lower())
            if w:
                ex.append(f'<a class="rx" href="#w-{slug(w["w"])}"><b>{E(w["w"])}</b><span class="rz">{E(w["zh"].split("；")[0])}</span><span class="rj" lang="ja">{E(w["ja"].split("；")[0])}</span></a>')
            else:
                ex.append(f'<span class="rx"><b>{E(x)}</b></span>')
        out.append(f"""<div class="root"><div class="rh"><span class="rname">{E(r['root'])}</span><span class="rmean pair"><span class="cz">{E(r['zh'])}</span><span class="cj" lang="ja">{E(r['ja'])}</span></span><span class="rorig">{E(r.get('origin',''))}</span></div>
 {bi(E(r['exp_zh']), E(r['exp_ja']), 'p', 'rexp')}<div class="rxs">{''.join(ex)}</div></div>""")
    out.append("</section>")
    toc = exam_toc(day) + "".join(f'<a href="#g-{E(g["id"])}">{bi(E(g["title_zh"]), E(g["title_ja"]))} <small>{len(g["words"])}</small></a>' for g in day["groups"])
    out.append(f'<nav class="toc stoc card"><div class="lbl">' + bi("📑 本课目录", "📑 目次") + f'</div>{toc}<a href="#quiz">' + bi("📝 小测验", "📝 ミニテスト") + '</a></nav>')
    out.append("</div></aside>")
    # toolbar
    out.append(f"""<div class="tools" id="tools">
 <button type="button" id="tHide" class="tb">{bi('🙈 遮住释义', '🙈 意味を隠す')}</button>
 <button type="button" id="tPlay" class="tb">{bi('▶ 全部播放', '▶ 全部再生')}</button>
 <button type="button" id="tTodo" class="tb">{bi('只看未掌握', '未習得のみ')}</button>
 <span class="prog" id="prog"></span>
</div>""")
    # contents
    out.append(f'<nav class="toc mtoc">{toc}</nav>')
    i = 0
    for g in day["groups"]:
        out.append(f'<section class="card grp" id="g-{E(g["id"])}"><h2>' + bi(E(g["title_zh"]), E(g["title_ja"])) + f' <small>{len(g["words"])}</small></h2><ol class="wlist">')
        for w in g["words"]:
            i += 1
            out.append(render_word(n, i, w))
        out.append("</ol></section>")
    # quiz
    out.append('<section class="card" id="quiz"><h2>' + bi("📝 小测验（10 题）", "📝 ミニテスト（10問）") + '</h2><div id="quizBox"></div></section>')
    qd = [{"w": w["w"], "s": slug(w["w"]), "zh": "；".join(w["zh"].split("；")[:2]), "ja": "；".join(w["ja"].split("；")[:2])} for w in ws]
    out.append(f'<script type="application/json" id="wdata">{json.dumps({"day": n, "words": qd}, ensure_ascii=False)}</script>')
    nav_l = f'<a href="day{prev_day}.html">← Day {prev_day}</a>' if prev_day else "<span></span>"
    nav_r = f'<a href="day{next_day}.html">Day {next_day} →</a>' if next_day else '<a href="index.html">' + bi("全部日期", "一覧へ") + "</a>"
    out.append(f'<div class="nav">{nav_l}{nav_r}</div>')
    out.append("</main>")
    out.append(footer(v))
    return "\n".join(out)


def render_index(days, v, sp=None):
    out = [HEAD.format(title=E(SITE_TITLE), desc=E(SITE_SUB_ZH), v=v, body="home")]
    out.append(f"""<header class="hero"><div class="wrap"><div class="herotop">{LANGSW}</div>
<h1>{E(SITE_TITLE)}</h1>
<p class="sub" lang="ja">{E(SITE_SUB_JA)}</p>
<p class="sub2">{bi(E(SITE_SUB_ZH), 'TOEIC 550〜650 → 800 を目指す人のための単語帳。IPA・つづり・音声・語源・中日の意味つき。')}</p>
</div></header>
<main class="wrap"><ul class="list">""")
    if sp and sp.get("days"):
        b = sprint_banner(sp)
        if b:
            out.append(f"  <li>{b}</li>")
    newest = days[-1][0] if days else None
    for n, d in reversed(days):
        cnt = len(words_of(d))
        new = f'<span class="badge-new">NEW</span>' if n == newest else ""
        roots = "  ·  ".join(r["root"] for r in d.get("roots", []))
        out.append(f"""  <li><a class="ep" href="day{n}.html" data-day="{n}" data-total="{cnt}">
    <div class="num">{n}<small>Day</small></div>
    <div><h2>{bi(E(d['title_zh']), E(d['title_ja']))}{new}</h2>
    <div class="meta">{bi(f"{cnt} 词 · {fmt_date(d['date'], 'zh')}", f"{cnt} 語 · {fmt_date(d['date'], 'ja')}")}</div>
    <div class="meta roots">{E(roots)}</div>
    <div class="meta done"></div></div>
  </a></li>""")
    out.append("</ul>")
    out.append('<p class="tip">' + bi("💡 每个单词都有 🔊 发音、逐字母拼写和词根拆解；“已掌握”的记录保存在本机浏览器。",
                                     "💡 各単語に 🔊 音声・つづり・語源分解つき。「覚えた」の記録はこの端末のブラウザに保存されます。") + "</p>")
    out.append("</main>")
    out.append(footer(v))
    return "\n".join(out)


# ------------------------------------------------------------------ exam sprint pages (exam-sprint.html, exam-warmup.html)


def _bar(v, title):
    return [HEAD.format(title=E(title), desc=E(title), v=v, body="dayp xpage"),
            f'<header class="bar"><div class="wrap barin"><a href="index.html">← {E(SITE_TITLE)}</a>{LANGSW}</div></header>',
            '<main class="wrap">']


def _days_left(sp):
    import datetime as dt
    from zoneinfo import ZoneInfo
    today = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return (dt.date.fromisoformat(sp["exam_date"]) - today).days


def render_plan(sp, nums, v):
    ed = sp["exam_date"]
    out = _bar(v, f"考前冲刺计划 · {ed} TOEIC IP | {SITE_TITLE}")
    out.append('<h1 class="title">' + bi("🎯 考前冲刺计划", "🎯 試験直前対策プラン") + "</h1>")
    out.append('<div class="meta">' + bi(f"考试：{fmt_date(ed, 'zh')} · {E(sp['exam_zh'])}", f"試験：{fmt_date(ed, 'ja')} · {E(sp['exam_ja'])}") + "</div>")
    out.append('<section class="card"><h2>' + bi("每天怎么做", "毎日の進め方") + "</h2><ol class=\"xsteps\">"
               + "<li>" + bi("✏️ 先做 15 道 Part 5 语法真题（约 5–8 分钟），点选项立刻看答案和解析。", "✏️ まず Part 5 の文法問題15問（約5〜8分）。選択肢をタップすると正解と解説が出ます。") + "</li>"
               + "<li>" + bi("📖 再做 3 组 Part 7 阅读（约 12 题，按每题 1 分钟计时）。先看题目，再回原文找依据。", "📖 次に Part 7 の読解3セット（約12問、1問1分で計時）。設問を先に読み、本文で根拠を探します。") + "</li>"
               + "<li>" + bi("📚 最后背当天 60 个单词；时间不够时，单词可以以后补。", "📚 最後にその日の60語。時間がなければ単語は後回しで構いません。") + "</li>"
               + "<li>" + bi("🎧 听力 Part 1–4 题型已经全部讲完：这周抽一次用 IP 模式完整做一遍模拟考，查漏补缺。", "🎧 リスニング Part 1〜4 は解説済み。今週一度 IP モードで模試を通して解き、弱点を確認しましょう。")
               + ' <a href="https://zixuniaowu.github.io/toeic-ip-mock/">📝 IP 模拟考试</a></li></ol>'
               + '<p class="xnote">' + bi("三套真题的 Part 5 共 90 题，6 天每天 15 题，正好全部再做一遍；阅读优先安排还没练过的篇目。", "3セットの Part 5 全90問を6日間で毎日15問、ちょうど一巡します。読解はまだ練習していないセットを優先。") + "</p></section>")
    out.append('<section class="card"><h2>' + bi("🌙 今晚的热身（11/10）", "🌙 今夜のウォームアップ（11/10）") + "</h2><p>"
               + bi("Test 1 Part 6 八道题（刚在第 58–59 期讲过）+ 两组熟悉的 Part 7。", "Test 1 Part 6 の8問（第58〜59回で解説済み）＋ おなじみの Part 7 の2セット。")
               + '</p><a class="btn" href="exam-warmup.html">' + bi("开始热身练习 →", "ウォームアップを始める →") + "</a></section>")
    out.append('<section class="card"><h2>' + bi("📅 6 天安排", "📅 6日間の予定") + '</h2><ol class="xplan">')
    for n_s, d in sorted(sp["days"].items(), key=lambda x: int(x[0])):
        n = int(n_s)
        gl = " · ".join(q["label"].replace("Test ", "T").replace(" · ", " ") for q in d["grammar"])
        p6 = d.get("part6") or []
        rl = " · ".join(f'{E(r["label"])}（{len(r["questions"])}）' for r in d["reading"])
        rq = sum(len(r["questions"]) for r in d["reading"])
        link = (f'<a class="btn sm" href="day{n}.html">' + bi("打开 →", "開く →") + "</a>") if n in nums else \
            ('<span class="xsoon">' + bi("当天早上发布", "当日の朝に公開") + "</span>")
        p6h = ""
        if p6:
            p6h = "<div><b>" + bi("Part 6 复习", "Part 6 復習") + f"</b> {E(' · '.join(s['label'] for s in p6))}（{sum(len(s['questions']) for s in p6)}）</div>"
        out.append(f'<li class="xpd"><div class="xpdh"><span class="num">{n}<small>Day</small></span><div><b>{bi(fmt_date(d["date"], "zh"), fmt_date(d["date"], "ja"))}</b>'
                   f'<div class="meta">{bi(E(d["focus_zh"]), E(d["focus_ja"]))}</div></div>{link}</div>'
                   f'<div class="xpdb"><div><b>{bi("语法 Part 5", "文法 Part 5")}</b>（{len(d["grammar"])}）<span class="xids">{E(gl)}</span></div>{p6h}'
                   f'<div><b>{bi("阅读 Part 7", "読解 Part 7")}</b>（{rq}）{rl}</div></div></li>')
    out.append("</ol></section>")
    out.append(f'<div class="xban">{bi("📅 考试当天 11/17：不做新题，提前检查电脑和网络环境，前一晚早点休息。加油！", "📅 試験当日 11/17：新しい問題はやらず、PC とネット環境を事前に確認し、前の晩は早めに休みましょう。がんばって！")}</div>')
    out.append("</main>")
    out.append(footer(v))
    return "\n".join(out)


def render_warmup(sp, v):
    w = sp["warmup"]
    out = _bar(v, f"今晚热身 · Part 6 + Part 7 | {SITE_TITLE}")
    out.append('<h1 class="title">' + bi("🌙 今晚热身：Part 6 + Part 7", "🌙 今夜のウォームアップ：Part 6 + Part 7") + "</h1>")
    n6 = sum(len(s["questions"]) for s in w["part6"]); n7 = sum(len(s["questions"]) for s in w["reading"])
    out.append('<div class="meta">' + bi(f"{fmt_date(w['date'], 'zh')} · {n6 + n7} 题（约 20 分钟）", f"{fmt_date(w['date'], 'ja')} · {n6 + n7} 問（約20分）")
               + f' · <a href="exam-sprint.html">{bi("冲刺计划", "対策プラン")}</a></div>')
    out.append('<p class="intro">' + bi("先做 Test 1 Part 6 的两篇（第 58–59 期刚讲过，检验是否还记得线索），再做两组熟悉的 Part 7。明天开始每天的单词页会带 15 道语法 + 3 组阅读。",
                                        "まず Test 1 Part 6 の2つの文章（第58〜59回で解説済み。ヒントを覚えているか確認）、次におなじみの Part 7 を2セット。明日から毎日の単語ページに文法15問＋読解3セットが付きます。") + "</p>")
    out += render_exam({"part6": w["part6"], "reading": w["reading"]})
    out.append('<div class="nav"><a href="exam-sprint.html">← ' + bi("冲刺计划", "対策プラン") + '</a><a href="index.html">' + bi("全部日期", "一覧へ") + " →</a></div>")
    out.append("</main>")
    out.append(footer(v))
    return "\n".join(out)


def sprint_banner(sp):
    left = _days_left(sp)
    if left < 0:
        return ""
    cd = bi(f"距考试还有 {left} 天", f"試験まであと {left} 日") if left else bi("今天考试，加油！", "今日が試験、がんばって！")
    return (f'<div class="ep xhome"><div class="num">🎯<small>{E(sp["exam_date"][5:].replace("-", "/"))}</small></div>'
            f'<div><h2><a href="exam-sprint.html">{bi("考前冲刺：语法真题 + 阅读训练", "試験直前対策：文法の本番問題 + 読解")}</a></h2>'
            f'<div class="meta"><span class="xcd" data-exam="{E(sp["exam_date"])}">{cd}</span> · {bi("Day 39–44 每天 15 道 Part 5 + 3 组 Part 7", "Day 39〜44 毎日 Part 5 15問 + Part 7 3セット")}</div>'
            f'<div class="xhl"><a class="btn sm" href="exam-sprint.html">{bi("📅 6 天计划", "📅 6日間プラン")}</a>'
            f'<a class="btn sm" href="exam-warmup.html">{bi("🌙 今晚热身", "🌙 今夜のウォームアップ")}</a></div></div></div>')


# ------------------------------------------------------------------ main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", nargs="?", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--force-audio", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    nums = all_days()
    if not nums:
        sys.exit("no data/dayN.json files")
    targets = nums if a.all or a.day is None else [a.day]
    days = {n: load_day(n) for n in nums}
    for n in nums:  # dates = real publish dates, never a fixed sequence
        pd = publish_date(n)
        if days[n].get("date") != pd:
            print(f"day{n}: date {days[n].get('date')} -> {pd}")
            days[n]["date"] = pd
            fp = DATA / f"day{n}.json"
            raw = json.loads(fp.read_text(encoding="utf-8"))
            raw["date"] = pd
            fp.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = False
    for n in targets:
        if n not in days:
            sys.exit(f"data/day{n}.json not found")
        errs, warns = validate(n, days[n])
        warns += ipa_crosscheck(days[n])
        for w in warns:
            print(f"  WARN day{n}: {w}")
        for e in errs:
            print(f"  ERROR day{n}: {e}")
        bad |= bool(errs)
        print(f"day{n}: {len(words_of(days[n]))} words, {len(errs)} errors, {len(warns)} warnings")
    if bad:
        sys.exit("validation failed")
    if a.check:
        return
    if not a.no_audio:
        for n in targets:
            make_audio(n, days[n], a.force_audio)
    import datetime as dt
    v = dt.datetime.now().strftime("%Y%m%d%H%M")
    ordered = [(n, days[n]) for n in nums]
    sp = load_sprint()
    for n in nums:  # re-render all days so prev/next links stay correct
        i = nums.index(n)
        prev_day = nums[i - 1] if i > 0 else None
        next_day = nums[i + 1] if i + 1 < len(nums) else None
        (ROOT / f"day{n}.html").write_text(render_day(n, merge_sprint(n, days[n], sp), prev_day, next_day, v), encoding="utf-8")
    (ROOT / "index.html").write_text(render_index(ordered, v, sp), encoding="utf-8")
    if sp:
        (ROOT / "exam-sprint.html").write_text(render_plan(sp, nums, v), encoding="utf-8")
        if sp.get("warmup"):
            (ROOT / "exam-warmup.html").write_text(render_warmup(sp, v), encoding="utf-8")
    manifest = [{"day": n, "date": d["date"], "title_zh": d["title_zh"], "title_ja": d["title_ja"],
                 "words": len(words_of(d)), "roots": [r["root"] for r in d.get("roots", [])]} for n, d in ordered]
    (DATA / "days.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    used = []
    for n, d in ordered:
        used += [w["w"] for w in words_of(d)]
    (ROOT / "used_words.txt").write_text("\n".join(used) + "\n", encoding="utf-8")
    # final checks
    problems = []
    for p in [ROOT / "index.html", *ROOT.glob("day*.html"), *ROOT.glob("exam-*.html"), *(ROOT / "assets").glob("*"), *DATA.glob("*.json"), ROOT / "used_words.txt"]:
        if p.is_file() and HANGUL.search(p.read_text(encoding="utf-8", errors="ignore")):
            problems.append(f"Hangul in {p.relative_to(ROOT)}")
    for n in nums:
        for src in re.findall(r'data-src="([^"]+)"', (ROOT / f"day{n}.html").read_text(encoding="utf-8")):
            if not (ROOT / src).exists():
                problems.append(f"missing audio {src}")
    for pr in problems[:20]:
        print("  ERROR", pr)
    if problems:
        sys.exit(f"{len(problems)} output problems")
    print(f"OK: rendered {len(nums)} day page(s) + index.html; used_words.txt = {len(used)} words")


if __name__ == "__main__":
    main()
