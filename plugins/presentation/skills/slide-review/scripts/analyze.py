#!/usr/bin/env python3
"""スライド（PDF / Marp Markdown）を機械的に計測し、評価の材料を出力する。

使い方:
    python analyze.py <input.pdf|input.md|input.pptx> <out_dir> [--minutes N] [--pages A-B]

出力（out_dir 配下）:
    analysis.json   ページごとの計測結果
    summary.md      エージェントが読むための要約
    thumbs/pNN.png  幅 320px のサムネイル（サムネイル判定用）
    sheets/sheetN.png  サムネイルを 4×3 に並べた一覧
    full/pNN.png    幅 1280px の画像（細部の確認用）

依存: pymupdf（pip install pymupdf）。Marp の場合は npx（@marp-team/marp-cli）と Chrome。
pptx の場合は LibreOffice（soffice）。python-pptx があれば発表者ノートと指定フォントも読む。
"""

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit("pymupdf が必要です: pip install pymupdf")

# 基準: PowerPoint 16:9 の幅 960pt で本文 24pt、注釈 18pt
BASE_WIDTH = 960.0
BODY_MIN = 24.0
NOTE_MIN = 18.0

THUMB_WIDTH = 320
FULL_WIDTH = 1280
SHEET_COLS, SHEET_ROWS = 4, 3

MARP_CLI = "@marp-team/marp-cli@4.1.2"

# 環境依存（OS 付属）のフォント。名前の部分一致で判定する
ENV_DEPENDENT_FONTS = [
    "MS-Gothic", "MSGothic", "MS-PGothic", "MSPGothic", "MS-Mincho", "MSMincho",
    "MS-PMincho", "MSPMincho", "MS-UIGothic", "Meiryo", "YuGothic", "Yu Gothic",
    "YuMincho", "Yu Mincho", "Hiragino", "Osaka", "Segoe", "Trebuchet",
    "Calibri", "Cambria", "Candara", "Consolas", "Tahoma", "Verdana", "Georgia",
    "Century", "BIZ-UD", "BIZUD", "UDDigiKyokasho",
]

JA = r"぀-ヿ㐀-鿿ｦ-ﾟ"
# 日本語と英字が半角スペースなしで接している箇所（数字は対象外）
RE_JA_THEN_EN = re.compile(rf"[{JA}][A-Za-z][A-Za-z0-9.+#\-]*")
RE_EN_THEN_JA = re.compile(rf"[A-Za-z][A-Za-z0-9.+#\-]*(?<![0-9])[{JA}]")
RE_THANKS = re.compile(r"ご清聴|ありがとうございま|Thank you|Thanks", re.I)

# Marp の HTML コメントのうち、ディレクティブ（key: value）だけのもの
MARP_DIRECTIVE = re.compile(r"^\s*_?[A-Za-z][A-Za-z0-9]*\s*:")


def clean_font(name):
    return name.split("+", 1)[1] if "+" in name else name


