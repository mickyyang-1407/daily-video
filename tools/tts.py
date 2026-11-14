"""配音引擎。每個引擎是一個函式 fn(items)，items = [(要念的字, 輸出 wav 路徑)]，輸出一律 44.1 kHz 單聲道 16-bit。

免費（不用金鑰）
  say        macOS 內建語音（預設）。聲音在 config.json 的 say.voice，`say -v '?'` 可以列出這台 Mac 有哪些
  edge       edge-tts 套件（pip install edge-tts），用微軟 Edge「大聲朗讀」的線上語音；非官方介面，可能隨時失效
付費（金鑰放 .env）
  breeze-api BreezeBlue 官方 API：BREEZE_API_KEY、BREEZE_VOICE_ID
  minimax    MiniMax t2a_v2：MINIMAX_API_KEY
  gemini     Google Gemini TTS：GEMINI_API_KEY
要加新的引擎：寫一個 fn(items)，登記到最下面的 ENGINES。"""
import base64, json, shutil, subprocess, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import CFG, env, log

UA = "daily-video-pipeline/1.0"


def pmap(fn, items, n):
    with ThreadPoolExecutor(max(1, min(n, len(items)))) as ex:
        for _ in ex.map(fn, items):
            pass


def to44(src, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", "aresample=44100:filter_size=64,silenceremove=start_periods=1:start_threshold=-50dB",
                    "-ac", "1", "-c:a", "pcm_s16le", str(dst)], check=True)


def need_key(name, engine):
    k = env(name)
    if not k:
        raise SystemExit(f"{engine} 需要 {name}（寫在 .env）")
    return k


# ───────────── 免費 ─────────────
def tts_say(items):
    if not shutil.which("say"):
        raise SystemExit("say 只有 macOS 有；其他系統請把 engine 改成 edge 或付費引擎")
    c = CFG.get("say", {})

    def one(it):
        text, out = it
        tmp = out.with_suffix(".aiff")
        cmd = ["say", "-o", str(tmp)]
        if c.get("voice"):
            cmd += ["-v", c["voice"]]
        if c.get("rate"):
            cmd += ["-r", str(c["rate"])]
        r = subprocess.run(cmd + [text], capture_output=True, text=True)
        if r.returncode or not tmp.exists():
            raise SystemExit(f"say 失敗：{r.stderr.strip()[:200]}（聲音 {c.get('voice')} 有裝嗎？系統設定 → 輔助使用 → 語音內容 → 系統聲音）")
        to44(tmp, out); tmp.unlink()

    pmap(one, items, c.get("parallel", 4))


def tts_edge(items):
    try:
        import edge_tts
    except ImportError:
        raise SystemExit("edge 引擎要先 pip install edge-tts")
    import asyncio
    c = CFG.get("edge", {})

    def one(it):
        text, out = it
        tmp = out.with_suffix(".mp3")
        asyncio.run(edge_tts.Communicate(text, c.get("voice", "zh-TW-HsiaoChenNeural"), rate=c.get("rate", "+0%")).save(str(tmp)))
        to44(tmp, out); tmp.unlink()

    pmap(one, items, c.get("parallel", 4))


# ───────────── 付費 ─────────────
def _post(req, engine, tries=6, retry_codes=(429, 500, 502, 503)):
    for i in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After") or 10 * (i + 1))
            if e.code not in retry_codes or i == tries - 1 or wait > 120:     # 額度用完就直接報錯，不要傻等幾小時
                raise SystemExit(f"{engine} {e.code}: {e.read()[:300]!r}")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as e:
            if i == tries - 1:
                raise SystemExit(f"{engine} 連線失敗：{e}")
            time.sleep(5 * (i + 1))


