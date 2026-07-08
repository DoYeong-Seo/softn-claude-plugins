#!/usr/bin/env python3
"""
QuizN-planning-flow — Flowchart exporter
=========================================
HTML 또는 SVG 흐름도를 PNG(FHD·QHD·4K)·PDF로 일괄 변환한다.
해상도 정책(디자인 D2): 짧은 변 >= 1080px(FHD 최소), 최대 2160px(4K).

백엔드 자동 탐지 우선순위:
  1) Playwright (HTML/SVG 모두, CSS 변수·다크/라이트·테마 정확 렌더 + 벡터 PDF)  ← 권장
  2) rsvg-convert (SVG만, PNG/PDF)
  3) cairosvg   (SVG만, PNG/PDF)

설치 예:
  pip install playwright --break-system-packages && python -m playwright install chromium
  # 또는  apt-get install librsvg2-bin   /   pip install cairosvg --break-system-packages

사용 예:
  python export_flowchart.py flow.html --out exports --fhd --4k --pdf --mode both --theme show
  python export_flowchart.py flow.svg  --out exports --fhd --qhd --4k
"""
import argparse, os, sys, shutil, subprocess

PRESETS = {"fhd": 1920, "qhd": 2560, "4k": 3840}   # width 기준, 16:9
VB_W, VB_H = 1920, 1080


def out_name(stem, tag, theme, mode, ext):
    parts = [stem, tag]
    if theme: parts.append(theme)
    if mode:  parts.append(mode)
    return "_".join(parts) + "." + ext


def ensure_dirs(base):
    for d in ("png-fhd", "png-qhd", "png-4k", "pdf"):
        os.makedirs(os.path.join(base, d), exist_ok=True)


def sub_for(tag):
    return {"fhd": "png-fhd", "qhd": "png-qhd", "4k": "png-4k"}[tag]


# ---------------- Playwright backend (preferred) ----------------
def export_playwright(src, out, widths, want_pdf, modes, theme, stem):
    from playwright.sync_api import sync_playwright
    is_html = src.lower().endswith((".html", ".htm"))
    url = "file://" + os.path.abspath(src)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for mode in modes:
            scale_done = set()
            for tag in widths:
                width = PRESETS[tag]
                scale = width / VB_W
                page = browser.new_page(viewport={"width": VB_W, "height": VB_H},
                                        device_scale_factor=scale)
                page.goto(url)
                if is_html:
                    page.evaluate("(m)=>{document.body.dataset.mode=m;}", mode)
                    if theme:
                        page.evaluate("(t)=>{document.body.dataset.theme=t;}", theme)
                    page.wait_for_timeout(300)
                    el = page.query_selector("#flow") or page.query_selector("svg")
                    target = el if el else page
                else:
                    target = page
                png_path = os.path.join(out, sub_for(tag),
                                        out_name(stem, tag, theme, mode, "png"))
                (target if hasattr(target, "screenshot") else page).screenshot(path=png_path)
                print("PNG  ->", png_path)
                page.close()
            if want_pdf:
                page = page = browser.new_page()
                page.goto(url)
                if is_html:
                    page.evaluate("(m)=>{document.body.dataset.mode=m;}", mode)
                    if theme: page.evaluate("(t)=>{document.body.dataset.theme=t;}", theme)
                    page.wait_for_timeout(300)
                pdf_path = os.path.join(out, "pdf", out_name(stem, "vec", theme, mode, "pdf"))
                page.pdf(path=pdf_path, landscape=True, print_background=True,
                         width="420mm", height="237mm")  # ~A3 가로 16:9
                print("PDF  ->", pdf_path)
                page.close()
        browser.close()


# ---------------- SVG-only backends ----------------
def export_rsvg(src, out, widths, want_pdf, theme, mode, stem):
    for tag in widths:
        w = PRESETS[tag]; h = round(w * VB_H / VB_W)
        dst = os.path.join(out, sub_for(tag), out_name(stem, tag, theme, mode, "png"))
        subprocess.check_call(["rsvg-convert", "-w", str(w), "-h", str(h), "-o", dst, src])
        print("PNG  ->", dst)
    if want_pdf:
        dst = os.path.join(out, "pdf", out_name(stem, "vec", theme, mode, "pdf"))
        subprocess.check_call(["rsvg-convert", "-f", "pdf", "-o", dst, src])
        print("PDF  ->", dst)


def export_cairosvg(src, out, widths, want_pdf, theme, mode, stem):
    import cairosvg
    data = open(src, "rb").read()
    for tag in widths:
        w = PRESETS[tag]; h = round(w * VB_H / VB_W)
        dst = os.path.join(out, sub_for(tag), out_name(stem, tag, theme, mode, "png"))
        cairosvg.svg2png(bytestring=data, write_to=dst, output_width=w, output_height=h)
        print("PNG  ->", dst)
    if want_pdf:
        dst = os.path.join(out, "pdf", out_name(stem, "vec", theme, mode, "pdf"))
        cairosvg.svg2pdf(bytestring=data, write_to=dst)
        print("PDF  ->", dst)


def have(mod=None, cmd=None):
    if cmd: return shutil.which(cmd) is not None
    try:
        __import__(mod); return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="QuizN-planning-flow flowchart exporter")
    ap.add_argument("src", help="입력 HTML 또는 SVG 경로")
    ap.add_argument("--out", default="exports", help="출력 폴더 (기본 exports/)")
    ap.add_argument("--fhd", action="store_true", help="1920×1080 (최소 보장)")
    ap.add_argument("--qhd", action="store_true", help="2560×1440")
    ap.add_argument("--4k", dest="k4", action="store_true", help="3840×2160 (최대)")
    ap.add_argument("--pdf", action="store_true", help="PDF 생성")
    ap.add_argument("--mode", choices=["light", "dark", "both"], default="light")
    ap.add_argument("--theme", choices=["show", "board", "video", "class"], default=None)
    args = ap.parse_args()

    widths = [t for t, on in (("fhd", args.fhd), ("qhd", args.qhd), ("4k", args.k4)) if on]
    if not widths:
        widths = ["fhd"]  # 기본은 최소 보장(FHD)
    modes = ["light", "dark"] if args.mode == "both" else [args.mode]
    stem = os.path.splitext(os.path.basename(args.src))[0]
    ensure_dirs(args.out)
    is_html = args.src.lower().endswith((".html", ".htm"))

    if have(mod="playwright"):
        export_playwright(args.src, args.out, widths, args.pdf, modes, args.theme, stem)
    elif not is_html and have(cmd="rsvg-convert"):
        for m in modes:
            export_rsvg(args.src, args.out, widths, args.pdf, args.theme, m, stem)
    elif not is_html and have(mod="cairosvg"):
        for m in modes:
            export_cairosvg(args.src, args.out, widths, args.pdf, args.theme, m, stem)
    else:
        sys.exit(
            "내보내기 백엔드를 찾지 못했습니다.\n"
            "  HTML 입력: pip install playwright --break-system-packages && "
            "python -m playwright install chromium\n"
            "  SVG 입력 : apt-get install librsvg2-bin  또는  "
            "pip install cairosvg --break-system-packages\n"
            "또는 HTML 템플릿의 내장 내보내기 버튼(SVG/PNG/PDF)을 사용하세요."
        )
    print("완료. 출력 폴더:", os.path.abspath(args.out))


if __name__ == "__main__":
    main()
