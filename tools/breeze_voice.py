#!/usr/bin/env python3
"""選配：在 BreezeBlue 官方 API 用文字描述「設計」一個主播聲音（只做一次）。要 .env 的 BREEZE_API_KEY（付費，試聽也會扣點）。
python3 tools/breeze_voice.py design          # 用下面的描述出 3 個試聽 → work/voice-previews/1–3.mp3
python3 tools/breeze_voice.py design calm     # 冷靜版 3 個 → work/voice-previews-calm/
python3 tools/breeze_voice.py save <1|2|3> [calm]   # 存成正式聲音（佔一個 voice slot），印出要寫進 .env 的 BREEZE_VOICE_ID
聲音描述與試聽稿可以在 config.json 的 breeze-api 加 voice_description、voice_description_calm、preview_text 來改。"""
import base64, json, sys, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CFG, ROOT, env

OUT = ROOT / "work/voice-previews"
API = "https://api.breeze.blue/v1"
B = CFG.get("breeze-api", {})
DESC = B.get("voice_description", "一位三十歲左右的台灣女性主播，台灣口音，聲音明亮俐落，咬字清楚，語速中等偏快，自信、有條理，帶一點溫度。")
DESC_CALM = B.get("voice_description_calm", "一位三十五歲左右的台灣女性資深新聞主播，台灣口音，聲音低沉溫潤、冷靜沉穩，語速中等、不疾不徐，語氣平穩客觀。")
TEXT = B.get("preview_text", "早安，歡迎收看今天的節目。這是一段試聽，用來挑選主播的聲音。")


def key():
    k = env("BREEZE_API_KEY")
    if not k:
        sys.exit("沒有 BREEZE_API_KEY：到 BreezeBlue 官網訂閱後建一把 key，寫進 .env")
    return k


def call(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body, ensure_ascii=False).encode(),
                                 headers={"xi-api-key": key(), "content-type": "application/json", "user-agent": "daily-video-pipeline/1.0"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        sys.exit(f"{e.code}: {e.read()[:400]!r}")


def main():
    if sys.argv[1:2] == ["design"]:
        desc = DESC_CALM if sys.argv[2:3] == ["calm"] else DESC
        d = call("/voice-previews/design", {"voice_description": desc, "text": TEXT, "language_code": "zh", "guidance_scale": 4.0, "preview_count": 3})
        global OUT
        if sys.argv[2:3] == ["calm"]:
            OUT = OUT.parent / "voice-previews-calm"
        OUT.mkdir(parents=True, exist_ok=True)
        ids = []
        for i, p in enumerate(d["previews"], 1):
            (OUT / f"{i}.mp3").write_bytes(base64.b64decode(p["audio_base_64"]))
            ids.append(p["generated_voice_id"])
        (OUT / "ids.json").write_text(json.dumps(ids))
        print("試聽：", *[OUT / f"{i}.mp3" for i in range(1, len(ids) + 1)], sep="\n")
    elif sys.argv[1:2] == ["save"]:
        src = OUT.parent / "voice-previews-calm" if sys.argv[3:4] == ["calm"] else OUT
        gid = json.loads((src / "ids.json").read_text())[int(sys.argv[2]) - 1]
        v = call(f"/voice-previews/{gid}/save", {"voice_name": B.get("voice_name", "daily-video"), "voice_description": DESC_CALM if sys.argv[3:4] == ["calm"] else DESC, "language_code": "zh"})
        print("已存。把下面這行寫進 .env，再把 config.json 的 engine 改成 breeze-api：\nBREEZE_VOICE_ID=" + v["voice_id"])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
