# chatkb-relationship-corpus

> **仓库名（GitHub repository name）**：`chatkb-relationship-corpus`
>
> **仓库描述（About / description）**：
> 中文：`本地纯文本语料库：成人（18+）亲密关系沟通、情绪回应、边界设定与反诈识别。可导出为 AI 知识库投喂材料。私有仓库，专有许可，禁止抓取、搬运与训练。`
> English: `Local plain-text corpus on adult (18+) romantic communication, emotional responsiveness, boundaries and scam-safety. Exportable as AI knowledge-base feed. Private, proprietary license — no scraping, no redistribution, no training.`
>
> 备选名：`lianai-chat-kb`、`relationship-chat-corpus`（若名字被占用）。

---

## 1. 这是什么

一个**纯文本**语料库，主题是「成年人之间的沟通与亲密关系」，供本人本地学习与后期投喂 AI 知识库使用。它由四部分组成：

1. **原创中文实战笔记**（`03_notes/`）——自己写的、可直接照着用的聊天/边界/反诈手册。
2. **证据层**：开放获取（Open Access）的英文学术论文全文（`01_raw/europepmc_xml/`、`02_text/europepmc/`），全部来自 CC / CC0 / 公有领域许可。
3. **中文公开材料**：官方公开文件全文（法律、政策、公告）、中文维基百科条目（CC BY-SA）、媒体文章的**短摘录**（版权仍属原权利人）、开源 Skill 仓库（按各自许可，且已按第 3 节规则剔除操控话术文件）。
4. **工具与清单**（`tools/`、`05_manifest/`）——抓取脚本、元数据、去重与分块脚本、许可与来源报告。

主题轴上除了聊天技巧、情绪与依恋、金钱边界、反操控之外，还各有一条完整链路覆盖**性沟通与同意**和**星座/生肖/玄学**：英文学术研究 facet + 中文百科条目 + 官方文件与媒体揭批 + 原创笔记（`03_notes/10_性沟通与同意.md`、`03_notes/11_星座生肖与玄学话题.md`）。两条都遵守同一底线：只谈成年人的沟通、健康与自保，不写露骨内容，不教用星座给人分类。

**不是什么**：不是 PUA 教材，不是话术包，不是「怎么让人给你花钱」的教程，不是心理治疗或法律建议，也不承诺任何结果。

---

## 2. AI / 爬虫使用限制（请先读这一节）

本仓库**不采用任何开源许可证**。除非另有书面授权：

- ❌ **禁止 AI 抓取、爬取、镜像、批量读取本仓库内容**（包括但不限于 GitHub 爬虫、数据集采集器、`git clone` 后批量喂给模型）。
- ❌ **禁止把本仓库内容用于训练、微调、蒸馏、RAG 索引、嵌入向量库、生成衍生数据集或合成数据**。
- ❌ **禁止复制、改写、转述、翻译后重新发布**本仓库的原创内容（尤其是 `03_notes/`、`tools/`、`04_chunks/`、`05_manifest/` 中的清单与说明）。
- ❌ **禁止把本仓库整体或部分上传到任何第三方 AI 服务、数据集平台、网盘、论坛或镜像站**。
- ❌ **禁止移除或篡改**来源、许可、署名信息（`05_manifest/` 与各文件头部的 `TITLE / URL / LICENSE / RETRIEVED` 字段）。
- ✅ **允许**：仓库所有者本人在本地读取、检索、自用；把第三方 CC / 公有领域文件按**其原始许可**使用（本仓库不额外授予任何权利）。
- ✅ **允许 AI 助手**：在所有者本人的授权会话中，作为本地上下文回答问题；这属于个人使用，不构成对外授权。

> 第三方内容（论文、维基条目、官方文件、开源 Skill）的许可由其各自权利人决定，本仓库只是**归档与署名**。本仓库的专有许可**只覆盖我们自己原创的部分**（笔记、脚本、清单、分类体系、编辑性选择与注释），**不覆盖也不试图限制**第三方内容的原有许可。

