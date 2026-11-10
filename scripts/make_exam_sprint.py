#!/usr/bin/env python3
"""Generate data/exam_sprint.json: the 2026-11-17 TOEIC IP exam sprint (Days 39-44 + tonight's warm-up).

Sources (all local to the box, nothing invented):
  * stems / options / passages: /workspace/ets950/build/test{1,2,3}_site.json
  * answer keys + explanations cross-checked with the toeic800 podcast content
    (/workspace/toeic_podcast/epNN_content.py): Part 5 keys from ep51-ep57 (_KEY dicts, T3 via t3.ans),
    Part 6/7 keys from the sequential walkthroughs ep8-ep33. Any key mismatch aborts.
  * Test 2: test2_site.json Part 5-7 explanations are '生成解析' placeholders and its Part 7 passages /
    questions are abridged, so Test 2 explanations come from the episodes (ep51-57 for Part 5) and
    Test 2 Part 7 passages, questions, options and explanations come verbatim from the sequential
    episodes ep17-ep25 (their keys also equal test2_site.json).
build_day.py merges exam_sprint.json["days"][N] into dayN.html automatically.
"""
import json, os, re, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POD = '/workspace/toeic_podcast'
SITE = {t: json.load(open(f'/workspace/ets950/build/test{t}_site.json', encoding='utf-8'))['groups'] for t in (1, 2, 3)}

# ---------------------------------------------------------------- podcast content (verified keys)
sys.path.insert(0, POD)
_cwd = os.getcwd(); os.chdir(POD)
TR = {}
_h = types.ModuleType('ep_helpers')
def _T(z, j):
    TR[z] = j
    return z
_h.T = _T; _h.save_tr = lambda *a, **k: None; _h.words_order = lambda *a, **k: []; _h.TR = TR
sys.modules['ep_helpers'] = _h
import t3  # noqa: E402  (Test 3 answer key)

def _exec(ep):
    f = f'{POD}/ep{ep}_content.py'
    ns = {'__file__': f}
    try:
        exec(compile(open(f, encoding='utf-8').read(), f, 'exec'), ns)
    except Exception:  # trailing vocab asserts fail with the stubbed helpers; data is already defined
        pass
    return ns

P5SRC = {}   # (t, no) -> dict(ep, ans, tip_zh, tip_ja, exp_zh, exp_ja)
for ep in range(51, 58):
    ns = _exec(ep)
    key = ns.get('_KEY', {})
    for stem, opts, ans, note, exp, words, label in ns['P5']:
        m = re.match(r'Test (\d) · Q(\d+)', label)
        t, n = int(m.group(1)), int(m.group(2))
        ref = t3.ans(n) if t == 3 else key[(t, n)]
        assert ans == ref, (ep, t, n, ans, ref)
        P5SRC[(t, n)] = dict(ep=ep, ans=ans, tip_zh=note, tip_ja=TR[note], exp_zh=exp, exp_ja=TR[exp])

SEQ = {}     # (t, first, last) -> sequential-episode set
for ep in range(8, 34):
    ns = _exec(ep)
    for s in ns.get('P7', []) or []:
        m = re.search(r'Test (\d) Q(\d+)[–-](\d+)', s.get('title', ''))
        if m:
            SEQ.setdefault((int(m.group(1)), int(m.group(2)), int(m.group(3))), dict(s, ep=ep))
os.chdir(_cwd)

# ---------------------------------------------------------------- builders
TOPIC = {51: ('词性', '品詞'), 52: ('时态 · 语态', '時制 · 態'), 53: ('介词 vs 连词', '前置詞 vs 接続詞'),
         54: ('关系词 · 代词', '関係詞 · 代名詞'), 55: ('词汇', '語彙'), 56: ('词汇', '語彙'),
         57: ('综合：介词 · 副词 · 连接', '総まとめ：前置詞 · 副詞 · つなぎ')}
L = 'ABCD'

