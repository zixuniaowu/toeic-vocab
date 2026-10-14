# TOEIC 800 · 毎日背单词

在线地址：**https://zixuniaowu.github.io/toeic-vocab/**

每天 60 个 TOEIC 600–850 分段高频词，按**词根**和**主题**分组。每个词都有：词性 + 美式 IPA、逐字母拼写（S-C-H-E-D-U-L-E）、🔊 单词发音和 🔊 例句发音、中文 / 日文释义、TOEIC 风格例句（中日翻译）、词根拆解（前缀 / 词根 / 后缀，中日释义）、2–3 个相关形式 / 搭配，以及可选的 TOEIC 提示。
页首有“今日词根”专栏。学习功能：遮住释义自测（点卡片显示）、✓ 已掌握（localStorage）、只看未掌握、▶ 全部播放（单词 → 例句 → 下一个）、10 题小测验。界面中文为主，可切换日本語（记在 localStorage `tv.lang`）。

纯静态网站（HTML / CSS / 原生 JS），GitHub Pages 从 `main` 分支根目录发布。外观沿用 [toeic800](https://github.com/zixuniaowu/toeic800) 的单词表样式和 visitor-badge 访问计数（page_id `toeic-vocab`）。

## 目录

```
index.html, dayN.html        # 生成的页面（不要手改，改 JSON 后重新生成）
assets/style.css, app.js     # 样式、学习功能（发音、全部播放、自测、已掌握、小测验、语言切换）
data/dayN.json               # 每天的单词数据（唯一需要手写的文件）
data/days.json               # 生成的日期清单
audio/dayN/<slug>.mp3        # 单词发音；<slug>_ex.mp3 = 例句发音
used_words.txt               # 本站已用过的所有单词（生成）
scripts/build_day.py         # 校验 + 生成音频 + 生成页面
scripts/verify_live.py       # 发布后检查线上页面 / 音频
scripts/make_day_video.py    # 生成中文讲解 MP4（输出 videos/，上传 Release）
NEXT_DAY.txt                 # 每日例行下一课编号（避免与批量发布撞车）
videos/dayN.mp4              # 本地讲解视频（gitignore，上传到 Release media-v1）
scripts/day_template.json    # 新一天 JSON 的模板
```

## 发音是怎么做的

和 toeic800 一样：**预先生成的 MP3**，用 edge-tts（Microsoft Edge 在线 TTS）`en-US-AriaNeural` 女声（24 kHz、48 kbps 单声道）。页面用一个共享的 `Audio` 元素在点击事件里播放（iOS Safari 可用）；“全部播放”在 `ended` 后依次播放下一个文件。不依赖 Web Speech API。只生成缺少的文件；`--force-audio` 全部重新生成。


## 讲解视频（每日）

每天有一条**中文讲解 MP4**（词根讲解 → 逐词卡片 + 字母拼写朗读 → 快速复习）。视频**不放进 GitHub Pages**（避免仓库过大），而是上传到 Release `media-v1`：

- 播放地址：`https://github.com/zixuniaowu/toeic-vocab/releases/download/media-v1/dayN.mp4`
- 每天页面里的 `<video>` 和“下载本课视频”链接都指向上述 URL。

生成（在仓库根目录）：

```bash
/tmp/wp/bin/python scripts/make_day_video.py N          # 单天
/tmp/wp/bin/python scripts/make_day_video.py --all      # 全部已有 dayN.json
```

输出到 `videos/dayN.mp4`（已在 `.gitignore`）。上传 / 更新 Release：

```bash
gh release upload media-v1 videos/dayN.mp4 --clobber -R zixuniaowu/toeic-vocab
# 若 Release 尚不存在：
# gh release create media-v1 videos/day*.mp4 -t "Explanation videos" -n "Chinese explanation MP4s for each vocab day" -R zixuniaowu/toeic-vocab
```

每日 6:15 例行应：写 `data/dayN.json` → `build_day.py N` → `make_day_video.py N` → commit/push Pages → `gh release upload media-v1 videos/dayN.mp4 --clobber` → `verify_live.py N`。下一课编号写在仓库根目录 `NEXT_DAY.txt`（当前应为已发布最大 Day + 1）。

## 新增一天（例如 Day 2）

环境（一次性）：
```bash
python3 -m venv /tmp/wp && /tmp/wp/bin/pip install edge-tts cmudict   # cmudict 只用于 IPA 交叉检查（可选）
```

1. **选词**：60 个 TOEIC 600–850 高频词，按 3–4 个词根 + 1–2 个主题分组。
   - 不能和 `used_words.txt`（本站已用）重复——脚本会报错。
   - 尽量避开播客已讲过的词 `/workspace/toeic_podcast/used_words.txt`——脚本会给出警告（允许，但优先新词）。
2. **写数据**：复制 `scripts/day_template.json` 为 `data/day2.json`，`"day": 2`、`"date": "YYYY-MM-DD"`。每个词：
   | 字段 | 说明 |
   |---|---|
   | `w`, `pos`, `ipa` | 单词、词性（`v.` `n.` `adj.` `adv.` `n./v.`）、美式 IPA（`/.../`，与 toeic800 同一套符号：ɝ ɚ ɑ ɔ oʊ eɪ） |
   | `zh`, `ja` | 中文 / 日文释义，多个义项用 `；` 分隔（小测验取前两个） |
   | `ex`, `ex_zh`, `ex_ja` | TOEIC 风格英文例句及中日翻译；例句中第一个与单词同词干的词会自动加粗（不匹配时加 `"hl": "实际形式"`） |
   | `parts` | 词根拆解 `[["re-","再","再び"],["port","搬运","運ぶ"],["-er","表示人","〜する人"]]`；以 `-` 结尾 = 前缀，以 `-` 开头 = 后缀，其余 = 词根 |
   | `note` | `{"zh","ja"}` 词源说明。**没有可靠词根时 `parts` 留空 `[]`，`note` 必须说明“没有可靠的词根拆分”**（脚本会检查）。不要编造词源。 |
   | `forms` | 2–3 个相关形式 / 搭配 `[["reimbursement (n.)","报销","払い戻し"], ...]` |
   | `tip` | 可选 `{"zh","ja"}` TOEIC 提示 / 常见陷阱 |
   | `say` | 可选：TTS 朗读文本（默认 = `w`） |
   - `roots`：今日词根 3–4 个，`examples` 写当天的单词（会自动链接到卡片）。
   - **不能出现韩文**（脚本用 Hangul 正则检查 JSON 和所有输出）。
3. **生成**：
   ```bash
   /tmp/wp/bin/python scripts/build_day.py 2            # 校验 → 生成 120 个 MP3 → day2.html + index.html + days.json + used_words.txt
   /tmp/wp/bin/python scripts/build_day.py 2 --check    # 只校验
   ```
   会重新渲染所有 dayN.html（更新上一天 / 下一天链接）。看到 `OK: rendered ...` 才算成功；`WARN` 需要人工看一下（IPA 与 CMUdict 不一致、与播客重复等）。
4. **发布**：
   ```bash
   git add -A && git commit -m "day 2: <主题>" && git push
   ```
   Pages 约 1 分钟后更新，然后：
   ```bash
   python3 scripts/verify_live.py 2     # index/day2 返回 200、120 个 MP3 都是 200、无韩文
   ```

## 内容规范

- 水平：TOEIC 550–650 → 目标 800（IP テスト）。词汇选 600–850 分段的高频词。
- 例句自然、贴近 TOEIC（邮件、通知、会议、合同、出差等场景），中文为简体，日文为自然的日语。
- 词源必须可靠：拿不准就写“没有可靠的词根拆分 / 本族词”，并在 `exp_zh` 里提示形近但不同源的陷阱（例：attain ≠ tain，tentative ≠ ten，opportunity ≠ port“搬运”）。