详见 [`LICENSE`](LICENSE)。同一份限制另有**给 AI 代理读的机器可读版本** [`AGENTS.md`](AGENTS.md)（编码代理与检索工具在进入仓库时会先读它）；两者措辞冲突时以 `LICENSE` 为准。

---

## 3. 内容边界（编写与筛选时执行的规则）

- **仅限成年人（18+）**。涉及未成年人的内容一律排除；标题/摘要含青少年、儿童、孕产等词的研究会被过滤掉。
- **不教操控**：不含 PUA、打压式搭讪（negging）、情感操控、施压、欺骗、"测试"等技巧。相关话题只以**识别与自保**的角度出现（见 `08_反操控与安全.md`）。这条规则同样**作用于抓来的第三方内容**：开源恋爱教练 Skill 里教「服从性测试 / 废物测试 / 冷读 / 推拉 / 进挪」的文件会被整份丢弃，连 `01_raw/` 都不留（实现见 `tools/fetch_zh.py` 的 `MANIP_MARKERS`，记录见 `00_readme/许可与来源说明.md` 第 4 节）。
- **不做群体决定论**：不写「所有女人都……」，不用年龄、星座、MBTI 去预测某个具体的人。星座/MBTI 只作为**破冰话题和社会现象**讨论。
- **不用贬义标签**：不使用「精神小妹」这类称呼；涉及县域/小镇年轻女性时使用中性表述并强调个体差异。
- **金钱优先自保**：谈钱的部分重点在**互惠是否对等、如何拒绝、如何识别单向索取与恋爱诈骗（杀猪盘）**，不是「怎么花钱换好感」。
- **版权克制**：媒体与商业心理平台文章只保存短摘录并注明出处；不搬运整本书、整篇付费文章。

---

## 4. 目录结构

```
chatkb-relationship-corpus/
├── README.md                  # 本文件
├── LICENSE                    # 专有许可（All Rights Reserved）+ AI 使用限制
├── 00_readme/                 # 附加说明（许可分层、来源清单等）
├── 01_raw/                    # 原始抓取文件（可复现、可校验）
│   ├── europepmc_xml/         #   论文 JATS XML 原文
│   ├── zh_official/           #   中文官方/媒体页面 HTML
│   ├── zh_wikipedia/          #   中文维基 API 原始 JSON
│   └── skills/                #   开源 Skill 仓库原始 md/txt
├── 02_text/                   # 清洗后的纯文本（带来源头部）
│   ├── europepmc/             #   每篇一个 .txt
│   ├── zh_official/
│   ├── zh_wikipedia/
│   ├── gutenberg/             #   公版中文/英文书籍纯文本
│   └── skills/
├── 03_notes/                  # ★ 原创中文实战笔记（本仓库核心价值）
├── 04_chunks/                 # 供 AI 知识库投喂的分块（chunks.jsonl）
├── 05_manifest/               # 元数据、许可报告、来源清单、抓取日志
│   ├── records/               #   每个文档一条 JSON（含 sha256、字节数、许可）
│   ├── search/                #   检索快照（可复现）
│   ├── manifest.jsonl         #   全库清单
│   └── report.json            #   体积/许可/主题统计
└── tools/                     # 抓取、清洗、分块、报告脚本
```

---

## 5. 许可分层（重要）

