#!/usr/bin/env python3
"""下載 Noto Sans CJK TC（思源黑體繁中，SIL Open Font License 1.1）四個字重到 remotion/public/fonts/，約 68 MB。
字型檔不放進 repo（太大）；沒下載也能做片，畫面會改用系統的中文字型（macOS 是蘋方）。
python3 tools/get_fonts.py"""
import sys, urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "remotion/public/fonts"
BASE = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/TraditionalChinese/"

DEST.mkdir(parents=True, exist_ok=True)
for w in ("Regular", "Medium", "Bold", "Black"):
    name = f"NotoSansCJKtc-{w}.otf"
    out = DEST / name
    if out.exists() and out.stat().st_size > 5_000_000:
        print("已經有", name); continue
    print("下載", name, "…", flush=True)
    try:
        data = urllib.request.urlopen(BASE + name, timeout=300).read()
    except Exception as e:
        sys.exit(f"下載失敗（{e}）。可以手動到 https://github.com/notofonts/noto-cjk 下載 {name} 放進 {DEST}")
    if data[:4] != b"OTTO":
        sys.exit(f"{name} 下載到的不是字型檔，請手動下載")
    out.write_bytes(data)
print("完成：", DEST)
