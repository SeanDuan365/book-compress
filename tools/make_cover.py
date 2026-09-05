#!/usr/bin/env python3
"""为压缩版 EPUB 准备封面：优先提取原书封面，拿不到则用书名生成一张排版封面。

用法:
    .venv/bin/python tools/make_cover.py --title "书名" --author "作者" \
        --out output/<书名>/cover.jpg [--source 原书路径] [--label 精读版]

规则:
- 提供了 --source 且为 EPUB: 在其中查找封面图（cover 属性 / 文件名含 cover 的图片），
  找到则提取保存，原书封面直接复用。
- 找不到或无 --source: 生成 1200x1600 排版封面（深色底 + 书名 + 作者 + 角标）。
"""

import argparse
import io
import sys
from pathlib import Path

# macOS 常见中文字体，按优先级尝试
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def extract_from_epub(source: Path) -> bytes | None:
    try:
        from ebooklib import epub, ITEM_IMAGE
    except ImportError:
        return None
    try:
        book = epub.read_epub(str(source))
    except Exception as e:
        print(f"[warn] 读取源 EPUB 失败: {e}", file=sys.stderr)
        return None

    # 1) OPF 里 <meta name="cover"> 指定的项
    for item in book.get_items_of_type(ITEM_IMAGE):
        if "cover" in item.get_name().lower():
            return item.get_content()

    # 2) 文件名含 cover 的第一张图（上面循环已覆盖）
    # 3) 兜底：spine 里第一张图片
    for item in book.get_items_of_type(ITEM_IMAGE):
        return item.get_content()
    return None


def wrap_text(draw, text, font, max_width):
    lines, buf = [], ""
    for ch in text:
        if draw.textlength(buf + ch, font=font) > max_width and buf:
            lines.append(buf)
            buf = ch
        else:
            buf += ch
    if buf:
        lines.append(buf)
    return lines


def generate_cover(title: str, author: str, label: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 1600
    BG = (24, 32, 48)
    FG = (240, 240, 235)
    ACCENT = (212, 160, 63)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    def load_font(size, bold=False):
        for path in FONT_CANDIDATES:
            if Path(path).exists():
                try:
                    # PingFing/Songti 是 ttc 集合，index 0 一般是常规字重
                    idx = 2 if (bold and "PingFang" in path) else 0
                    return ImageFont.truetype(path, size, index=idx)
                except Exception:
                    try:
                        return ImageFont.truetype(path, size)
                    except Exception:
                        continue
        return ImageFont.load_default()

    # 顶部角标
    tag_font = load_font(44)
    tag = f"BOOK-COMPRESS · {label}"
    draw.rectangle([80, 120, 80 + draw.textlength(tag, font=tag_font) + 48, 196],
                   outline=ACCENT, width=3)
    draw.text((104, 132), tag, font=tag_font, fill=ACCENT)

    # 书名（自动换行，逐行居中）
    title_font = load_font(140, bold=True)
    lines = wrap_text(draw, title, title_font, W - 200)[:6]
    total_h = sum(draw.textbbox((0, 0), ln, font=title_font)[3] + 36 for ln in lines)
    y = (H - total_h) // 2 - 60
    for ln in lines:
        w = draw.textlength(ln, font=title_font)
        draw.text(((W - w) // 2, y), ln, font=title_font, fill=FG)
        y += draw.textbbox((0, 0), ln, font=title_font)[3] + 36

    # 分隔线 + 作者
    draw.line([(W // 2 - 90, y + 60), (W // 2 + 90, y + 60)], fill=ACCENT, width=3)
    author_font = load_font(64)
    aw = draw.textlength(author, font=author_font)
    draw.text(((W - aw) // 2, y + 110), author, font=author_font, fill=FG)

    # 底部说明
    note_font = load_font(36)
    note = "观点与例子均摘自原书 · 压缩学习版"
    nw = draw.textlength(note, font=note_font)
    draw.text(((W - nw) // 2, H - 140), note, font=note_font,
              fill=(160, 160, 155))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description="准备 EPUB 封面")
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", default="")
    parser.add_argument("--out", required=True, help="输出 cover.jpg 路径")
    parser.add_argument("--source", default=None, help="原书文件（EPUB）路径")
    parser.add_argument("--label", default="精读版", help="封面角标文字")
    args = parser.parse_args()

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    data, how = None, None
    if args.source:
        src = Path(args.source).expanduser().resolve()
        if src.suffix.lower() == ".epub" and src.exists():
            data = extract_from_epub(src)
            how = f"提取自原书封面: {src.name}"
    if data is None:
        data = generate_cover(args.title, args.author, args.label)
        how = "程序生成排版封面"

    out.write_bytes(data)
    print(f"[ok] 封面: {out}（{how}，{len(data)//1024} KB）")


if __name__ == "__main__":
    main()
