# book-compress —— 书籍压缩 Agent（讲书版）

把一本书（PDF/EPUB/TXT/DOCX）压成"有人给你讲书"的精读版，输出 Kindle 可读的 EPUB + Markdown 源稿 + 压缩报告。每章末尾自带**累积思维导图**（第 N 章的导图覆盖第 1~N 章）。

## 文件结构

```
book-compress/
├── SKILL.md              # 技能定义（Agent 的大脑，所有流程与原则都在这里）
└── tools/
    ├── extract_book.py   # 提取全书并切分章节（PDF/EPUB/TXT/DOCX）
    ├── make_cover.py     # 封面：优先提取原书封面，拿不到则生成排版封面
    ├── build_epub.py     # Markdown → Kindle 可读 EPUB（含封面、目录）
    └── make_test_books.py# 生成测试书（可选，验证用）
```

## 安装到 ZCode（3 步）

1. **放技能文件**：把 `SKILL.md` 放到你的 ZCode 工作区的技能目录：
   - 全局：`~/.zcode/skills/book-compress/SKILL.md`
   - 或工作区级：`<工作区>/.zcode/skills/book-compress/SKILL.md`
   （把 `tools/` 整个目录也放进 `<工作区>/tools/`。注意：SKILL.md 里的 `<skill-dir>/scripts/`、`<python>` 是占位符，安装时对应你实际的脚本目录和 python 调用方式即可）

2. **装依赖**（只需一次）：
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install pymupdf beautifulsoup4 python-docx ebooklib Pillow
   # 还需要 pandoc（EPUB 生成用）：brew install pandoc
   ```

3. **调用**：把书放进工作区，然后：
   ```
   /book-compress <书的路径>
   ```

## 输出

`output/<书名>/` 下三个文件：
- `压缩版.epub` —— 传 Kindle 即可读（带封面 + 目录 + 每章累积思维导图）
- `压缩版.md` —— 源稿，可搜索、再加工
- `压缩报告.md` —— 压缩比、书型判定、审计结果

## 核心设计（为什么不会"变味"）

1. **讲书模式**：每章由代理读完原文后用自己的话转述，像向没读过的人讲书——论证顺序、逻辑关系显式交代，案例嵌进叙述（数字机检兜底：全书数字 token 逐个回源）。
2. **两层保真**：事实层（数字/人名/实验设计/结果/限定词）锁死，叙述层放开；禁止模糊词代替数字、禁止引入原文没有的事实。
3. **篇幅由内容决定**：先盘点论证单元（讲/略讲/不讲+理由），再全部讲清，字数是结果不是目标。
4. **独立语义审计**：由未参与写作的审计代理逐节对照原文与讲稿，按 A 事实错误 / B 语义漂移 / C 无据新增 / D 关键遗漏 / E 风格差异 分级，A/B/C/D 必须修复清零。
5. **累积思维导图**：每章末尾附导图，第 N 章覆盖第 1~N 章；当前章展开到三级（论点→证据，带核心数字），前文各章压缩为二级枝干且逐字保持一致；导图节点全部可回源。
6. **跨章去重**：同一观点只完整保留一次，标注其余出处章节。

## 注意

- 扫描版 PDF 需要先 OCR（ocrmypdf），提取脚本会检测并提示。
- 依赖环境：Python 3.10+，macOS/Windows/Linux 均可（封面中文字体按系统自动选择）。
