#!/usr/bin/env python3
"""Build a Chinese explanation MP4 for one toeic-vocab day.

Usage:
  /tmp/wp/bin/python scripts/make_day_video.py 7
  /tmp/wp/bin/python scripts/make_day_video.py --all

Outputs videos/dayN.mp4 (not committed to Pages; upload to GitHub Release).
"""
from __future__ import annotations
import asyncio, hashlib, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUDIO = ROOT / "audio"
OUT = ROOT / "videos"
TMP_ROOT = Path("/tmp/tv_video")
SEG = Path("/tmp/tv_tts_cache"); SEG.mkdir(parents=True, exist_ok=True)

HOST = "zh-CN-XiaoxiaoNeural"
EN = "en-US-AriaNeural"
HANGUL = re.compile(r"[\uAC00-\uD7AF]")

sys.path.insert(0, "/workspace/toeic_podcast")
from PIL import Image, ImageDraw, ImageFont  # noqa
import cards as cards_mod  # noqa

cards_mod.LANG = "zh"
W, H = cards_mod.W, cards_mod.H
F = cards_mod.F
WHITE, DIM, ACC, BOXBG = cards_mod.WHITE, cards_mod.DIM, cards_mod.ACC, cards_mod.BOXBG
para = cards_mod.para
fit_one = cards_mod.fit_one
rbox = cards_mod.rbox
base = cards_mod.base

def slug(w: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", w.lower()).strip("-")

def spell_letters(w: str) -> str:
    return ". ".join(ch.upper() for ch in w if ch.isalpha()) + "."

def spell_display(w: str) -> str:
    return " - ".join(ch.upper() for ch in w if ch.isalpha())

def dur(p: str | Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]
    ).decode())

def tts(text: str, voice: str = HOST) -> Path:
    text = text.strip()
    if not text:
        p = SEG / "silence_placeholder.mp3"
        if not p.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                            "-t", "0.3", "-q:a", "9", str(p)], check=True)
        return p
    h = hashlib.md5(f"{voice}|{text}".encode()).hexdigest()
    p = SEG / f"{h}.mp3"
    if p.exists() and p.stat().st_size > 500:
        return p
    async def _go():
        import edge_tts
        for _ in range(4):
            try:
                await asyncio.wait_for(edge_tts.Communicate(text, voice, rate="+10%").save(str(p)), timeout=40)
                if p.stat().st_size > 500:
                    return
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt): raise
                await asyncio.sleep(2)
        raise RuntimeError(f"tts failed: {text[:40]}")
    asyncio.run(_go())
    return p

def silence(sec: float) -> Path:
    p = SEG / f"sil_{sec:.2f}.mp3"
    if not p.exists() or p.stat().st_size < 100:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                        "-t", str(sec), "-q:a", "9", str(p)], check=True)
    return p

def concat_mp3(files: list[Path], out: Path):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "96k", str(out)], check=True)
    lst.unlink(missing_ok=True)

def save_card(img: Image.Image, path: Path):
    img.save(path, "PNG", optimize=True)

def card_cover(day: dict, path: Path):
    img, d = base(left=f"Day {day['day']}", right="TOEIC 800 · 词根词汇")
    para(d, 60, 180, f"Day {day['day']}", True, 72, ACC, W - 120, center=True)
    para(d, 80, 280, day["title_zh"], True, 40, WHITE, W - 160, center=True)
    para(d, 80, 400, " · ".join(r["root"] for r in day["roots"]), False, 28, DIM, W - 160, center=True)
    para(d, 80, 520, "中文讲解 · 词根 · 拼写 · 例句", False, 28, ACC, W - 160, center=True)
    save_card(img, path)

def card_root(r: dict, idx: int, path: Path):
    r = dict(r, exp_zh=r["exp_zh"].replace("⚠️", "注意：").replace("⚠", "注意："))
    img, d = base(left=f"词根 {idx}/4", right=r["root"])
    para(d, 60, 90, r["root"], True, 56, ACC, W - 120, center=True)
    para(d, 80, 180, f"{r['zh']}  /  {r['ja']}", True, 36, WHITE, W - 160, center=True)
    para(d, 80, 250, r.get("origin", ""), False, 24, DIM, W - 160, center=True)
    y = para(d, 70, 320, r["exp_zh"], False, 28, WHITE, W - 140)
    examples = "、".join(r.get("examples", [])[:6])
    if examples:
        para(d, 70, min(y + 20, 620), "例词：" + examples, False, 24, ACC, W - 140)
    save_card(img, path)

