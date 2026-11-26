#!/usr/bin/env python3
import json, sys
sys.path.insert(0, 'scripts')
import make_exam_sprint as m
p = m.ROOT / 'data' / 'exam_sprint.json'
d = json.load(open(p, encoding='utf-8'))
used = {r['id'] for v in d['days'].values() for r in v.get('reading', []) + v.get('part6', [])}
rd = [m.rset(3, 147, 149), m.rset(3, 150, 151)]
for r in rd:
    assert r['id'] not in used, r['id']
prev = {x['id'] for k in range(45, 55) for x in d['days'].get(str(k), {}).get('grammar', [])}
cand = [(t, n) for (t, n) in sorted(m.P5SRC) if f'T{t}-Q{n}' not in prev]
print(len(cand), cand[:20])
sel = cand[:8]
g = m.P([(t, [n]) for t, n in sel])
d['days']['55'] = dict(date='2026-11-27', focus_zh='考后轻复习：Part 5 复习 8 题 + Part 7 两篇（Test 3）',
                       focus_ja='試験後の軽い復習：Part 5 復習8問＋Part 7 の2題（Test 3）',
                       grammar=g, reading=rd)
p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print([x['id'] for x in g], [x['id'] for x in rd])
