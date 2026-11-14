#!/usr/bin/env python3
"""選配（config.json 的 whisper.enabled）：念得對不對打分——Whisper 聽寫 → 跟原文比「拼音＋聲調」（1.0＝全對）。
make_day.py 的重念機制用它挑最好的一版，整支旁白的 QC 也用它；tts_check.py 用這裡的 py/diff 逐句檢查。
要先 pip install openai-whisper pypinyin opencc-python-reimplemented（第一次會下載 Whisper 模型，約 1.6 GB）。
echo '[{"text": "要念的字", "wavs": ["a.wav", "b.wav"]}]' | python3 tools/tts_score.py  → [[分數, 聽到, 差異], …] 每個 wav 一筆
只適用中文旁白（比的是漢語拼音）。"""
import difflib, json, re, sys
from pathlib import Path

import opencc
from pypinyin import Style, lazy_pinyin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_day as md
from common import CFG

WH = CFG.get("whisper", {})
t2s = opencc.OpenCC("t2s")


# 比「拼音＋聲調」不比字：Whisper 常寫成同音字（理事→李氏、初值→出職），那不是念錯
def py(s):
    s = md.say_numbers(t2s.convert(s)).replace("日", "号")          # Whisper 寫 11月3日，稿子念「號」
    return lazy_pinyin(re.sub(r"[^一-鿿]", "", s), style=Style.TONE3, neutral_tone_with_five=True)


def diff(a, b):
    sm = difflib.SequenceMatcher(None, a, b)
    return sm.ratio(), [f"{' '.join(a[i1:i2])}→{' '.join(b[j1:j2]) or '（沒念）'}" for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]


_model = None
def hear(audio):
    global _model
    import whisper
    if _model is None:
        _model = whisper.load_model(WH.get("model", "large-v3-turbo"))
    return _model.transcribe(audio, language=WH.get("language", "zh"), fp16=False)["text"].strip()      # 不給 initial_prompt：給了會漏念日期


if __name__ == "__main__":
    out = []
    for job in json.load(sys.stdin):
        want = py(job["text"])
        out.append([[round(s, 3), got, d] for got in map(hear, job["wavs"]) for s, d in [diff(want, py(got))]])
    print(json.dumps(out, ensure_ascii=False))