def p5(t, n):
    q = SITE[t][f'R{n}']['questions'][0]
    s = P5SRC[(t, n)]
    assert q['no'] == n and L[q['answer']] == s['ans'], (t, n)
    it = dict(id=f'T{t}-Q{n}', label=f'Test {t} · Q{n}', test=t, no=n, part=5, q=' '.join(q['q'].split()),
              options=list(q['options']), answer=s['ans'], topic_zh=TOPIC[s['ep']][0], topic_ja=TOPIC[s['ep']][1],
              tip_zh=s['tip_zh'], tip_ja=s['tip_ja'], src=f"ep{s['ep']}")
    if t == 2:  # site explanation is a generated placeholder -> episode walkthrough
        it.update(exp_zh=s['exp_zh'], exp_ja=s['exp_ja'])
    else:
        it.update(exp_zh=q['exp'], exp_ja=q['exp_ja'])
        if q.get('vocab'):
            it.update(vocab_zh=q['vocab'], vocab_ja=q.get('vocab_ja') or q['vocab'])
    return it

def site_set(t, a, b, part):
    g = SITE[t][f'R{a}']
    seq = SEQ[(t, a, b)]
    nos = [q['no'] for q in g['questions']]
    assert nos == list(range(a, b + 1)), (t, a, nos)
    qs = []
    for q, sq in zip(g['questions'], seq['qs']):
        k = L[q['answer']]
        ref = t3.ans(q['no']) if t == 3 else sq[2]
        assert k == ref == sq[2], (t, q['no'], k, ref, sq[2])
        qs.append(dict(no=q['no'], label=f"Test {t} · Q{q['no']}", q=' '.join(q['q'].split()) if q.get('q') else None,
                       options=list(q['options']), answer=k, exp_zh=q['exp'], exp_ja=q['exp_ja']))
    return dict(id=f'T{t}-Q{a}-{b}', label=f'Test {t} · Q{a}–{b}', test=t, part=part, intro=g['intro'],
                docs=g['docs'], questions=qs, src=f"site+ep{seq['ep']}")

def seq_set(t, a, b):
    """Test 2 Part 7: passage/questions/explanations verbatim from the sequential episode."""
    s = SEQ[(t, a, b)]
    g = SITE[t][f'R{a}']
    docs = s.get('docs') or [s['text']]
    qs = []
    for i, sq in enumerate(s['qs']):
        n = a + i
        site_k = L[g['questions'][i]['answer']]
        assert g['questions'][i]['no'] == n and site_k == sq[2], (t, n, site_k, sq[2])
        exp = next(x for x in sq[3:] if isinstance(x, str) and x in TR)
        qs.append(dict(no=n, label=f'Test {t} · Q{n}', q=sq[0], options=list(sq[1]), answer=sq[2],
                       exp_zh=exp, exp_ja=TR[exp]))
    assert a + len(qs) - 1 == b
    return dict(id=f'T{t}-Q{a}-{b}', label=f'Test {t} · Q{a}–{b}', test=t, part=7, intro=g['intro'],
                text_docs=[d.strip() for d in docs], questions=qs, src=f"ep{s['ep']}")

def rset(t, a, b):
    return seq_set(t, a, b) if t == 2 else site_set(t, a, b, 7)

def P(spec):
    out = []
    for t, nums in spec:
        out += [p5(t, n) for n in nums]
    return out