| 层 | 内容 | 许可 | 归属 |
| --- | --- | --- | --- |
| A. 原创层 | `03_notes/`、`tools/`、`04_chunks/`、`05_manifest/` 中的清单与注释、分类体系 | **专有（All Rights Reserved）**，见 `LICENSE` | 仓库所有者 |
| B. 开放获取论文 | `02_text/europepmc/` | 各篇文件头部标注（CC BY / CC BY-SA / CC BY-NC / CC BY-NC-SA / CC BY-NC-ND / CC0 / PD） | 原作者；本仓库仅归档，须保留署名 |
| C. 百科条目 | `02_text/zh_wikipedia/` | CC BY-SA 4.0 | 中文维基百科贡献者 |
| D. 官方公开文件 | 法律、政策、公告全文 | 官方公开文件（依当地法规可自由传播，仍注明出处） | 发布机关 |
| E. 公版书籍 | `02_text/gutenberg/` 等 | 公有领域 / Project Gutenberg 许可 | 原作者（已过版权期） |
| F. 媒体/商业文章 | `02_text/zh_official/` 中 `MODE: excerpt` 的文件 | **仅短摘录，个人研究用**；版权仍属原权利人 | 原媒体/机构 |
| G. 开源 Skill | `02_text/skills/` | 按仓库各自许可（MIT 等）；无许可者仅存短摘录 | 原仓库作者 |

**任何对外分享都必须逐层遵守上表**。A 层默认不可分享；B–G 层按其原许可，且必须保留 `02_text/*` 与 `05_manifest/records/*` 中的来源头部与署名信息。

---

## 6. 本地使用

```bash
# 环境（Windows / Git Bash）
uv venv .venv
.venv/Scripts/python.exe -m pip install requests beautifulsoup4 lxml lxml-html-clean pymupdf

# 抓取开放获取论文（增量，已下载的会跳过）
.venv/Scripts/python.exe tools/fetch_europepmc.py --target-raw-mb 150 --max-papers 2000 --per-query 100

# 抓取中文公开材料 / 维基 / 开源 Skill / 公版书
.venv/Scripts/python.exe tools/fetch_zh.py            # 全量
.venv/Scripts/python.exe tools/fetch_zh.py --only wiki
.venv/Scripts/python.exe tools/fetch_books.py --lang zh --max-total-mb 48

# 把原创笔记登记进清单（build_corpus 才会收录）
.venv/Scripts/python.exe tools/register_notes.py

# 清洗 + 分块 + 清单 + 报告
.venv/Scripts/python.exe tools/build_corpus.py
.venv/Scripts/python.exe tools/report.py

# 质检
.venv/Scripts/python.exe tools/verify_chunks.py      # 片段可解析、字段完整、长度分布、每种角色抽样
.venv/Scripts/python.exe tools/check_policy.py       # 合规扫描（操控/决定论/未成年/胁迫/贬义标签）
.venv/Scripts/python.exe tools/check_policy.py --dirs 03_notes 02_text/skills
.venv/Scripts/python.exe tools/prune_offtopic.py     # 删除混入的非主题论文
.venv/Scripts/python.exe tools/check_manifest_sync.py  # 清单与磁盘一致性（missing_files 必须为 0）

# 收紧过滤器之后复查已入库内容
.venv/Scripts/python.exe tools/prune_offtopic.py --scan            # 用当前标题过滤器复查（只列不删）
.venv/Scripts/python.exe tools/prune_offtopic.py --scan --apply    # 确认后删除
.venv/Scripts/python.exe tools/dedupe_wiki.py                      # 删除重定向重复与模糊命中抓到的错条目（原因写在 DROP 字典里）
.venv/Scripts/python.exe tools/prune_books.py                      # 删除混入的 Gutenberg 噪声书

# 加新内容之前先验证目标存在
.venv/Scripts/python.exe tools/diagnose_facets.py barnum_forer birth_date_mate   # facet 抓到 0 篇时看每条候选卡在哪道闸门
.venv/Scripts/python.exe tools/probe_wiki_titles.py                # 写进 WIKI 列表前先确认中文维基真有这一篇
.venv/Scripts/python.exe tools/fetch_europepmc.py --only-topics consent_types --dry-run   # 只数候选，不下载
```

> Windows / Git Bash 提示：脚本内部已强制 UTF-8 输出；在命令行里直接传中文参数会失败，所有中文都写在脚本的常量表里（`tools/query_specs.py`、`tools/fetch_zh.py`、`tools/fetch_books.py`）。

