#!/usr/bin/env python3
"""提取书籍全文并按章节切分。

用法:
    .venv/bin/python tools/extract_book.py <book_path> [--outdir DIR]

支持格式: PDF / EPUB / TXT / DOCX

输出 (默认写到 .book_work/<书名>/):
    fulltext.md  带章节标记的全文，每章开头有一行 HTML 注释元信息
    meta.json    书名、格式、章节列表、各章字数、扫描版检测等

章节标记格式（供 book-compress 流程按章切片使用）:
    <!-- chapter: N | title: 章节标题 | chars: 字数 -->
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

CHAPTER_HEADER_RE = re.compile(
    r"^<!-- chapter: (\d+) \| title: (.*?) \| chars: (\d+) -->$"
)

# 中文/英文常见章节标题模式
CHAPTER_PATTERNS = [
    r"^第[一二三四五六七八九十百千0-9０-９]+[章部篇讲回]",
    r"^第[0-9０-９]+章",
    r"^Chapter\s+\d+",
    r"^PART\s+[IVX0-9]+",
    r"^Part\s+[IVX0-9]+",
    r"^\d{1,2}[、.．]\s*\S{2,}",
]


def clean_text(text: str) -> str:
    """规范化空白与 Unicode，合并硬换行产生的碎句。"""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    # 段落内硬换行合并：单换行且前后都不是标题/列表 → 合并
    lines = [ln.strip() for ln in text.split("\n")]
    merged = []
    buf = ""
    for ln in lines:
        if not ln:
            if buf:
                merged.append(buf)
                buf = ""
            merged.append("")
        elif re.match(r"^(#|[-*]\s|\d+[、.．]\s|>)", ln) or looks_like_heading(ln):
            if buf:
                merged.append(buf)
                buf = ""
            merged.append(ln)
        else:
            buf = f"{buf}{ln}" if buf else ln
    if buf:
        merged.append(buf)
    out = "\n".join(merged)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def looks_like_heading(line: str) -> bool:
    if len(line) > 60:
        return False
    return any(re.match(p, line) for p in CHAPTER_PATTERNS)


# ---------------------------------------------------------------- EPUB

def extract_epub(path: Path):
    from ebooklib import epub, ITEM_DOCUMENT
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(path), options={"ignore_ncx": False})
    title = (book.get_metadata("DC", "title") or [("未知书名", "")])[0][0]
    author = (book.get_metadata("DC", "creator") or [("未知作者", "")])[0][0]

    # 从 TOC 拿标题映射（href -> title）
    toc_titles = {}

    def walk_toc(items):
        for it in items:
            if isinstance(it, tuple):
                section, children = it
                href = getattr(section, "href", None)
                if href:
                    toc_titles[href.split("#")[0]] = re.sub(
                        r"\s+", " ", str(section.title or "")
                    ).strip()
                walk_toc(children)
            else:
                href = getattr(it, "href", None)
                if href:
                    toc_titles[href.split("#")[0]] = re.sub(
                        r"\s+", " ", str(it.title or "")
                    ).strip()

    try:
        walk_toc(book.toc)
    except Exception:
        pass

    chapters = []
    for idx, item in enumerate(book.get_items_of_type(ITEM_DOCUMENT), 1):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()
        text = soup.get_text("\n")
        text = clean_text(text)
        if not text or len(text) < 50:  # 跳过封面/目录/版权页碎片
            continue
        href = item.get_name()
        toc_title = toc_titles.get(href) or toc_titles.get(href.split("/")[-1], "")
        first_heading = ""
        h = soup.find(["h1", "h2", "h3"])
        if h:
            first_heading = re.sub(r"\s+", " ", h.get_text()).strip()
        title_line = toc_title or first_heading or f"第{len(chapters) + 1}部分"
        chapters.append({"title": title_line, "text": text})

    return title, author, chapters


# ---------------------------------------------------------------- PDF

def extract_pdf(path: Path):
    import pymupdf

    doc = pymupdf.open(str(path))
    title = (doc.metadata or {}).get("title") or path.stem
    author = (doc.metadata or {}).get("author") or "未知作者"

    total_chars = 0
    page_texts = []
    for page in doc:
        t = clean_text(page.get_text("text"))
        page_texts.append(t)
        total_chars += len(t)

    warnings = []
    # 扫描版检测：平均每页可提取字符过少
    if doc.page_count >= 5 and total_chars / max(doc.page_count, 1) < 100:
        warnings.append(
            "PDF 疑似扫描版（平均每页可提取文本 <100 字符），需要先 OCR。"
            "建议用 ocrmypdf 或 ABCLily OCR 后重跑。"
        )

    toc = doc.get_toc()  # [(level, title, page), ...]
    chapters = []
    if toc:
        # 用书签边界切分；只取 level-1 项作为章边界
        bounds = [(p - 1, t) for lvl, t, p in toc if lvl <= 1 and p <= doc.page_count]
        if bounds and bounds[0][0] > 0:
            chapters.append({"title": "前言", "pages": (0, bounds[0][0])})
        for i, (start, t) in enumerate(bounds):
            end = bounds[i + 1][0] if i + 1 < len(bounds) else doc.page_count
            chapters.append({"title": t, "pages": (start, end)})
    else:
        # 无书签：逐页找章节标题行
        current_title, buf = "前言", []
        for t in page_texts:
            first = t.split("\n", 1)[0].strip() if t else ""
            if looks_like_heading(first):
                rest = t.split("\n", 1)[1].strip() if "\n" in t else ""
                if buf:
                    chapters.append({"title": current_title, "text": "\n".join(buf)})
                current_title, buf = first, [rest]
            else:
                buf.append(t)
        if buf:
            chapters.append({"title": current_title, "text": "\n".join(buf)})
        chapters = [
            c if "text" in c else {**c, "text": "\n".join(
                page_texts[c["pages"][0]:c["pages"][1]])}
            for c in chapters
        ]
    if toc:
        chapters = [
            {**c, "text": "\n".join(page_texts[c["pages"][0]:c["pages"][1]])}
            for c in chapters
        ]
    # 过滤近空章节
    chapters = [c for c in chapters if len(c.get("text", "").strip()) >= 30]

    doc.close()
    return title, author, chapters, warnings


# ---------------------------------------------------------------- TXT

def extract_txt(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.split("\n")
    chapters, current_title, buf = [], "正文", []
    for ln in lines:
        s = ln.strip()
        if looks_like_heading(s):
            if buf:
                chapters.append({"title": current_title, "text": "\n".join(buf)})
            current_title, buf = s, [ln]
        else:
            buf.append(ln)
    if buf:
        chapters.append({"title": current_title, "text": "\n".join(buf)})
    chapters = [
        {**c, "text": clean_text(c["text"])} for c in chapters
        if len(clean_text(c["text"])) >= 30
    ]
    return path.stem, "未知作者", chapters


# ---------------------------------------------------------------- DOCX

def extract_docx(path: Path):
    import docx as docx_lib

    d = docx_lib.Document(str(path))
    title = d.core_properties.title or path.stem
    author = d.core_properties.author or "未知作者"
    chapters, current_title, buf = [], "正文", []
    for para in d.paragraphs:
        text = para.text.strip()
        style = (para.style.name or "").lower()
        is_heading = ("heading" in style or "标题" in style) and text
        if not is_heading and text and looks_like_heading(text) and len(buf) > 200:
            is_heading = True  # 正文长段后出现章节样式行，视为章边界
        if is_heading:
            if buf:
                chapters.append({"title": current_title, "text": "\n".join(buf)})
            current_title, buf = text, []
        elif text:
            buf.append(text)
    if buf:
        chapters.append({"title": current_title, "text": "\n".join(buf)})
    chapters = [
        {**c, "text": clean_text(c["text"])} for c in chapters
        if len(clean_text(c["text"])) >= 30
    ]
    return title, author, chapters


# ---------------------------------------------------------------- main

def write_outputs(outdir: Path, title, author, chapters, fmt, warnings):
    outdir.mkdir(parents=True, exist_ok=True)
    fulltext = outdir / "fulltext.md"
    meta_path = outdir / "meta.json"

    meta_chapters = []
    parts = [f"# {title}\n\n**作者**: {author}\n"]
    for i, ch in enumerate(chapters, 1):
        text = ch["text"]
        t = ch["title"]
        # 标题已自带章号时不再重复冠以"第N章"
        heading = t if re.match(r"^(第.{1,8}[章部篇讲回]|Chapter\s|PART|Part\s)", t) \
            else f"第{i}章 {t}"
        header = f"<!-- chapter: {i} | title: {t} | chars: {len(text)} -->"
        block = f"{header}\n\n## {heading}\n\n{text}\n"
        parts.append(block)
        meta_chapters.append({
            "index": i,
            "title": ch["title"],
            "chars": len(text),
        })
    fulltext.write_text("\n".join(parts), encoding="utf-8")

    meta = {
        "title": title,
        "author": author,
        "format": fmt,
        "source": str(book_path),
        "total_chars": sum(c["chars"] for c in meta_chapters),
        "n_chapters": len(meta_chapters),
        "chapters": meta_chapters,
        "warnings": warnings,
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] 提取完成: {fulltext}")
    print(f"[ok] 元数据:   {meta_path}")
    print(f"    书名: {title} | 格式: {fmt} | 章节数: {len(meta_chapters)} "
          f"| 总字数: {meta['total_chars']}")
    for w in warnings:
        print(f"[warn] {w}", file=sys.stderr)


def main():
    global book_path
    parser = argparse.ArgumentParser(description="书籍提取与章节切分")
    parser.add_argument("book", help="书籍文件路径")
    parser.add_argument("--outdir", default=None, help="输出目录")
    args = parser.parse_args()

    book_path = Path(args.book).expanduser().resolve()
    if not book_path.exists():
        sys.exit(f"[error] 文件不存在: {book_path}")

    fmt = book_path.suffix.lower().lstrip(".")
    outdir = Path(args.outdir) if args.outdir else \
        Path(__file__).resolve().parent.parent / ".book_work" / book_path.stem

    warnings = []
    if fmt == "epub":
        title, author, chapters = extract_epub(book_path)
    elif fmt == "pdf":
        title, author, chapters, warnings = extract_pdf(book_path)
    elif fmt == "txt":
        title, author, chapters = extract_txt(book_path)
    elif fmt == "docx":
        title, author, chapters = extract_docx(book_path)
    else:
        sys.exit(f"[error] 不支持的格式: .{fmt}（支持 pdf/epub/txt/docx）")

    if not chapters:
        sys.exit("[error] 未能识别出任何章节内容")
    write_outputs(outdir, title, author, chapters, fmt, warnings)


if __name__ == "__main__":
    main()
