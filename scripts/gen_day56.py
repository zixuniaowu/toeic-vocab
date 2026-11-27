#!/usr/bin/env python3
import json
L=[l for l in open('scripts/day56_words.txt',encoding='utf-8').read().split('\n') if l.strip()]
groups={};order=[];cur=None
for l in L:
    if l.startswith('## '): cur=l[3:]; groups[cur]=[]; order.append(cur); continue
    f=l.split('|'); assert len(f)==12,f[0]
    w,pos,ipa,zh,ja,ex,exz,exj,parts,nz,nj,forms=f
    d=dict(w=w,pos=pos,ipa=ipa,zh=zh,ja=ja,ex=ex,ex_zh=exz,ex_ja=exj,
      parts=[x.split(':') for x in parts.split(';')] if parts else [],
      forms=[x.split('=') for x in forms.split(';')])
    if nz: d['note']=dict(zh=nz,ja=nj)
    groups[cur].append(d)
T={'part':('词根 -part-：部分','語根 -part-：部分'),'opt':('词根 -opt-：选择','語根 -opt-：選ぶ'),'propri':('词根 -propri-：自己的','語根 -propri-：自分の'),'clar':('词根 -clar-：清楚','語根 -clar-：明るい・明確'),'prop':('主题：提案、投标与合同条款','テーマ：提案・入札・契約条項'),'media':('主题：数字媒体与办公网络','テーマ：デジタルメディアとオフィスネットワーク')}
G=[dict(id=k,title_zh=T[k][0],title_ja=T[k][1],words=groups[k]) for k in order]
ws=lambda k:[w['w'] for w in groups[k]]
R=lambda root,o,zh,ja,ez,ej,ex: dict(root=root,origin=o,zh=zh,ja=ja,exp_zh=ez,exp_ja=ej,examples=ex)
roots=[
R('-part-','Latin pars, partis','部分；份额','部分；分け前','来自拉丁语 pars（部分）。一部分 → partial；分到一份的人 → partner；分出来的块 → department；离开 → depart；拿一份 → participation。','ラテン語 pars（部分）から。一部 → partial；分け前を持つ人 → partner；分けた区分 → department；離れる → depart；分け前を取る → participation。',ws('part')),
R('-opt-','Latin optare','选择','選ぶ','来自拉丁语 optare（选择）。选项 → option；选来用 → adopt；选择退出 → opt out。⚠️ optimal / optimism 来自 optimus（最好的），不是此词根。','ラテン語 optare（選ぶ）から。選択肢 → option；選び取る → adopt；脱退する → opt out。optimal / optimism は optimus（最良の）由来で別源。',['option','optional','optionally','opt','adopt','adoption','adopter']),
R('-propri-','Latin proprius','自己的；本分','自分の；本来の','来自拉丁语 proprius（自己的）。据为己有 / 划拨 → appropriation；合乎本分 → appropriate；得体 → propriety；所有人 → proprietorship。','ラテン語 proprius（自分の）から。自分のものにする・充当 → appropriation；本来にふさわしい → appropriate；礼儀 → propriety；所有者 → proprietorship。',ws('propri')),
R('-clar-','Latin clarus','明亮；清楚','明るい；明確','来自拉丁语 clarus（明亮、清楚）。清晰度 → clarity；使清楚 → clarify / clarification；clear 也经古法语来自 clarus。','ラテン語 clarus（明るい・明確）から。明確さ → clarity；はっきりさせる → clarify / clarification；clear も古フランス語経由で clarus 由来。',ws('clar'))]
d=dict(day=56,date='2026-11-28',title_zh='四大词根 + 提案投标与合同条款 + 数字媒体与办公网络',title_ja='4つの語根＋提案・入札・契約条項＋デジタルメディアとオフィスネットワーク',
 intro_zh='今天的词根是 -part-（部分）、-opt-（选择）、-propri-（自己的）、-clar-（清楚）；主题是提案、投标与合同条款，以及数字媒体与办公网络。',
 intro_ja='今日の語根は -part-（部分）、-opt-（選ぶ）、-propri-（自分の）、-clar-（明確）。テーマは提案・入札・契約条項、デジタルメディアとオフィスネットワーク。',
 voice='en-US-AriaNeural',roots=roots,groups=G)
print(sum(len(g['words']) for g in G))
json.dump(d,open('data/day56.json','w'),ensure_ascii=False,indent=1)
