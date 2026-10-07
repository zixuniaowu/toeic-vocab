#!/usr/bin/env python3
"""Check the deployed site: HTTP 200 for index/dayN pages, every 🔊 MP3 reachable, no Hangul.

Usage: python3 scripts/verify_live.py [N ...]   (default: every day in data/)
       BASE=https://zixuniaowu.github.io/toeic-vocab/ python3 scripts/verify_live.py 3
"""
import os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = os.environ.get("BASE", "https://zixuniaowu.github.io/toeic-vocab/").rstrip("/") + "/"
HANGUL = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uAC00-\uD7AF\uD7B0-\uD7FF]")
ROOT = Path(__file__).resolve().parent.parent


def get(url, head=False):
    req = urllib.request.Request(url, method="HEAD" if head else "GET", headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, (b"" if head else r.read())


def main():
    days = [int(a) for a in sys.argv[1:]] or sorted(int(p.stem[3:]) for p in (ROOT / "data").glob("day*.json") if p.stem[3:].isdigit())
    bad = 0
    for page in ["index.html"] + [f"day{n}.html" for n in days]:
        st, body = get(BASE + page)
        text = body.decode("utf-8")
        hg = HANGUL.search(text)
        print(f"{st} {BASE + page}  {len(body)} bytes  hangul={'YES' if hg else 'no'}")
        bad += (st != 200) + bool(hg)
        if page.startswith("day"):
            srcs = sorted(set(re.findall(r'data-src="([^"]+)"', text)))
            with ThreadPoolExecutor(12) as ex:
                res = list(ex.map(lambda s: (s, get(BASE + s, head=True)[0]), srcs))
            miss = [s for s, c in res if c != 200]
            print(f"    audio: {len(srcs) - len(miss)}/{len(srcs)} files return 200" + (f"  MISSING: {miss[:5]}" if miss else ""))
            bad += len(miss)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