def rel_luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((rel_luminance(a), rel_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def int_to_rgb(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def hexcolor(rgb):
    return "#%02x%02x%02x" % rgb


def quantize(rgb, step=16):
    return tuple(min(255, (v // step) * step + step // 2) for v in rgb)


def background_color(pix, rect, scale, margin=3):
    """行の矩形のすぐ外側をなぞり、最も多い色を背景色とみなす（文字そのものを拾わないため）。"""
    x0, y0 = max(0, int(rect.x0 * scale) - margin), max(0, int(rect.y0 * scale) - margin)
    x1, y1 = min(pix.width - 1, int(rect.x1 * scale) + margin), min(pix.height - 1, int(rect.y1 * scale) + margin)
    if x1 <= x0 or y1 <= y0:
        return None
    counter = collections.Counter()
    for x in range(x0, x1 + 1, 2):
        counter[quantize(pix.pixel(x, y0)[:3])] += 1
        counter[quantize(pix.pixel(x, y1)[:3])] += 1
    for y in range(y0, y1 + 1, 2):
        counter[quantize(pix.pixel(x0, y)[:3])] += 1
        counter[quantize(pix.pixel(x1, y)[:3])] += 1
    return counter.most_common(1)[0][0]


def page_palette(pix, top=6):
    counter = collections.Counter()
    for y in range(0, pix.height, 4):
        for x in range(0, pix.width, 4):
            counter[quantize(pix.pixel(x, y)[:3], 32)] += 1
    total = sum(counter.values())
    return [(hexcolor(c), round(n / total, 3)) for c, n in counter.most_common(top) if n / total >= 0.01]


def has_japanese_font():
    try:
        out = subprocess.run(["fc-list", ":lang=ja", "family"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return True  # fontconfig のない環境（macOS など）では確認しない
    return bool(out.strip())


def marp_declared_fonts(md_text):
    """Marp の CSS で指定されたフォント名を返す。"""
    fonts = []
    for decl in re.findall(r"font-family\s*:\s*([^;}\n]+)", md_text):
        for name in decl.split(","):
            name = name.strip().strip("'\"").strip()
            if name and name.lower() not in ("sans-serif", "serif", "monospace") and name not in fonts:
                fonts.append(name)
    return fonts


def check_installed(fonts):
    """指定フォントがこの環境で解決されるかを調べる。"""
    result = []
    for name in fonts:
        try:
            matched = subprocess.run(["fc-match", "-f", "%{family}", name],
                                     capture_output=True, text=True).stdout
        except FileNotFoundError:
            matched = None
        installed = None if matched is None else name.lower() in matched.lower()
        result.append({"font": name, "installed": installed, "fallback": matched})
    return result


def pptx_to_pdf(pptx_path, out_dir):
    cmd = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=600)
    except FileNotFoundError:
        sys.exit("pptx の変換には LibreOffice（soffice）が必要です。PDF に書き出したものを指定してください。")
    return out_dir / (pptx_path.stem + ".pdf")


def pptx_info(pptx_path):
    """発表者ノートと、テーマ・テキストで指定されたフォント名を返す。python-pptx がなければ空。"""
    try:
        from pptx import Presentation
    except ImportError:
        return None, None
    prs = Presentation(str(pptx_path))
    notes, fonts = [], collections.Counter()
    for slide in prs.slides:
        notes.append(slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else "")
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.name and run.text.strip():
                        fonts[run.font.name] += len(run.text.strip())
    # テーマのフォント（明示指定のない文字に使われる）
    for master in prs.slide_masters:
        for rel in master.part.rels.values():
            if rel.reltype.endswith("/theme"):
                xml = rel.target_part.blob.decode("utf-8", "ignore")
                for tag in ("latin", "ea"):
                    for face in re.findall(rf'<a:{tag} typeface="([^"]+)"', xml)[:2]:
                        if face and not face.startswith("+"):
                            fonts.setdefault(face, 0)
    return notes, [f for f, _ in fonts.most_common()]


def marp_to_pdf(md_path, out_dir):
    pdf_path = out_dir / (md_path.stem + ".pdf")
    cmd = ["npx", "-y", MARP_CLI, "--pdf", "--allow-local-files", str(md_path), "-o", str(pdf_path)]
    # marp-cli は標準入力が開いていると入力を待ち続けるため、明示的に閉じる
    subprocess.run(cmd, check=True, cwd=md_path.parent, capture_output=True,
                   stdin=subprocess.DEVNULL, timeout=300)
    return pdf_path


def marp_notes(md_text):
    """Marp のスライドごとに、ディレクティブ以外の HTML コメント（発表者ノート）を返す。"""
    body = md_text
    m = re.match(r"^---\n.*?\n---\n", md_text, re.S)
    if m:
        body = md_text[m.end():]
    slides, buf, fence = [], [], False
    for line in body.split("\n"):
        if line.startswith("```"):
            fence = not fence
        if not fence and line.strip() == "---":
            slides.append("\n".join(buf))
            buf = []
        else:
            buf.append(line)
    slides.append("\n".join(buf))
    notes = []
    for s in slides:
        found = []
        for c in re.findall(r"<!--(.*?)-->", s, re.S):
            lines = [l for l in c.strip().split("\n") if l.strip()]
            if lines and not all(MARP_DIRECTIVE.match(l) for l in lines):
                found.append(c.strip())
        notes.append("\n".join(found))
    return notes


def analyze_page(page, index):
    width = page.rect.width
    k = BASE_WIDTH / width  # PowerPoint 換算の倍率
    scale = 2.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)

    # 行単位で集計する。PDF の span は字形ごとに細切れになることがあるため
    spans, lines_text = [], []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not re.search(r"\w", text):
                continue
            rect = pymupdf.Rect(line["bbox"])
            y = rect.y0 / page.rect.height
            # 下端の短い数字はページ番号とみなし、判定から外す
            if y > 0.85 and re.fullmatch(r"[0-9]{1,3}", text):
                continue
            size, color, font = collections.Counter(), collections.Counter(), collections.Counter()
            for s in line["spans"]:
                n = len(s["text"].strip())
                size[round(s["size"] * k, 1)] += n
                color[s["color"]] += n
                font[clean_font(s["font"])] += n
            fg = int_to_rgb(color.most_common(1)[0][0])
            bg = background_color(pix, rect, scale)
            spans.append({
                "text": text,
                "font": font.most_common(1)[0][0],
                "pt": size.most_common(1)[0][0],
                "color": hexcolor(fg),
                "bg": hexcolor(bg) if bg else None,
                "contrast": round(contrast(fg, bg), 2) if bg else None,
                "y": round(y, 3),
                "line": len(lines_text),
            })
            lines_text.append(text)

    chars = sum(len(s["text"]) for s in spans)
    small_body = [s for s in spans if NOTE_MIN <= s["pt"] < BODY_MIN]
    small_note = [s for s in spans if s["pt"] < NOTE_MIN]
    low_contrast = [s for s in spans if s["contrast"] is not None
                    and s["contrast"] < (4.5 if s["pt"] < NOTE_MIN else 3.0)]

    # 見出し候補: 上部 30% にある最大サイズの行
    top = [s for s in spans if s["y"] < 0.3]
    heading = None
    if top:
        max_pt = max(s["pt"] for s in top)
        heading_lines = dict.fromkeys(s["line"] for s in top if s["pt"] == max_pt)
        heading = " ".join(lines_text[i] for i in heading_lines if i < len(lines_text))

    full_text = "\n".join(lines_text)
    compact = re.sub(r"[\s、。・,.:：/|()（）%％]", "", full_text)
    digits_only = bool(compact) and len(compact) <= 6 and bool(re.fullmatch(r"[0-9０-９]+", compact))

    # 1 文字の英字（「n秒」の n など）は数を表す変数とみなして除く
    spacing = sorted({m for m in RE_JA_THEN_EN.findall(full_text) + RE_EN_THEN_JA.findall(full_text)
                      if len(re.sub(rf"[{JA}]", "", m)) > 1})

    page_area = page.rect.get_area()
    images, backgrounds = [], 0
    for info in page.get_image_info():
        ratio = (pymupdf.Rect(info["bbox"]) & page.rect).get_area() / page_area
        if ratio >= 0.95:
            backgrounds += 1  # 全面の背景画像は図として数えない
        else:
            images.append(ratio)

    return {
        "page": index + 1,
        "heading_candidate": heading,
        "text": full_text,
        "chars": chars,
        "max_pt": max((s["pt"] for s in spans), default=None),
        "min_pt": min((s["pt"] for s in spans), default=None),
        "fonts": sorted({s["font"] for s in spans}),
        "text_colors": sorted({s["color"] for s in spans}),
        "palette": page_palette(pix),
        "images": len(images),
        "image_area_ratio": round(min(sum(images), 1.0), 2),
        "background_images": backgrounds,
        "below_body_min": [{"text": s["text"][:40], "pt": s["pt"]} for s in small_body],
        "below_note_min": [{"text": s["text"][:40], "pt": s["pt"]} for s in small_note],
        "low_contrast": [{"text": s["text"][:40], "pt": s["pt"], "fg": s["color"], "bg": s["bg"],
                          "ratio": s["contrast"]} for s in low_contrast],
        "spacing_candidates": spacing,
        "digits_only": digits_only,
        "thanks": bool(RE_THANKS.search(full_text)),
    }


def collapse_repeated(pages):
    """ヘッダー・フッターのように半数以上のページに出る小さい文字は、ページごとの指摘から外して一度だけ報告する。"""
    if len(pages) < 3:
        return []
    keys = ("below_body_min", "below_note_min", "low_contrast")
    counter = collections.Counter()
    for p in pages:
        counter.update({(s["text"], s["pt"]) for k in keys for s in p[k]})
    common = {key for key, n in counter.items() if n >= max(3, len(pages) / 2)}
    for p in pages:
        for k in keys:
            p[k] = [s for s in p[k] if (s["text"], s["pt"]) not in common]
    return [{"text": t, "pt": pt, "pages": counter[(t, pt)]} for t, pt in sorted(common)]


def render_images(doc, out_dir, offset=0):
    (out_dir / "thumbs").mkdir(parents=True, exist_ok=True)
    (out_dir / "full").mkdir(parents=True, exist_ok=True)
    (out_dir / "sheets").mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(doc):
        for sub, w in (("thumbs", THUMB_WIDTH), ("full", FULL_WIDTH)):
            z = w / page.rect.width
            page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False).save(out_dir / sub / f"p{i + 1 + offset:02d}.png")

    per_sheet = SHEET_COLS * SHEET_ROWS
    aspect = doc[0].rect.height / doc[0].rect.width
    cell_w, cell_h = THUMB_WIDTH, THUMB_WIDTH * aspect
    sheets = []
    for start in range(0, len(doc), per_sheet):
        sheet = pymupdf.open()
        sp = sheet.new_page(width=SHEET_COLS * cell_w, height=SHEET_ROWS * cell_h)
        for j, i in enumerate(range(start, min(start + per_sheet, len(doc)))):
            r = pymupdf.Rect((j % SHEET_COLS) * cell_w, (j // SHEET_COLS) * cell_h,
                             (j % SHEET_COLS + 1) * cell_w, (j // SHEET_COLS + 1) * cell_h)
            sp.show_pdf_page(r, doc, i)
            sp.draw_rect(r, color=(0.6, 0.6, 0.6), width=0.5)
            sp.insert_text((r.x0 + 4, r.y0 + 12), str(i + 1 + offset), fontsize=10, color=(1, 0, 0))
        name = f"sheet{start // per_sheet + 1}.png"
        sp.get_pixmap(dpi=72, alpha=False).save(out_dir / "sheets" / name)
        sheets.append(f"sheets/{name} (p{start + 1 + offset}-{min(start + per_sheet, len(doc)) + offset})")
    return sheets


def write_summary(result, out_dir):
    pages = result["pages"]
    lines = [f"# 計測結果: {result['source']}", ""]
    if result.get("page_range"):
        lines.append(f"- 枚数: {len(pages)}（全 {result['total_pages']} 枚のうち p{result['page_range'][0]}-{result['page_range'][1]}）")
    else:
        lines.append(f"- 枚数: {len(pages)}")
    lines.append(f"- スライド幅: {result['page_width']} pt（PowerPoint 換算倍率 ×{result['scale_to_pptx']}）")
    if result.get("minutes"):
        lines.append(f"- 発表時間: {result['minutes']} 分 → {result['sec_per_slide']} 秒/枚"
                     f"（目安 20〜30 秒/枚 = {result['slides_range'][0]}〜{result['slides_range'][1]} 枚）")
    named = [(f, n) for f, n in result["fonts"] if not f.startswith("Type3")]
    if len(named) < len(result["fonts"]):
        lines.append("- 使用フォント: PDF にフォント名が残っていない文字あり（Type3）。目視で確認すること")
    if named:
        lines.append(f"- フォント名が取れた文字: {', '.join(f'{f} ({n}字)' for f, n in named)}")
    if result["env_dependent_fonts"]:
        lines.append(f"- 環境依存の可能性があるフォント: {', '.join(result['env_dependent_fonts'])}")
    if result.get("declared_fonts"):
        decl = []
        for f in result["declared_fonts"]:
            mark = "" if f["installed"] else "（この環境に未インストール。代替フォントで描画）"
            decl.append(f["font"] + mark)
        lines.append(f"- ソースで指定されたフォント: {', '.join(decl)}")
    if result["repeated_small_text"]:
        lines.append("- 多くのページに共通する小さい文字（ヘッダー・フッターなど）: " + " / ".join(
            f"「{r['text']}」{r['pt']}pt ×{r['pages']}" for r in result["repeated_small_text"]))
    lines.append(f"- 文字色: {', '.join(f'{c} ({n}字)' for c, n in result['text_colors'])}")
    lines.append(f"- 画像: {', '.join(result['sheets'])}（サムネイル一覧）")
    lines.append("")
    lines.append("## 見出しの流れ")
    lines.append("")
    for p in pages:
        h = p["heading_candidate"] or (p["text"].split("\n")[0] if p["text"] else "（文字なし）")
        lines.append(f"{p['page']}. {h[:60]}")
    lines.append("")
    lines.append("## ページごとの機械検出")
    lines.append("")
    for p in pages:
        flags = []
        if p["below_note_min"]:
            flags.append("18pt 未満: " + " / ".join(f"「{s['text']}」{s['pt']}pt" for s in p["below_note_min"][:4]))
        if p["below_body_min"]:
            flags.append("24pt 未満: " + " / ".join(f"「{s['text']}」{s['pt']}pt" for s in p["below_body_min"][:4]))
        if p["low_contrast"]:
            flags.append("低コントラスト: " + " / ".join(
                f"「{s['text']}」{s['fg']} on {s['bg']} ({s['ratio']})" for s in p["low_contrast"][:3]))
        if p["spacing_candidates"]:
            flags.append("半角スペース候補: " + ", ".join(p["spacing_candidates"][:8]))
        if p["digits_only"]:
            flags.append("数字だけのスライド")
        if p["thanks"] and p["page"] == len(pages):
            flags.append("「ありがとうございました」系の文言")
        if p.get("notes"):
            flags.append("発表者ノートあり")
        info = f"{p['chars']}字, 最大 {p['max_pt']}pt, 画像 {p['images']} 枚 (面積 {int(p['image_area_ratio'] * 100)}%)"
        lines.append(f"- p{p['page']}: {info}")
        for f in flags:
            lines.append(f"  - {f}")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("out_dir")
    ap.add_argument("--minutes", type=float, help="発表時間（分）")
    ap.add_argument("--pages", help="評価するページ範囲（例: 1-60）。番号は元のスライド番号のまま報告する")
    args = ap.parse_args()

    src = Path(args.input).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    notes, declared = None, None
    if src.suffix.lower() == ".md":
        if not has_japanese_font():
            sys.exit("日本語フォントが見つからないため、Marp を正しく描画できません。"
                     "日本語フォントを入れるか（例: fonts-noto-cjk）、Marp で書き出した PDF を指定してください。")
        md_text = src.read_text(encoding="utf-8")
        notes = marp_notes(md_text)
        declared = check_installed(marp_declared_fonts(md_text))
        pdf = marp_to_pdf(src, out_dir)
    elif src.suffix.lower() == ".pptx":
        notes, fonts = pptx_info(src)
        declared = check_installed(fonts) if fonts else None
        pdf = pptx_to_pdf(src, out_dir)
    elif src.suffix.lower() == ".pdf":
        pdf = src
    else:
        sys.exit("PDF・Marp の Markdown・pptx のいずれかを指定してください（Google Slides は PDF に書き出してから）")

    doc = pymupdf.open(pdf)
    total_pages = len(doc)
    first = 1
    if args.pages:
        a, _, b = args.pages.partition("-")
        first, last = int(a), int(b or a)
        doc.select(list(range(first - 1, min(last, total_pages))))
    offset = first - 1
    pages = [analyze_page(page, i + offset) for i, page in enumerate(doc)]
    repeated = collapse_repeated(pages)
    if notes:
        for p in pages:
            if p["page"] - 1 < len(notes):
                p["notes"] = notes[p["page"] - 1]

    font_count, color_count = collections.Counter(), collections.Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for s in line["spans"]:
                    n = len(s["text"].strip())
                    if n:
                        font_count[clean_font(s["font"])] += n
                        color_count[hexcolor(int_to_rgb(s["color"]))] += n

    width = doc[0].rect.width
    result = {
        "source": str(src),
        "pdf": str(pdf),
        "page_width": round(width, 1),
        "scale_to_pptx": round(BASE_WIDTH / width, 3),
        "aspect": round(width / doc[0].rect.height, 3),
        "fonts": font_count.most_common(),
        "env_dependent_fonts": sorted({f for f in font_count
                                       if any(e.lower() in f.lower() for e in ENV_DEPENDENT_FONTS)}),
        "text_colors": color_count.most_common(8),
        "repeated_small_text": repeated,
        "declared_fonts": declared,
        "page_range": [first, first + len(pages) - 1] if args.pages else None,
        "total_pages": total_pages,
        "pages": pages,
    }
    if args.minutes:
        sec = args.minutes * 60
        result.update(minutes=args.minutes, sec_per_slide=round(sec / len(pages), 1),
                      slides_range=[int(sec // 30), int(sec // 20)])
    result["sheets"] = render_images(doc, out_dir, offset)

    (out_dir / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    write_summary(result, out_dir)
    print(out_dir / "summary.md")


if __name__ == "__main__":
    main()