def tts_breeze_api(items):
    """BreezeBlue 官方 API。聲音用 tools/breeze_voice.py 設計並存好，voice id 寫進 .env 的 BREEZE_VOICE_ID。"""
    key, vid, b = need_key("BREEZE_API_KEY", "breeze-api"), need_key("BREEZE_VOICE_ID", "breeze-api"), CFG.get("breeze-api", {})

    def one(it):
        text, out = it
        body = {"text": text, "model_id": b.get("model", "breeze-tts-2"), "language_code": b.get("language_code", "zh")}
        if b.get("instruct"):
            body |= {"instructions": b["instruct"], "voice_settings": {"guidance_scale": 4.0}}
        req = urllib.request.Request(f"https://api.breeze.blue/v1/text-to-speech/{vid}?output_format=wav_24000",
                                     data=json.dumps(body, ensure_ascii=False).encode(), headers={"xi-api-key": key, "content-type": "application/json", "user-agent": UA})
        tmp = out.with_suffix(".raw.wav"); tmp.write_bytes(_post(req, "breeze-api"))
        to44(tmp, out); tmp.unlink()

    pmap(one, items, b.get("parallel", 2))      # 同時幾句受方案的併發上限限制


def tts_minimax(items):
    key, m = need_key("MINIMAX_API_KEY", "minimax"), CFG.get("minimax", {})
    url = m.get("url", "https://api.minimax.io/v1/t2a_v2")      # 中國站的金鑰改成 https://api.minimaxi.com/v1/t2a_v2

    def one(it):
        text, out = it
        body = {"model": m.get("model", "speech-2.8-hd"), "text": text, "stream": False,
                "voice_setting": {"voice_id": m.get("voice", "Chinese (Mandarin)_News_Anchor"), "speed": m.get("speed", 1.0), "vol": 1, "pitch": 0,
                                  **({"emotion": m["emotion"]} if m.get("emotion") else {})},
                "audio_setting": {"sample_rate": 44100, "format": "wav", "channel": 1}}
        if m.get("language_boost"):
            body["language_boost"] = m["language_boost"]
        if m.get("pronunciation"):                # 指定讀音，例："重押/(zhong4)(ya1)"
            body["pronunciation_dict"] = {"tone": m["pronunciation"]}
        req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        for i in range(8):
            d = json.loads(_post(req, "minimax", tries=8))
            code = d.get("base_resp", {}).get("status_code")
            if code in (1002, 1039) and i < 7:    # 每分鐘次數／字數上限：HTTP 200 回這兩個碼
                time.sleep(min(60, 5 * 2 ** i)); continue
            if code != 0:
                raise SystemExit(f"minimax {d.get('base_resp')}")
            break
        tmp = out.with_suffix(".raw.wav"); tmp.write_bytes(bytes.fromhex(d["data"]["audio"]))
        to44(tmp, out); tmp.unlink()

    pmap(one, items, m.get("parallel", 6))


def tts_gemini(items):
    key, g = need_key("GEMINI_API_KEY", "gemini"), CFG.get("gemini", {})

    def one(it):
        text, out = it
        body = {"model": g.get("model", "gemini-3.8-flash-tts"), "input": [{"type": "user_input", "content": [{"type": "text", "text": text,
                "annotations": [{"type": "speech_metadata", "style": g.get("style", "")}]}]}],
                "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": g.get("voice", "Zephyr")}]}}
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/interactions", data=json.dumps(body).encode(),
                                     headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        d = json.loads(_post(req, "gemini", tries=8, retry_codes=(429, 500, 503)))
        c = [x for s in d["steps"] for x in s.get("content", []) if x.get("type") == "audio"][0]
        tmp = out.with_suffix(".raw.wav"); tmp.write_bytes(base64.b64decode(c["data"]))
        to44(tmp, out); tmp.unlink()

    pmap(one, items, g.get("parallel", 2))


ENGINES = {"say": tts_say, "edge": tts_edge, "breeze-api": tts_breeze_api, "minimax": tts_minimax, "gemini": tts_gemini}


def voice_key(engine):
    """換聲音／改讀音表就不吃舊的快取"""
    c = dict(CFG.get(engine, {}))
    if engine == "breeze-api":
        c["voice_id"] = env("BREEZE_VOICE_ID")
    return json.dumps(c, sort_keys=True, ensure_ascii=False)


def synth(engine, items):
    if engine not in ENGINES:
        raise SystemExit(f"沒有 {engine} 這個配音引擎，可用的有：{', '.join(ENGINES)}")
    log(f"TTS {engine}：新合成 {len(items)} 句")
    ENGINES[engine](items)
