#!/usr/bin/env python3
"""把压缩版 Markdown 编译为 Kindle 可读的 EPUB。

用法:
    .venv/bin/python tools/build_epub.py <压缩版.md> -o output/<书名>/压缩版.epub \
        [--title 书名] [--author 作者]

约定：压缩版 Markdown 中每章用 `## ` 标题（二级），pandoc 按 level-2 切分
EPUB spine，目录即"一章一节"，与原书目录一一对应。
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Markdown → EPUB")
    parser.add_argument("markdown", help="压缩版 Markdown 文件")
    parser.add_argument("-o", "--output", required=True, help="输出 .epub 路径")
    parser.add_argument("--title", default=None, help="书名（默认从一级标题读取）")
    parser.add_argument("--author", default="book-compress")
    parser.add_argument("--cover", default=None, help="封面图片路径（jpg/png）")
    args = parser.parse_args()

    md = Path(args.markdown).expanduser().resolve()
    if not md.exists():
        sys.exit(f"[error] 文件不存在: {md}")

    title = args.title
    if not title:
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        title = title or md.stem

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pandoc", str(md),
        "-o", str(out),
        "-f", "markdown+east_asian_line_breaks",
        "-t", "epub3",
        "--metadata", f"title={title}",
        "--metadata", f"author={args.author}",
        "--metadata", "lang=zh-CN",
        "--metadata", "copyright=压缩学习版 · 观点与例子均摘自原书",
        "--toc", "--toc-depth=2",
        "--split-level=2",
    ]
    if args.cover:
        cover = Path(args.cover).expanduser().resolve()
        if not cover.exists():
            sys.exit(f"[error] 封面不存在: {cover}")
        cmd += ["--epub-cover-image", str(cover)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"[error] pandoc 失败:\n{result.stderr}")
    print(f"[ok] EPUB 已生成: {out}（{out.stat().st_size // 1024} KB）")


if __name__ == "__main__":
    main()