投喂 AI 知识库时用 `04_chunks/chunks.jsonl`（每行一个片段，带 `doc_id / source / license / topics / lang / role`），或用 `02_text/` 下的整篇 `.txt`。**不要**把 `01_raw/` 里的 HTML/XML 直接投喂，噪声太大。

---

## 6b. 版本管理（git）

仓库用 git 管理，**必须保持 private**。跟踪与忽略的边界：

| 目录 | 体积 | 是否进 git | 原因 |
| --- | --- | --- | --- |
| `README.md`、`LICENSE`、`AGENTS.md`、`00_readme/`、`03_notes/`、`tools/` | ~0.7 MB | ✅ | 原创层与规则本身 |
| `02_text/` | 114 MB | ✅ | 有效内容正文，单文件最大 2.7 MB，全部低于 GitHub 100 MB 硬限制 |
| `05_manifest/records/`、`manifest.jsonl`、`sources.csv`、`report.json` | ~9 MB | ✅ | 来源、许可、sha256 与统计，是"可核验"的依据 |
| `01_raw/` | 242 MB | ❌ | 原件只作复现凭证，本地保留；GitHub 上体积无意义 |
| `04_chunks/` | 198 MB | ❌ | `chunks.jsonl` 单个文件就超过 GitHub 100 MB 上限，且可由 `tools/build_corpus.py` 重建 |
| `05_manifest/search/`、`*.log`、`*.out`、`.venv/` | ~82 MB | ❌ | 检索响应缓存、抓取日志、虚拟环境 |

`.gitattributes` 里写了 `* -text`：**禁止换行符自动转换**，因为 `05_manifest/records/` 记录了每个文件的 sha256 与字节数，checkout 时被改过一个 `\n` 校验就会失败。

```bash
git init
git symbolic-ref HEAD refs/heads/main    # git <2.28 这样改名默认分支；新版直接 git init -b main
git add .
git status --short | wc -l               # 确认忽略生效（约 1790 个文件）
git commit -m "chatkb corpus: ..."
```