# ---------------------------------------------------------------- the 6-day plan
DAYS = {
 39: dict(date='2026-11-11', focus_zh='词性题（看空格位置判断词性）', focus_ja='品詞問題（空所の位置で品詞を判断）',
          grammar=P([(1, [104, 106, 108, 110, 115, 121, 123]), (2, [101, 107, 108, 124]), (3, [102, 104, 106, 108])]),
          reading=[(1, 196, 200), (3, 181, 185), (2, 151, 152)]),
 40: dict(date='2026-11-12', focus_zh='词性收尾 + 时态语态 + 介词/连词（开头）', focus_ja='品詞の残り + 時制・態 + 前置詞/接続詞（前半）',
          grammar=P([(2, [126]), (3, [110, 114, 122, 129]), (1, [112, 127]), (2, [106, 116, 122]), (3, [118, 126, 127]), (1, [102, 111])]),
          reading=[(3, 186, 190), (2, 176, 180), (2, 155, 157)]),
 41: dict(date='2026-11-13', focus_zh='介词 vs 连词 + 关系词 · 代词', focus_ja='前置詞 vs 接続詞 + 関係詞・代名詞',
          grammar=P([(1, [114, 124]), (2, [102, 110, 112, 114, 125, 130]), (3, [103, 113, 123]), (3, [124]), (1, [126, 101, 119])]),
          reading=[(3, 191, 195), (2, 164, 167), (2, 168, 171)]),
 42: dict(date='2026-11-14', focus_zh='代词收尾 + 词汇题（形容词 · 动词 · 名词）', focus_ja='代名詞の残り + 語彙問題（形容詞・動詞・名詞）',
          grammar=P([(2, [103, 120, 128]), (3, [112, 116]), (1, [109]), (2, [111, 123, 127]), (3, [107]), (1, [122]), (2, [109, 129]), (3, [111]), (2, [105])]),
          reading=[(3, 196, 200), (2, 181, 185), (2, 147, 148)]),
 43: dict(date='2026-11-15', focus_zh='词汇题（名词 · 副词 · 动词 · 形容词）', focus_ja='語彙問題（名詞・副詞・動詞・形容詞）',
          grammar=P([(1, [128]), (3, [128]), (1, [113]), (3, [121]), (1, [118, 120]), (2, [115, 121]), (1, [116]), (3, [115]), (1, [125, 129]), (2, [117, 118]), (3, [109])]),
          reading=[(2, 186, 190), (2, 191, 195), (2, 149, 150)]),
 44: dict(date='2026-11-16', focus_zh='Part 5 总收尾 + Test 1 Part 6 全部 16 题复习', focus_ja='Part 5 総仕上げ + Test 1 Part 6 全16問の復習',
          grammar=P([(1, [130]), (3, [117, 119]), (1, [103, 105, 107]), (2, [119]), (3, [101]), (2, [104]), (3, [105]), (3, [120, 130, 125]), (2, [113]), (1, [117])]),
          part6=[(1, 131, 134), (1, 135, 138), (1, 139, 142), (1, 143, 146)],
          reading=[(2, 196, 200), (2, 172, 175), (2, 161, 163)]),
}
WARMUP = dict(date='2026-11-10', part6=[(1, 131, 134), (1, 139, 142)], reading=[(1, 147, 148), (1, 181, 185)])

def build():
    out = {'exam_date': '2026-11-17', 'exam_zh': 'TOEIC IP Online（1 小时 · 90 题）', 'exam_ja': 'TOEIC IP Online（1時間・90問）',
           'days': {}, 'warmup': None}
    seen_g, seen_r = set(), set()
    for n, d in DAYS.items():
        g = d['grammar']
        assert len(g) == 15, (n, len(g))
        for it in g:
            assert it['id'] not in seen_g, it['id']; seen_g.add(it['id'])
        rs = [rset(*x) for x in d['reading']]
        for r in rs:
            assert r['id'] not in seen_r, r['id']; seen_r.add(r['id'])
        day = dict(date=d['date'], focus_zh=d['focus_zh'], focus_ja=d['focus_ja'], grammar=g, reading=rs)
        if d.get('part6'):
            day['part6'] = [site_set(*x, part=6) for x in d['part6']]
        out['days'][str(n)] = day
    assert len(seen_g) == 90, len(seen_g)
    w = dict(date=WARMUP['date'], part6=[site_set(*x, part=6) for x in WARMUP['part6']], reading=[rset(*x) for x in WARMUP['reading']])
    for r in w['reading']:
        assert r['id'] not in seen_r, r['id']
    out['warmup'] = w
    return out

if __name__ == '__main__':
    data = build()
    p = ROOT / 'data' / 'exam_sprint.json'
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for n, d in data['days'].items():
        rq = sum(len(r['questions']) for r in d['reading'])
        p6 = sum(len(s['questions']) for s in d.get('part6', []))
        print(f"Day {n}: grammar {len(d['grammar'])} + part6 {p6} · reading {[r['id'] for r in d['reading']]} = {rq} q")
    print('warmup:', [s['id'] for s in data['warmup']['part6']], [r['id'] for r in data['warmup']['reading']])
    print('wrote', p)
