#!/usr/bin/env python3
import json, sys
sys.path.insert(0, 'scripts')
import make_exam_sprint as m
p = m.ROOT / 'data' / 'exam_sprint.json'
d = json.load(open(p, encoding='utf-8'))
used = {r['id'] for v in d['days'].values() for r in v.get('reading', []) + v.get('part6', [])}
rd = [m.rset(1, 191, 195), m.rset(1, 149, 150)]
for r in rd:
    assert r['id'] not in used, r['id']
g = m.P([(1, [117, 118, 119, 120, 122, 125]), (2, [111, 113])])
d['days']['52'] = dict(date='2026-11-24', focus_zh='考后轻复习：Part 5 复习 8 题 + Part 7 两篇（Test 1）',
                       focus_ja='試験後の軽い復習：Part 5 復習8問＋Part 7 の2題（Test 1）',
                       grammar=g, reading=rd)
p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print([x['id'] for x in g], [x['id'] for x in rd])