# 推到 GitHub（先在网页建一个 **private** 空仓库，不要勾选初始化 README/LICENSE）
git remote add origin git@github.com:<your-user>/chatkb-relationship-corpus.git
git push -u origin main
```

---

## 7. 规模快照

以 `05_manifest/report.json` 为准（每次运行 `tools/report.py` 会刷新）。

- 计量口径：**"有效内容" = `02_text/` + `03_notes/` 的字节数**——清洗过、带来源头部的纯文本。`04_chunks/` 是同一批文档重新序列化后的投喂导出（含片段重叠与元数据），与有效内容有重叠，**不叠加计算**。`01_raw/` 的 XML/HTML 只是可复现凭证，不计入。

快照（2026-10-26）：

| 项 | 数值 |
| --- | --- |
| 文档数 | 1766 篇（清单与磁盘一致：缺失正文文件 0） |
| 有效内容 | **114.54 MB**（120,103,077 字节） |
| 投喂导出 `04_chunks/chunks.jsonl` | 197.84 MB / 118,443 个片段（0 行解析失败，字段完整） |
| 原始凭证 `01_raw/` | 237.98 MB / 1787 个文件 |
| 语言分布 | en 81.41 MB（1389 篇）、zh 33.07 MB（375 篇）、es/de 各 1 篇 |
| 主题标签 | 236 个 |
| 短摘录文档 | 25 篇（`excerpt_only: true`，禁止再分发） |

按来源：

| 来源 | 篇数 | 有效内容 | 许可 |
| --- | --- | --- | --- |
| `europepmc` 开放获取论文 | 1339 | 58.81 MB | CC BY 970 / BY-NC-ND 176 / BY-NC 165 / BY-NC-SA 28 |
| `gutenberg` 公版书 | 108 | 51.92 MB | 公有领域（中文经典 56 本 + 英文 52 本，含 Ellis《Studies in the Psychology of Sex》卷 1–6 与礼仪会话手册） |
| `zh_wikipedia` 中文维基条目 | 264 | 2.72 MB | CC BY-SA 4.0（2026-10-26 逐条核对标题，清掉 17 条早期模糊命中抓到的错文章，见 `00_readme/许可与来源说明.md` 第 4 节） |
| `zh_official` 官方文件与媒体摘录 | 40 | 0.68 MB | 官方公开文件 17 篇（全文）+ 媒体/机构短摘录 23 篇 |
| `original_note` **原创中文笔记** | 13 | 0.25 MB | 专有（本仓库核心） |
| `github_skill` 开源 AI 恋爱教练 Skill | 2 | 0.17 MB | MIT（已按第 3 节规则剔除操控内容） |

### 性与玄学两条链路（2026-10-26 补充）

| 层 | 性与亲密 | 星座 / 生肖 / 玄学 |
| --- | --- | --- |
| 英文论文（Europe PMC facet） | 19 个 facet：性脚本 32、性积极态度 31、忠诚与越界 28、性胁迫 27、性满意度 26、 sexting 26、同意类型 22、性治疗与干预 16、无性恋与禁欲 16、自我表露 14、欲望差 13、频率 11、沟通训练 9、色情与关系 9、功能与障碍 9、安全性沟通 8、愉悦差异 7、年长性议题 2、合意非一夫一妻 3（合计约 309 篇次） | 7 个 facet：占星信念 10、超自然信念 9、占星效度检验 4、占卜与数字命理 2、迷信与决策 2、巴纳姆/福勒 1、出生日期与择偶 0（开放获取库里查不到这类论文，接受空结果而不是放宽过滤） |
| 中文百科（维基条目） | 性學、人类性行为、人类性反应周期、性愉悅、性欲、性功能障碍、性高潮、性治療、性取向、无性恋、性別認同、跨性別、避孕、生殖健康、安全性行為、前戲、性玩具、自慰、性侵犯、婚内强奸、约会强奸、網路性愛、色情、性教育、金赛报告等 | 黄道十二宫、星座、生肖、黄历、中國占星術、占星术、算命、占卜、八字命学、紫微斗数、面相學、塔罗牌、风水、迷信、巴纳姆效应、确认偏误、冷读术、伪科学、超自然等 12 个星座条目 |
| 官方与媒体 | 艾滋病防治条例与实施方案、婚前医学检查规范、地方免费婚检公告 | 市场监管部门对占卜经营的定性、新华/中青报对玄学消费与「运势付费」的报道与揭批、高校婚恋课程公告 |
| 公版书（Project Gutenberg） | Ellis《Studies in the Psychology of Sex》卷 1–6、《Sex and Society》《Taboo and Genetics》《The Social Emergency》《Homo-sexual Life》 | 无（检索到的候选全是宗教语文学与动物民俗，人工复核后删除，见 `00_readme/许可与来源说明.md` 第 4 节） |
| 原创笔记 | `03_notes/10_性沟通与同意.md` | `03_notes/11_星座生肖与玄学话题.md` |

两条链路执行同一底线：**只谈成年人的沟通、健康与自保**——不写露骨内容，不教用星座给人分类，玄学材料一律站在**机制解释与反诈**一侧。

---

## 8. 免责声明

- 本仓库是**个人学习资料**，不构成心理咨询、心理治疗、法律或财务建议。
- 研究结论存在文化与样本局限，不能直接套用到某个具体的人身上；**具体的人永远比任何分类重要**。
- 涉及人身安全、诈骗、家暴、胁迫时，请优先报警（110 / 96110）、联系妇联（12338）或心理援助热线（12356），并咨询专业人士。
- 引用的第三方观点不代表本仓库立场；本仓库明确反对操控、欺骗与任何形式的强迫。

---

## 9. 联系

私有仓库，不接收外部 issue / PR。如需授权（研究合作、二次分发、模型训练），请通过仓库所有者私下联系并取得书面许可。
