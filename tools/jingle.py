#!/usr/bin/env python3
"""選配：用 ElevenLabs 音效 API 生成自己的片頭／片尾音效（要 .env 的 ELEVENLABS_API_KEY，付費）。
python3 tools/jingle.py remotion/public/brand/intro.mp3 4 "short bright news sting, one clear hit at 0.6 seconds"
python3 tools/jingle.py remotion/public/brand/outro.mp3 5 "warm short outro sting"
生成的音效能不能商用、能不能再散布，以你的 ElevenLabs 方案條款為準；這個 repo 不附任何音效檔。
放好之後在 config.json 填：
  "jingle": {"intro": "brand/intro.mp3", "outro": "brand/outro.mp3", "intro_hit": 0.6, "outro_hit": 1.2}
（intro_hit／outro_hit＝音效重拍在第幾秒，片頭印章、片尾鈴鐺會對準它。用自己錄的或其他來源的音效也一樣放這兩個檔。）"""
import json, sys, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import env

if len(sys.argv) != 4:
    sys.exit(__doc__)
out, sec, text = sys.argv[1], float(sys.argv[2]), sys.argv[3]
key = env("ELEVENLABS_API_KEY")
if not key:
    sys.exit("沒有 ELEVENLABS_API_KEY（寫在 .env）")
req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_192",
                             data=json.dumps({"text": text, "duration_seconds": sec, "prompt_influence": 0.6}).encode(),
                             headers={"xi-api-key": key, "Content-Type": "application/json", "user-agent": "daily-video-pipeline/1.0"})
try:
    Path(out).write_bytes(urllib.request.urlopen(req, timeout=180).read()); print(out)
except urllib.error.HTTPError as e:
    sys.exit(f"{e.code}: {e.read()[:300]!r}")