def card_group(title: str, path: Path):
    img, d = base(left="分组", right="")
    para(d, 60, 280, title, True, 48, WHITE, W - 120, center=True)
    save_card(img, path)

def card_word(w: dict, n: int, total: int, path: Path):
    img, d = base(left=f"{n}/{total}", right=w.get("pos", ""))
    ft = fit_one(d, w["w"], True, 120, 1180)
    tw = d.textlength(w["w"], font=ft)
    d.text(((W - tw) / 2, 70), w["w"], font=ft, fill=WHITE)
    ipf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    d.text(((W - d.textlength(w["ipa"], font=ipf)) / 2, 222), w["ipa"], font=ipf, fill=DIM)
    sp = spell_display(w["w"])
    ft2 = fit_one(d, sp, True, 40, 1200)
    d.text(((W - d.textlength(sp, font=ft2)) / 2, 272), sp, font=ft2, fill=ACC)
    para(d, 60, 335, f"{w['zh']}　｜　{w['ja']}", True, 34, WHITE, W - 120, center=True)
    d.line([(120, 410), (W - 120, 410)], fill=(120, 150, 190), width=2)
    y = para(d, 80, 430, w["ex"], False, 28, (215, 228, 245), 1120, center=True)
    para(d, 80, y + 6, w["ex_zh"], False, 24, DIM, 1120, center=True)
    save_card(img, path)

def card_review(day: dict, path: Path):
    img, d = base(left="复习", right=f"Day {day['day']}")
    para(d, 60, 100, "今日复习", True, 52, ACC, W - 120, center=True)
    y = 200
    for r in day["roots"]:
        y = para(d, 80, y, f"{r['root']}　{r['zh']}", True, 32, WHITE, W - 160) + 8
    y += 20
    for g in day["groups"]:
        if g["id"] in {r["root"].split("/")[0].strip("- ").split()[0] for r in day["roots"]}:
            continue
        # theme groups: those after the 4 root groups
    themes = [g for g in day["groups"][4:]]
    for g in themes:
        y = para(d, 80, y, g["title_zh"], False, 28, ACC, W - 160) + 6
    para(d, 80, 620, f"共 {sum(len(g['words']) for g in day['groups'])} 词 · 记得做小测验", False, 26, DIM, W - 160, center=True)
    save_card(img, path)

