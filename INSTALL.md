# 安装指南

## 1. Python 依赖

需要 Python 3.10+。建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pymupdf beautifulsoup4 python-docx ebooklib Pillow
```

## 2. pandoc（EPUB 生成必需）

```bash
# macOS
brew install pandoc

# Windows
winget install JohnMacFarlane.Pandoc

# Ubuntu / Debian
sudo apt install pandoc
```

验证：`pandoc --version`

## 3. 放置技能文件

把 `SKILL.md` 放进 ZCode 的技能目录：

- 全局：`~/.zcode/skills/book-compress/SKILL.md`
- 工作区级：`<工作区>/.zcode/skills/book-compress/SKILL.md`

把 `tools/` 目录整体复制到工作区根目录下（或按你的习惯放置，并同步修改 SKILL.md 中的脚本调用路径占位符）。

## 4. 验证

把任意一本 EPUB/PDF/TXT/DOCX 书籍放进工作区，运行：

```
/book-compress <书的路径>
```

## 常见问题

- **扫描版 PDF 提取不出文字**：需要先 OCR（推荐 `ocrmypdf input.pdf output.pdf`），提取脚本会自动检测并提示。
- **EPUB 生成失败**：检查 pandoc 是否已安装、是否在 PATH 中。
- **生成的封面中文显示为方块**：系统缺少中文字体（主要是 Linux 服务器），安装任意中文字体（如 `fonts-noto-cjk`）后重试。
