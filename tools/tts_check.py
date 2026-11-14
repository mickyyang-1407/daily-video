#!/usr/bin/env python3
"""選配：逐句聽寫檢查——把旁白每一句切出來給 Whisper 聽，跟講稿比，列出念錯的句子（整份的平均分數看不出哪一句錯）。
python3 tools/tts_check.py work/2026-11-13 [--min 0.9] [--engine breeze-api] [--reuse]
要裝的套件同 tts_score.py。"""
import json, sys, wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tts_score as ts
md, py, diff = ts.md, ts.py, ts.diff

work = Path(sys.argv[1]); thr = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 0.9
engine = sys.argv[sys.argv.index("--engine") + 1] if "--engine" in sys.argv else md.CFG["engine"]   # 跟念的版本比（say_as 換過字）
cues = json.loads((work / "props.json").read_text())["ep"]["cues"]
with wave.open(str(work / "vo.wav")) as w:
    sr = w.getframerate(); pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
if sr != 16000:      # whisper 要 16 kHz
    pcm = np.interp(np.arange(0, len(pcm), sr / 16000), np.arange(len(pcm)), pcm).astype(np.float32)
old = {r["i"]: r["got"] for r in json.loads((work / "tts_check.json").read_text())} if "--reuse" in sys.argv else {}
bad, rows = [], []
for i, c in enumerate(cues):
    if i in old:
        got = old[i]
    else:
        seg = pcm[int(c["t0"] * 16000): int(c["t1"] * 16000) + 1600]
        got = ts.hear(seg)
    sim, wrong = diff(py(md.speakable(c["text"], engine)), py(got))
    rows.append({"i": i, "sim": round(sim, 3), "want": c["text"], "got": got, "diff": wrong})
    if sim < thr:
        bad.append(rows[-1])
(work / "tts_check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
print(f"{len(cues)} 句，低於 {thr}：{len(bad)} 句；平均 {np.mean([r['sim'] for r in rows]):.3f}")
for r in bad:
    print(f"#{r['i']} {r['sim']}｜{r['want']}\n  聽：{r['got']}\n  差：{'；'.join(r['diff'])}")
