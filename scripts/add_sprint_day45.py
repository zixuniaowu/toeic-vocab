#!/usr/bin/env python3
"""Add Day 45 (exam day 2026-11-17) to data/exam_sprint.json from unused, key-verified sets (reuses make_exam_sprint builders)."""
import json, sys
sys.path.insert(0, 'scripts')
import make_exam_sprint as m
p = m.ROOT / 'data' / 'exam_sprint.json'
d = json.load(open(p, encoding='utf-8'))
used = {r['id'] for v in d['days'].values() for r in v.get('reading', []) + v.get('part6', [])}
p6 = [m.site_set(3, 131, 134, part=6), m.site_set(3, 135, 138, part=6)]
rd = [m.rset(3, 161, 163), m.rset(3, 164, 167)]
for r in p6 + rd:
    assert r['id'] not in used, r['id']
d['days']['45'] = dict(date='2026-11-17', focus_zh='考试当天：Test 3 Part 6 两篇（8 题）+ Part 7 两篇快速复习',
                       focus_ja='試験当日：Test 3 Part 6 の2題（8問）＋ Part 7 の2題を最終確認',
                       grammar=[], part6=p6, reading=rd)
p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print([x['id'] for x in p6], [x['id'] for x in rd])
