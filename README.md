# book-compress —— 书籍压缩 Agent（讲书版）

把一本书（PDF/EPUB/TXT/DOCX）压成"有人给你讲书"的精读版：输出 Kindle 可读的 EPUB（含封面、目录、章末总结）+ Markdown 源稿 + 压缩报告。

核心保证：**核心观点一个不少（可逐条溯源），废话一字不留**。方法论源自对长文摘要研究（BooookScore）、事实一致性评估（SummaC/FactCC）和总结写作经典理论（Brown & Day 宏观规则）的调研与实战打磨。

## 这不是某个平台的插件

本仓库就是一份 `SKILL.md`（工作流定义）+ 四个普通 Python 脚本，**任何智能体都可以使用**——只要它能读文件、能执行命令，就没有任何门槛：

- **有技能/斜杠命令系统的 Agent**：把 `SKILL.md` 放进其技能目录即可用命令调用；
- **没有技能系统的 Agent**：无需安装，把 SKILL.md 的路径发给它，说"按这个流程压缩这本书"，它读完就会照着执行，脚本用系统 Python 跑即可。

换平台、换模型都不影响——因为方法论全部写在 SKILL.md 里，工具只是 pandoc 和几个标准库脚本。

## 文件结构

```
book-compress/
├── SKILL.md              # 工作流定义（Agent 的大脑，所有流程与原则都在这里）
├── INSTALL.md            # 依赖安装指南
└── tools/
    ├── extract_book.py   # 提取全书并切分章节（PDF/EPUB/TXT/DOCX，扫描版检测）
    ├── make_cover.py     # 封面：程序生成排版封面（默认），可选提取原书封面
    ├── build_epub.py     # Markdown → Kindle 可读 EPUB（封面 + 目录）
    └── make_test_books.py# 生成测试书（验证流程用）
```

## 安装（3 步）

1. **放置文件**：
   - 支持技能目录的 Agent：把 `SKILL.md` 放进其技能目录（各家目录不同，如 `~/.zcode/skills/`、`~/.claude/skills/` 等）；
   - 其他任何 Agent：无需放置，能告诉它 SKILL.md 的路径即可。
   （SKILL.md 里的 `<skill-dir>/scripts/`、`<python>` 是占位符，对应你实际的脚本目录和 Python 调用方式）

2. **装依赖**（详见 [INSTALL.md](INSTALL.md)）：
   ```bash
   pip install pymupdf beautifulsoup4 python-docx ebooklib Pillow
   # EPUB 生成还需要 pandoc：brew install pandoc（macOS）
   ```

3. **调用**：
   ```
   /book-compress <书的路径>          # 支持斜杠命令的 Agent
   "按 SKILL.md 的流程压缩这本书"    # 其他 Agent
   ```

## 输出

`output/<书名>/` 下三个文件：
- `压缩版.epub` —— 传 Kindle 即可读（封面 + 目录 + 每章末尾总结）
- `压缩版.md` —— 源稿，可搜索、再加工
- `压缩报告.md` —— 压缩比、书型判定、审计结果

## 核心设计（为什么不会"变味"）

1. **讲书模式**：每章由代理读完原文后用自己的话转述，像向没读过的人讲书——论证顺序、逻辑关系显式交代，案例嵌进叙述。
2. **两层保真**：事实层（数字/人名/实验设计/结果/限定词）锁死，叙述层放开；禁止模糊词代替数字、禁止引入原文没有的事实。
3. **篇幅由内容决定**：先盘点论证单元（讲/略讲/不讲+理由），再全部讲清，字数是结果不是目标。
4. **独立语义审计**：由未参与写作的审计代理逐节对照原文与讲稿，按 A 事实错误 / B 语义漂移 / C 无据新增 / D 关键遗漏 / E 风格差异 分级，A/B/C/D 必须修复清零——专抓"推测变事实、单院研究变普遍规律、归属张冠李戴"这类机检抓不到的叙述层失真。
5. **章末总结**（Brown & Day 宏观规则 + BLUF + 教科书 Key Takeaways 对齐原则）：条数由本章独立主张数决定（通常 3~5 条，不设配额），只收判断不收证据，自创归纳必须回源。
6. **数字回源机检**：全书数字 token（金额/百分比/年份/样本量）逐个回原文定位。
7. **跨章去重**：同一观点只完整保留一次，标注其余出处章节。

## 注意

- 扫描版 PDF 需要先 OCR（推荐 [ocrmypdf](https://ocrmypdf.readthedocs.io/)），提取脚本会检测并提示。
- 依赖环境：Python 3.10+，macOS/Windows/Linux 均可（封面中文字体按系统自动选择）。
- 本工具输出的是书籍的压缩学习版，仅供个人学习使用；请尊重原书版权，勿传播成品。

## License

[MIT](LICENSE)
