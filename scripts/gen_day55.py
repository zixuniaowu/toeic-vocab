#!/usr/bin/env python3
import json,re
L=[l for l in open('scripts/day55_words.txt',encoding='utf-8').read().split('\n') if l.strip()]
groups={};order=[]
cur=None
for l in L:
    if l.startswith('## '): cur=l[3:]; groups[cur]=[]; order.append(cur); continue
    f=l.split('|'); assert len(f)==12,f[0]
    w,pos,ipa,zh,ja,ex,exz,exj,parts,nz,nj,forms=f
    d=dict(w=w,pos=pos,ipa=ipa,zh=zh,ja=ja,ex=ex,ex_zh=exz,ex_ja=exj,
      parts=[x.split(':') for x in parts.split(';')] if parts else [],
      note=dict(zh=nz,ja=nj),forms=[x.split('=') for x in forms.split(';')])
    if w=='stagnate': d['note']=dict(zh=nz,ja=nj)
    groups[cur].append(d)
T={'sta':('词根 -sist- / -sta-：站立','語根 -sist- / -sta-：立つ'),'stru':('词根 -stru- / -struct-：建造','語根 -stru- / -struct-：建てる'),'mov':('词根 -mov- / -mot-：移动','語根 -mov- / -mot-：動く'),'cur':('词根 -cur-：关心；照料','語根 -cur-：気にかける・世話'),'plan':('主题：规划、财务与产能','テーマ：計画・財務・生産能力'),'fac':('主題：工程与设施','テーマ：エンジニアリングと施設')}
G=[dict(id=k,title_zh=T[k][0],title_ja=T[k][1],words=groups[k]) for k in order]
ws=lambda k:[w['w'] for w in groups[k]]
R=lambda root,o,zh,ja,ez,ej,ex: dict(root=root,origin=o,zh=zh,ja=ja,exp_zh=ez,exp_ja=ej,examples=ex)
roots=[R('-sist- / -sta-','Latin sistere / stare','站立','立つ','来自拉丁语 sistere / stare（站立）。一直站着 → persist；站出来对抗 → resist；站到旁边帮忙 → assist；稳固 → stable；建立 → establish；不变 → constant。⚠️ stagnate 来自 stagnum（池塘），不是此词根。','ラテン語 sistere / stare（立つ）から。最後まで立つ → persist；逆らう → resist；そばで助ける → assist；安定 → stable；設立 → establish；一定 → constant。stagnate は stagnum（池）由来で別源。',ws('sta')[:6]+['constant','instant']),
R('-struct- / -stru-','Latin struere','堆建；建造','積み上げる；建てる','来自拉丁语 struere（堆起、建造）。建设 → construction；阻塞 → obstruction；破坏 → destructive；上 / 下部结构 → superstructure / substructure。','ラテン語 struere（積む・建てる）から。建設 → construction；妨害 → obstruction；破壊的 → destructive；上部・下部構造 → superstructure / substructure。',ws('stru')),
R('-mov- / -mot-','Latin movere','移动','動かす','来自拉丁语 movere（移动）。移走 → remove；晋升 → promotion；骚动 → commotion；动力 → motivation。','ラテン語 movere（動かす）から。取り除く → remove；昇進 → promotion；騒ぎ → commotion；動機づけ → motivation。',ws('mov')),
R('-cur-','Latin cura','关心；照料','気にかける；世話','来自拉丁语 cura（关心、照料）。好奇 → curious；用心做 → accurate；无忧 → secure；张罗采购 → procure；治疗 → cure。','ラテン語 cura（気づかい・世話）から。好奇心 → curious；正確 → accurate；安心 → secure；調達 → procure；治療 → cure。',ws('cur'))]
d=dict(day=55,date='2026-11-27',title_zh='四大词根 + 规划财务与产能 + 工程与设施',title_ja='4つの語根＋計画・財務・生産能力＋エンジニアリングと施設',
 intro_zh='今天的词根是 -sist- / -sta-（站立）、-struct-（建造）、-mov- / -mot-（移动）、-cur-（关心；照料）；主题是规划、财务与产能，以及工程与设施。',
 intro_ja='今日の語根は -sist- / -sta-（立つ）、-struct-（建てる）、-mov- / -mot-（動かす）、-cur-（気にかける）。テーマは計画・財務・生産能力、エンジニアリングと施設。',
 voice='en-US-AriaNeural',roots=roots,groups=G)
print(sum(len(g['words']) for g in G))
json.dump(d,open('data/day55.json','w'),ensure_ascii=False,indent=1)