def build_day(n: int, crf: int = 30):
    day = json.loads((DATA / f"day{n}.json").read_text(encoding="utf-8"))
    raw = json.dumps(day, ensure_ascii=False)
    assert not HANGUL.search(raw), f"Hangul in day{n}"
    words = [w for g in day["groups"] for w in g["words"]]
    total = len(words)
    tmp = TMP_ROOT / f"day{n}"
    cards_dir = tmp / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    items = []  # {png, audio_files}
    # cover
    cover = cards_dir / "cover.png"
    card_cover(day, cover)
    intro = tts(f"大家好。今天是第 {n} 天，{day['title_zh']}。我们先讲四个词根，再按分组学习全部 {total} 个单词，最后快速复习。")
    items.append((cover, [intro, silence(0.4)]))

    # roots
    for i, r in enumerate(day["roots"], 1):
        png = cards_dir / f"root{i}.png"
        card_root(r, i, png)
        exp = r["exp_zh"].replace("⚠️", "注意，").replace("⚠", "注意，")
        txt = f"词根 {i}，{r['root']}，意思是{r['zh']}。{exp}"
        # keep root narration shorter if very long
        if len(txt) > 220:
            txt = f"词根 {i}，{r['root']}，意思是{r['zh']}。" + exp[:160] + "。"
        items.append((png, [tts(txt), silence(0.35)]))

    # groups + words
    wi = 0
    for g in day["groups"]:
        gpng = cards_dir / f"g_{g['id']}.png"
        card_group(g["title_zh"], gpng)
        items.append((gpng, [tts(f"接下来是：{g['title_zh']}。"), silence(0.25)]))
        for w in g["words"]:
            wi += 1
            wpng = cards_dir / f"w_{slug(w['w'])}.png"
            card_word(w, wi, total, wpng)
            site_w = AUDIO / f"day{n}" / f"{slug(w['w'])}.mp3"
            site_ex = AUDIO / f"day{n}" / f"{slug(w['w'])}_ex.mp3"
            assert site_w.exists() and site_ex.exists(), site_w
            zh_mean = w["zh"].split("；")[0]
            narr = tts(f"第 {wi} 个词，{w['w']}，{zh_mean}。")
            spell = tts(spell_letters(w["w"]), EN)
            tip_files = []
            if w.get("tip") and w["tip"].get("zh"):
                tip = w["tip"]["zh"]
                if len(tip) > 80:
                    tip = tip[:80]
                tip_files = [silence(0.15), tts("提示：" + tip)]
            files = [narr, silence(0.15), site_w, silence(0.2), spell, silence(0.2), site_w,
                     silence(0.25), tts("例句。"), silence(0.1), site_ex, silence(0.15), tts(w["ex_zh"])]
            files += tip_files + [silence(0.25)]
            items.append((wpng, files))

    # review
    rev = cards_dir / "review.png"
    card_review(day, rev)
    roots_line = "，".join(f"{r['root']}表示{r['zh']}" for r in day["roots"])
    items.append((rev, [tts(f"今天复习一下。四个词根：{roots_line}。共 {total} 个词，记得回网站做自测和小测验。明天见！"), silence(0.5)]))

    # build per-chunk wav/mp3 + timeline
    timeline = []
    chunk_mp3s = []
    t0 = 0.0
    for i, (png, files) in enumerate(items):
        chunk = tmp / f"c{i:04d}.mp3"
        concat_mp3(files, chunk)
        d = dur(chunk)
        timeline.append({"png": str(png), "start": t0, "dur": d})
        chunk_mp3s.append(chunk)
        t0 += d
        if i % 20 == 0:
            print(f"  day{n} audio chunks {i}/{len(items)}", flush=True)

    full_mp3 = tmp / "full.mp3"
    concat_mp3(chunk_mp3s, full_mp3)
    print(f"  day{n} audio {dur(full_mp3):.1f}s", flush=True)

    # ffmpeg stillimage video
    vtxt = tmp / "video.txt"
    lines = []
    for it in timeline:
        lines.append(f"file '{Path(it['png']).resolve()}'")
        lines.append(f"duration {it['dur']:.4f}")
    lines.append(f"file '{Path(timeline[-1]['png']).resolve()}'")
    vtxt.write_text("\n".join(lines) + "\n")
    out_mp4 = OUT / f"day{n}.mp4"
    D = f"{dur(full_mp3):.3f}"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(vtxt),
        "-i", str(full_mp3),
        "-map", "0:v", "-map", "1:a",
        "-vf", "fps=15,format=yuv420p", "-r", "15", "-fps_mode", "cfr",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "veryfast", "-tune", "stillimage",
        "-crf", str(crf), "-g", "150",
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2",
        "-t", D, "-movflags", "+faststart", str(out_mp4)
    ], check=True)
    print(f"OK day{n}: {out_mp4} {out_mp4.stat().st_size/1e6:.1f}MB {dur(out_mp4):.1f}s", flush=True)
    return out_mp4

def main():
    args = sys.argv[1:]
    crf = 30
    if "--crf" in args:
        i = args.index("--crf"); crf = int(args[i+1]); del args[i:i+2]
    if args == ["--all"] or not args:
        nums = sorted(int(p.stem[3:]) for p in DATA.glob("day*.json") if p.stem[3:].isdigit())
    else:
        nums = [int(a) for a in args]
    for n in nums:
        print(f"===== Day {n} =====", flush=True)
        build_day(n, crf=crf)

if __name__ == "__main__":
    main()
