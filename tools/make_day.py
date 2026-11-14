#!/usr/bin/env python3
"""一份講稿 → 一支影片。
讀 episodes/<日期>/script.md → 同資料夾 video.mp4、thumbnail.jpg、titles.txt、description.md、tags.txt、captions.srt、report.json
--weekly 讀同資料夾 weekly.md → video-weekly.mp4、thumbnail-weekly.jpg…（不蓋掉每日的檔）

python3 tools/make_day.py 2026-11-13 [--engine say|edge|breeze-api|minimax|gemini] [--dir <資料夾>] [--weekly]

- 主題（頻道名、段落規則、圖卡文字、要不要抓市場資料）在 themes/<主題>/theme.json，config.json 的 "theme" 決定用哪個
- 標題含「不公開」這類字（theme.sections.private）的段落整段不念、不進畫面、不進說明欄
- 主題有開每日數據（data.provider = yfinance）時，數據卡與走勢圖一律用抓到的真實數字；講稿裡的數字只念、不拿來畫圖
"""
import argparse, hashlib, json, re, subprocess, sys, time, wave
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CFG, ROOT, THEME, episodes_dir, log
import tts

W, H, SR = 1920, 1080, 44100
SEC, TXT, DATA = THEME["sections"], THEME["text"], THEME.get("data", {"provider": "none"})
HAS_MARKET = DATA.get("provider") == "yfinance"
WEEKLY = False                      # --weekly：讀 weekly.md，產出檔名加 -weekly，漲跌改算整週
HEADLINE = ""                       # 片頭頭條（標題候選第一個）
STEPS = {}


def kind_key():
    return "weekly" if WEEKLY else "daily"


def nm(fname):
    """video.mp4 → video-weekly.mp4（每週那支不蓋掉每日的檔）"""
    if not WEEKLY:
        return fname
    stem, _, ext = fname.rpartition(".")
    return f"{stem}-weekly.{ext}"


class step:
    """with step("配音"): … → STEPS["配音"] = 秒數（寫進 report）"""
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.t = time.time()

    def __exit__(self, *exc):
        STEPS[self.name] = round(time.time() - self.t, 1)
        log(f"⏱ {self.name} {STEPS[self.name]} 秒")


def has(title, key):
    return any(k in title for k in SEC.get(key, []))


# ───────────── 講稿 ─────────────
def strip_private(md):
    """標題含 theme.sections.private 任何一個字的整段（到下一個不私人的 # 或 ## 為止，底下的 ### 也算在內）
    不念、不進畫面、不進說明欄、連結也不收。不管它放在稿子哪個位置。"""
    keep, skip = [], False
    for raw in md.splitlines():
        m = re.match(r"^\s*(#{1,3})\s*(.*)", raw)
        if m and (has(m.group(2), "private") or (skip and len(m.group(1)) == 3)):
            skip = True; continue
        if m and len(m.group(1)) <= 2:
            skip = False
        if not skip:
            keep.append(raw)
    return "\n".join(keep)


def parse_script(md):
    """→ (sections[{title, sub?, lines}], 標題候選, 來源連結, 圖表)"""
    md = strip_private(md)
    sources = list(dict.fromkeys(re.findall(r"https?://[^\s)>\]]+", md)))
    sections, titles, cur = [], [], None
    for raw in md.splitlines():
        line = raw.strip()
        m = re.match(r"^(#{1,3})\s*(.+)", line)
        if m:
            head = re.sub(r"[*_`]", "", m.group(2)).strip()
            if len(m.group(1)) == 2:    # 寫手有時會把說明抄進段落標題「## 開場（一到兩句…）」→ 只留「開場」（### 小標裡的括號不動）
                head = re.split(r"[（(]", head)[0].strip() or head
            if len(m.group(1)) == 3 and sections:
                cur = {"title": sections[-1]["title"], "sub": head, "lines": []}
            else:
                cur = {"title": head, "lines": []}
            sections.append(cur)
            continue
        if not line or cur is None or re.match(r"^[-=*_]{3,}$", line):
            continue
        cur["lines"].append(line)
    chart = None
    for s in sections:
        if has(s["title"], "titles"):
            titles = [clean(l) for l in s["lines"] if clean(l)]
        if has(s["title"], "chart"):
            chart = parse_chart(s["lines"])
    sections = [s for s in sections if not (has(s["title"], "titles") or has(s["title"], "sources") or has(s["title"], "chart"))
                and any(clean(l) for l in s["lines"])]
    return sections, titles[:3], sources, chart


def parse_chart(lines):
    """圖表段 → {title, type, unit, points[[標籤, 數值]], source}。只用稿子給的資料點，不補、不猜；格式不對就不畫。
    資料點可以一行一個（「- A：-4.2%」），或寫在同一行用；或、分隔（「資料點：A -4.2；B -10.9」）"""
    c = {"title": "", "type": "bar", "unit": "", "points": [], "source": ""}
    num = r"([+-−]?\d[\d,]*(?:\.\d+)?)\s*(%|億|兆|萬|點|美元|元|人|次|件)?"
    for raw in lines:
        t = re.sub(r"^\s*[-*+•]\s*", "", raw).strip()
        k, _, v = t.partition("：") if "：" in t else t.partition(":")
        k, v = k.strip(), re.split(r"[（(]", v.strip())[0].strip()      # 括號裡的補充說明不算
        if k in ("圖名", "標題", "名稱", "title"):
            c["title"] = v
        elif k in ("類型", "圖表類型", "type"):
            c["type"] = "line" if any(w in v for w in ("折線", "走勢", "line")) else "bar"
        elif k in ("單位", "unit"):
            c["unit"] = v
        elif k in ("來源", "出處", "source"):
            c["source"] = t.partition("：")[2].strip() if "：" in t else t.partition(":")[2].strip()
        elif k in ("資料點", "points") and not v:
            continue
        else:
            items = re.split(r"[；;、]\s*", v) if k in ("資料點", "points") else [t]
            for it in items:
                m = re.match(r"^(.+?)[：:\s]\s*" + num + r"\s*$", it.strip())
                if m:
                    c["points"].append([m.group(1).strip(), float(m.group(2).replace(",", "").replace("−", "-"))])
                    c["unit"] = c["unit"] or (m.group(3) or "")
    return c if c["title"] and len(c["points"]) >= 2 else None


def clean(line):
    """markdown → 念得出來的純文字"""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)          # [文字](連結) → 文字
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s*(?:[-*+•]|\d+[.)、])\s*", "", t)            # 項目符號
    t = re.sub(r"[*_`#>|]", "", t)
    t = re.sub(r"[（(]\s*(?:來源|出處|source)[^）)]*[）)]", "", t, flags=re.I)
    return t.strip()


def sentences(text):
    parts = re.split(r"(?<=[。！？!?；;])", text)
    out = []
    for p in parts:
        p = p.strip()
        while len(p) > 46:                                         # 字幕一行放得下的長度；長句在逗號切
            cut = max((i for i, ch in enumerate(p[:46]) if ch in "，、：:," and not (ch in "：:" and p[i + 1:i + 2].isdigit())), default=-1)   # 23:00 的冒號不能切
            if cut < 12:
                break
            out.append(p[:cut + 1]); p = p[cut + 1:].strip()
        if re.search(r"[\w㐀-鿿]", p):
            out.append(p)
    return out


def speakable(t, engine):
    """念的版本（字幕仍用原文）：theme.say_as 先換字，再把日期、時間、年份、數字轉成中文念法，不交給 TTS 猜"""
    say_as = THEME.get("say_as", {})
    for a, b in {**say_as.get("all", {}), **say_as.get(engine, {})}.items():
        t = t.replace(a, b)
    return say_numbers(t) if THEME.get("speak_numbers", "zh") == "zh" else t


def say_numbers(t):
    D = "零一二三四五六七八九"
    trim = lambda x: x.rstrip("0").rstrip(".") if "." in x else x          # 2.00 → 2、4.50 → 4.5
    # 年份照數字念：1970 年 → 一九七零年
    t = re.sub(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?=\s*年)", lambda m: "".join(D[int(c)] for c in m.group(1)), t)
    # 時間：21:30 → 二十一點三十分、23:00 → 二十三點、00:15 → 零點十五分
    def hm(m):
        h, mi = int(m.group(1)), int(m.group(2))
        return zh_int(h) + "點" + ("" if mi == 0 else ("零" if mi < 10 else "") + zh_int(mi) + "分")
    t = re.sub(r"(?<![\d.])([01]?\d|2[0-4])[:：]([0-5]\d)(?!\d)", hm, t)
    # 「週二 11/3」直接接日期會念成「週二十一月」→ 中間加逗號停頓
    t = re.sub(r"(週[一二三四五六日])\s*(?=(?:1[0-2]|0?[1-9])/\d)", r"\1，", t)
    # 日期：11/3 → 十一月三號
    t = re.sub(r"(?<![\d.])(1[0-2]|0?[1-9])/([12]\d|3[01]|0?[1-9])(?![\d/])", lambda m: zh_int(int(m.group(1))) + "月" + zh_int(int(m.group(2))) + "號", t)
    # 百分比範圍：3.75–4.00% → 百分之三點七五到百分之四
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%?\s*[–—~～-]\s*(\d+(?:\.\d+)?)\s*%", lambda m: "百分之" + zh_num(trim(m.group(1))) + "到百分之" + zh_num(trim(m.group(2))), t)
    # 範圍 A–B → A 到 B（數字或日期之間的 dash）
    t = re.sub(r"(?<=[\d號%])\s*[–—~～-]\s*(?=[\d一二三四五六七八九十])", "到", t)
    # 百分比
    t = re.sub(r"([+-]?)(\d+(?:\.\d+)?)\s*%", lambda m: ("負" if m.group(1) == "-" else "") + "百分之" + zh_num(trim(m.group(2))), t)
    # 其餘數字（含千分位、小數）；後面接量詞的 2 念「兩」
    def num(m):
        x = m.group(1).replace(",", "")
        if x == "2" and re.match(r"\s*(萬|億|兆|千|百|個|位|週|天|年|小時|次|碼|票|倍|檔|家|成)", m.string[m.end():]):
            return "兩"
        return zh_num(trim(x) if "." in x else x)
    t = re.sub(r"(?<![A-Za-z])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)", num, t)
    return t


def zh_num(s):
    d = "零一二三四五六七八九"
    if "." in s:
        i, f = s.split(".")
        return zh_int(int(i)) + "點" + "".join(d[int(c)] for c in f)
    return zh_int(int(s))


def zh_int(n):
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 100:
        return ("" if n // 10 == 1 else d[n // 10]) + "十" + (d[n % 10] if n % 10 else "")
    if n >= 10000:
        hi, lo = divmod(n, 10000)
        return ("兩" if hi == 2 else zh_int(hi)) + "萬" + (("零" if lo < 1000 else "") + zh_small(lo) if lo else "")
    return zh_small(n)


def zh_small(n):
    d, out, zero = "零一二三四五六七八九", "", False
    for v, u in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
        q = n // v % 10
        if q:
            out += ("零" if zero and out else "") + ("兩" if q == 2 and u in "千百" and not out else d[q]) + u; zero = False
        elif out:
            zero = True
    return out or "零"


# ───────────── 配音 ─────────────
def whisper_on():
    return CFG.get("whisper", {}).get("enabled", False)


def score_takes(jobs):
    """[(念的字, [wav…])] → 每句最好那版的 [分數, 聽到, 差異]（tools/tts_score.py：Whisper 聽寫後比拼音＋聲調）"""
    py = CFG.get("whisper", {}).get("python") or sys.executable
    r = subprocess.run([py, str(ROOT / "tools/tts_score.py")], input=json.dumps(
        [{"text": t, "wavs": [str(w) for w in ws]} for t, ws in jobs], ensure_ascii=False), capture_output=True, text=True, timeout=3600)
    if r.returncode:
        log(f"打分失敗，不重念：{r.stderr[-300:]}")
        return [[1.0, "", []] for _ in jobs]
    return [max(rows, key=lambda x: x[0]) for rows in json.loads(r.stdout)]


def retake(engine, items):
    """有些 TTS 沒有指定讀音的欄位、每次念的又不一樣 → 每句給 Whisper 聽、比拼音，沒念對的重念（最多 retakes 次），留分數最高那版。
    config.json 的 <引擎>.retakes > 0 而且 whisper.enabled 才會做；每次念都一樣的引擎（say）重念沒有用。"""
    c = CFG.get(engine, {})
    n, thr = c.get("retakes", 0), c.get("min_score", 0.95)
    if not n or not whisper_on():
        return
    best = {o: s for (t, o), s in zip(items, score_takes([(t, [o]) for t, o in items]))}
    for k in range(1, n + 1):
        bad = [(t, o) for t, o in items if best[o][0] < thr]
        if not bad:
            break
        takes = [(t, o.with_suffix(f".t{k}.wav")) for t, o in bad]
        tts.synth(engine, takes)
        for (t, o), (_, tk), sc in zip(bad, takes, score_takes([(t, [tk]) for t, tk in takes])):
            if sc[0] > best[o][0]:
                o.write_bytes(tk.read_bytes()); best[o] = sc
            tk.unlink(missing_ok=True)
        log(f"重念第 {k} 輪：{len(bad)} 句 → 還有 {sum(best[o][0] < thr for _, o in items)} 句沒念對")
    for t, o in items:
        if best[o][0] < thr:
            log(f"重念 {n} 次仍沒念對（{best[o][0]}）｜{t[:24]}｜聽成：{best[o][1][:24]}｜{'；'.join(best[o][2])[:60]}")


def read_wav(p):
    with wave.open(str(p)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    loud = np.where(np.abs(a.astype(np.int32)) > 0.02 * 32768)[0]
    return a[max(0, loud[0] - int(0.05 * SR)):loud[-1] + int(0.08 * SR)] if len(loud) else a


def narrate(sections, engine, work):
    """每句一檔（有快取），回傳 [{sec, line, text, t0, t1}] 與整段音軌"""
    cache = work / "tts"; cache.mkdir(exist_ok=True)
    plan, todo = [], []
    for si, s in enumerate(sections):
        for li, line in enumerate(s["lines"]):
            for sent in sentences(clean(line)):
                say = speakable(sent, engine)
                h = hashlib.sha1(f"{engine}|{tts.voice_key(engine)}|{say}".encode()).hexdigest()[:16]
                out = cache / f"{h}.wav"
                plan.append((si, li, sent, out))
                if not out.exists() and (say, out) not in todo:
                    todo.append((say, out))
    log(f"講稿 {len(plan)} 句，要新合成 {len(todo)} 句")
    if todo:
        tts.synth(engine, todo)
        retake(engine, todo)
    gap_s, gap_sec = int(SR * CFG["pause"]["sentence"]), int(SR * CFG["pause"]["section"])
    audio, cues, cur, prev = [], [], 0, None
    for si, li, sent, out in plan:
        if prev is not None:
            g = np.zeros(gap_sec if si != prev else gap_s, np.int16); audio.append(g); cur += len(g)
        a = read_wav(out)
        cues.append({"sec": si, "line": li, "text": sent, "t0": cur / SR, "t1": (cur + len(a)) / SR})
        audio.append(a); cur += len(a); prev = si
    return cues, np.concatenate(audio)


# ───────────── 市場資料（真實收盤；主題沒開就整段不跑）─────────────
def market(day):
    import yfinance as yf
    tick = DATA["tickers"]
    end = datetime.strptime(day, "%Y-%m-%d").date()
    df = yf.download([t["ticker"] for t in tick], start=str(end - timedelta(days=60)), end=str(end), progress=False, auto_adjust=False)["Close"].dropna()
    rows = []
    for t in tick:
        s = df[t["ticker"]].dropna()
        if WEEKLY:   # 本週最後收盤 vs 上週最後收盤
            last = s.index[-1].date()
            prev = s[[i.date() < last - timedelta(days=last.weekday()) for i in s.index]]
            base = float(prev.iloc[-1])
        else:
            base = float(s.iloc[-2])
        rows.append({"ticker": t["ticker"], "name": t["name"], "aliases": t.get("aliases", []), "close": float(s.iloc[-1]), "chg": (float(s.iloc[-1]) / base - 1) * 100,
                     "series": [(str(i.date()), float(v)) for i, v in s.tail(22).items()]})
    default = next((i for i, t in enumerate(tick) if t["ticker"] == DATA.get("default_chart")), 0)
    return {"as_of": str(df.index[-1].date()), "rows": rows, "chg_label": TXT["chg_weekly" if WEEKLY else "chg_daily"], "default": default}


def events(sections, day):
    """數據段裡沒在講主要項目的句子＝大事／個別項目 → 圖卡資料：標籤、標題、關鍵數字、出處、（認得出代號就附）真實走勢。
    名稱 → 代號的對照在 theme.data.companies；稿子裡寫了（ABCD）這種括號代號會優先用。"""
    company = DATA.get("companies", {})
    idx_names = [n.replace(" ", "") for t in DATA["tickers"] for n in [t["name"], *t.get("aliases", [])]]
    out, want = {}, {}
    for si, s in enumerate(sections):
        if sec_kind(s["title"], si) != "market":
            continue
        for li, raw in enumerate(s["lines"]):
            t = clean(raw)
            m = re.match(r"^(" + DATA.get("event_labels", "焦點") + r")[：:]\s*", t or "")
            # 有標籤一定做卡；沒標籤的話，開頭就是指數名的是指數句，不做
            if not t or (not m and any(t.replace(" ", "").startswith(n) for n in idx_names)):
                continue
            label = m.group(1) if m else TXT["event_default"]
            body = t[m.end():] if m else t
            src = re.search(r"出處(?:是|：|:)\s*([^。]+)", body)
            body = re.sub(r"\s*出處(?:是|：|:)[^。]+。?", "", body).strip()
            tick = re.search(r"[（(]([A-Z]{1,5})[）)]", body)
            ticker = tick.group(1) if tick else next((v for k, v in company.items() if k in body), None)
            name = next((k for k, v in company.items() if v == ticker and k in body), ticker)
            # 關鍵數字：先找跟漲跌字連在一起的 %，再找金額／%
            num = None
            rng = re.search(r"([0-9.]+)\s*%\s*(?:到|至|–|-|~)\s*([0-9.]+)\s*%", body)
            if rng:
                num = {"text": f"{rng.group(1)}–{rng.group(2)}%", "dir": "flat"}
            for pat in (() if num else (r"(暴跌|重挫|大跌|下跌|跌|大漲|上漲|漲|勁揚)[約了]*\s*([0-9.]+)\s*%", r"(負|正)?\s*([0-9][0-9,.]*)\s*(億美元|兆美元|萬美元|美元|%)")):
                mm = re.search(pat, body)
                if mm:
                    if "%" in pat[-6:] and len(mm.groups()) == 2:
                        sign = "-" if any(w in mm.group(1) for w in ("跌", "挫")) else "+"
                        num = {"text": f"{sign}{mm.group(2)}%", "dir": "down" if sign == "-" else "up"}
                    else:
                        neg = mm.group(1) == "負"
                        num = {"text": f"{'-' if neg else ''}{mm.group(2)}{mm.group(3)}", "dir": "down" if neg else "flat"}
                    break
            head = re.split(r"[，。；]", body)[0]
            head = head if len(head) <= 30 else head[:29] + "…"
            out[f"{si}:{li}"] = {"label": label, "head": head, "body": body, "num": num, "source": src.group(1).strip() if src else "", "ticker": ticker, "name": name}
            if ticker:
                want[ticker] = True
    if want:
        import yfinance as yf
        end = datetime.strptime(day, "%Y-%m-%d").date()
        try:
            df = yf.download(list(want), start=str(end - timedelta(days=60)), end=str(end), progress=False, auto_adjust=False)["Close"]
            for e in out.values():
                if e["ticker"] and e["ticker"] in getattr(df, "columns", []):
                    sr = df[e["ticker"]].dropna()
                    if len(sr) > 5:
                        last = sr.index[-1].date(); mon = last - timedelta(days=last.weekday())
                        prev = sr[[i.date() < mon for i in sr.index]]
                        base = float(prev.iloc[-1]) if WEEKLY and len(prev) else float(sr.iloc[-2])
                        e["quote"] = {"close": float(sr.iloc[-1]), "chg": (float(sr.iloc[-1]) / base - 1) * 100, "label": TXT["chg_weekly" if WEEKLY else "chg_daily"],
                                      "series": [(str(i.date()), float(v)) for i, v in sr.tail(22).items()]}
        except Exception as ex:
            log("個別項目的走勢抓不到：", ex)
    return out


def week_range(mk):
    """本週第一個～最後一個交易日，例 10/27–10/31"""
    last = datetime.strptime(mk["as_of"], "%Y-%m-%d").date()
    mon = last - timedelta(days=last.weekday())
    first = next(d for d, _ in mk["rows"][0]["series"] if datetime.strptime(d, "%Y-%m-%d").date() >= mon)
    f = lambda x: f"{int(x[5:7])}/{int(x[8:])}"
    return f"{f(first)}–{f(mk['as_of'])}"


def sec_kind(title, idx):
    if idx == 0 or has(title, "open"):
        return "open"
    if HAS_MARKET and has(title, "market"):
        return "market"
    return "points"


# ───────────── 縮圖（Pillow）─────────────
def rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def find_font(weight):
    """先用 remotion/public/fonts 的 Noto Sans CJK TC（tools/get_fonts.py 下載），沒有就找系統裡的中文字型"""
    cands = [ROOT / f"remotion/public/fonts/NotoSansCJKtc-{weight}.otf", Path.home() / f"Library/Fonts/NotoSansCJKtc-{weight}.otf",
             *(Path(p) for p in CFG.get("thumbnail_fonts", [])),
             Path("/System/Library/Fonts/STHeiti Medium.ttc"), Path("/System/Library/Fonts/Hiragino Sans GB.ttc"), Path("/System/Library/Fonts/PingFang.ttc"),
             Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
             Path("C:/Windows/Fonts/msjhbd.ttc"), Path("C:/Windows/Fonts/msjh.ttc")]
    for p in cands:
        if p.exists():
            return str(p)
    sys.exit("找不到中文字型：先跑 python3 tools/get_fonts.py，或在 config.json 的 thumbnail_fonts 填一個字型檔路徑")


def font(w, s):
    return ImageFont.truetype(find_font(w), s)


def wrap(d, text, f, maxw):
    """逐字換行，但數字／英文單字（7.20%、Fed）不拆開"""
    out, cur = [], ""
    for tok in re.findall(r"[+-]?\d[\d,.]*%?|[A-Za-z][A-Za-z&.']*|\s+|.", text):
        if d.textlength(cur + tok, font=f) > maxw and cur.strip():
            out.append(cur.rstrip()); cur = tok.lstrip()
        else:
            cur += tok
    return out + ([cur] if cur.strip() else [])


def thumbnail(day, titles, mk, out):
    P = THEME["palette"]
    BG, BG2, INK, ACC, UP, DOWN = (rgb(P[k]) for k in ("bg", "bg2", "ink", "accent", "up", "down"))
    g = np.linspace(0, 1, H)[:, None]
    arr = (np.array(BG) * (1 - g) + np.array(BG2) * g)[:, None, :].repeat(W, 1).reshape(H, W, 3)
    im = Image.fromarray(arr.astype(np.uint8)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=INK)
    badge = THEME["badge"][kind_key()]
    bw = int(d.textlength(badge, font=font("Black", 66))) + 110
    d.rounded_rectangle([90, 62, 90 + bw, 152], 20, fill=ACC if WEEKLY else INK)
    d.text((90 + bw / 2, 107), badge, font=font("Black", 66), fill=BG, anchor="mm")
    when = week_range(mk) if WEEKLY and mk else day[5:].replace("-", "/")
    d.text((90 + bw + 40, 72), THEME["channel"] + "｜" + when, font=font("Bold", 56), fill=ACC)
    hook = re.sub(r"[｜|].*$", "", titles[0]) if titles else ""
    if mk:      # 左：漲跌最大的那一項；右：它近一個月的走勢（真實收盤）
        best = max(mk["rows"], key=lambda r: abs(r["chg"]))
        c = UP if best["chg"] >= 0 else DOWN
        d.text((90, 180), best["name"], font=font("Black", 120), fill=INK)
        d.text((90, 320), f"{best['chg']:+.2f}%", font=font("Black", 300), fill=c)
        v = [x for _, x in best["series"]]
        lo, hi = min(v), max(v)
        x0, x1, y0, y1 = 1230, 1850, 200, 600
        pts = [(x0 + i * (x1 - x0) / (len(v) - 1), y1 - (x - lo) / ((hi - lo) or 1) * (y1 - y0)) for i, x in enumerate(v)]
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.polygon(pts + [(x1, y1 + 60), (x0, y1 + 60)], fill=c + (60,))
        im.paste(ov, (0, 0), ov); d = ImageDraw.Draw(im)
        d.line(pts, fill=c, width=16, joint="curve")
        d.ellipse([pts[-1][0] - 26, pts[-1][1] - 26, pts[-1][0] + 26, pts[-1][1] + 26], fill=c)
        y = 720
        for l in wrap(d, hook, font("Black", 96), W - 180)[:2]:
            d.text((90, y), l, font=font("Black", 96), fill=INK); y += 120
    else:       # 沒有市場資料的主題：整張放標題
        d.rectangle([90, 250, 104, 250 + 190 * 3], fill=ACC)
        y = 260
        for l in wrap(d, hook, font("Black", 150), W - 300)[:3]:
            d.text((150, y), l, font=font("Black", 150), fill=INK); y += 190
        d.text((150, H - 170), THEME["tagline"][kind_key()], font=font("Bold", 52), fill=ACC)
    im.resize((1280, 720), Image.LANCZOS).save(out, quality=92)


# ───────────── 合成（Remotion）─────────────
def render_motion(sections, cues, audio, mk, day, work, out_mp4, chart=None):
    """動畫在 remotion/src/Video.tsx：這裡把資料寫成 props.json，旁白另存 wav，渲染完再把整片響度拉到 −14 LUFS"""
    rem = ROOT / "remotion"
    if not (rem / "node_modules").exists():
        sys.exit("還沒裝 Remotion：cd remotion && npm install")
    pub = rem / "public/ep" / work.name; pub.mkdir(parents=True, exist_ok=True)
    with wave.open(str(pub / "vo.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(audio.tobytes())
    doy = datetime.strptime(day, "%Y-%m-%d").timetuple().tm_yday
    accents = THEME.get("accents") or [THEME["palette"]["accent"]]      # accents 有填＝每天輪替；沒填＝固定用 palette.accent
    jingle = CFG.get("jingle") or None
    if jingle and not all((rem / "public" / jingle[k]).exists() for k in ("intro", "outro")):
        log("jingle 檔案不在 remotion/public/ 裡，這支片頭片尾沒有音效"); jingle = None
    ep = {"day": day, "channel": THEME["channel"], "stamp": THEME.get("stamp", ""), "badge": THEME["badge"][kind_key()],
          "intro_line": THEME.get("intro_line", HAS_MARKET),                    # 片頭頻道名下面的走勢折線
          "accent": accents[doy % len(accents)],                                # 重點色每天輪替
          "range": week_range(mk) if WEEKLY and mk else None, "tagline": THEME["tagline"][kind_key()],
          "intro": CFG["intro_sec"], "outro": CFG["outro_sec"], "narration": len(audio) / SR, "vo": f"ep/{work.name}/vo.wav",
          "market": mk, "chart": chart, "cues": cues, "headline": HEADLINE,
          "sections": [{"title": x["title"], "sub": x.get("sub"), "kind": sec_kind(x["title"], i), "lines": [clean(l) for l in x["lines"] if clean(l)]}
                       for i, x in enumerate(sections)],
          "events": events(sections, day) if mk else {},
          "burn_subs": CFG.get("burn_subtitles", False),     # 預設字幕走 YouTube CC（captions.srt），不燒進畫面
          "jingle": jingle,
          "theme": {"text": TXT, "verdict": THEME.get("verdict"), "trend_words": THEME.get("trend_words", {"up": [], "down": []}), "palette": THEME["palette"]}}
    if mk:
        log(f"大事圖卡：{len(ep['events'])} 張（附走勢 {sum(1 for e in ep['events'].values() if e.get('quote'))} 張）")
    props = work / "props.json"; props.write_text(json.dumps({"ep": ep}, ensure_ascii=False))
    raw = work / "motion.mp4"
    r_cfg = CFG.get("render", {})
    cmd = ["npx", "remotion", "render", "src/index.ts", "Daily", str(raw), f"--props={props}", f"--crf={r_cfg.get('crf', 23)}", "--log=error"]
    if r_cfg.get("concurrency"):
        cmd.append(f"--concurrency={r_cfg['concurrency']}")
    r = subprocess.run(cmd, cwd=rem, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("remotion render 失敗：" + (r.stderr or r.stdout)[-800:])
    # 整片只加一個固定增益到 −14 LUFS（動態的 loudnorm 會把小聲的片頭音效補大、毀掉它和旁白的相對音量）
    meas = subprocess.run(["ffmpeg", "-v", "info", "-i", str(raw), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    integ = float(re.findall(r"I:\s+(-?[0-9.]+) LUFS", meas)[-1])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-c:v", "copy",
                    "-af", f"volume={-14 - integ:.2f}dB,alimiter=limit=0.84:level=false,aresample=48000",
                    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", str(out_mp4)], check=True)
    (work / "vo.wav").write_bytes((pub / "vo.wav").read_bytes())
    return CFG["intro_sec"]


# ───────────── 上架文案 ─────────────
def package(day, sections, cues, titles, sources, lead, out_dir):
    """標題、說明欄（第一行是主題的 AI 揭露句）、標籤、CC 字幕"""
    P = THEME["publish"]
    md = datetime.strptime(day, "%Y-%m-%d").strftime("%-m/%-d")
    if not titles:
        hook = clean(sections[0]["lines"][0])[:24] if sections else THEME["channel"]
        titles = [t.format(hook=hook, channel=THEME["channel"], md=md) for t in P["fallback_titles"]]
    (out_dir / nm("titles.txt")).write_text("\n".join(titles[:3]) + "\n")
    chapters, seen = [], set()
    for c in cues:
        if c["sec"] not in seen:
            seen.add(c["sec"]); t = int(c["t0"] + lead)
            chapters.append(f"{t // 60}:{t % 60:02d} {sections[c['sec']].get('sub') or sections[c['sec']]['title']}")
    chapters[0] = "0:00 " + chapters[0].split(" ", 1)[1]
    summary = " ".join(clean(l) for l in sections[0]["lines"])[:120] if sections else ""
    desc = [P["ai_disclosure"], "", summary, "", P["chapters_label"], *chapters, "", P["sources_label"], *(sources or [P["no_sources"]]), "",
            P["disclaimer"], "", P["hashtags"][kind_key()].format(channel=THEME["channel"])]
    (out_dir / nm("description.md")).write_text("\n".join(desc) + "\n")
    tags = [t.format(channel=THEME["channel"]) for t in P["tags"][kind_key()]]
    body = " ".join(" ".join(s["lines"]) for s in sections)
    for k in P.get("tag_keywords", []):
        if k in body and k not in tags:
            tags.append(k)
    (out_dir / nm("tags.txt")).write_text(", ".join(tags) + "\n")
    write_srt(cues, lead, out_dir / nm("captions.srt"))
    return titles


def write_srt(cues, lead, path, maxlen=22):
    """CC 字幕：一句太長就在標點切開，時間按字數比例分；時間軸加上片頭秒數"""
    def ts(x):
        ms = int(round(x * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out, n = [], 0
    for c in cues:
        parts, buf = [], ""
        for ch in c["text"]:
            buf += ch
            if ch in "，、；：,;:" and len(buf) >= 8:
                parts.append(buf); buf = ""
        if buf:
            parts.append(buf)
        merged = []          # 太短的片段併回前一段，但不超過 maxlen
        for p in parts:
            if merged and len(merged[-1]) + len(p) <= maxlen:
                merged[-1] += p
            else:
                merged.append(p)
        total = sum(len(p) for p in merged) or 1; t = c["t0"]
        for p in merged:
            d = (c["t1"] - c["t0"]) * len(p) / total
            n += 1; out += [str(n), f"{ts(t + lead)} --> {ts(t + d + lead)}", p.rstrip("，、；：,;:"), ""]
            t += d
    path.write_text("\n".join(out))


def run_qc(out_dir, work, cues, engine):
    """不靠耳朵：整段旁白給 Whisper 聽寫，跟講稿比拼音＋聲調（1.0＝全對）"""
    with step("QC（Whisper 聽寫比對）"):
        sim = score_takes([("".join(speakable(c["text"], engine) for c in cues), [work / "vo.wav"])])[0][0]
    p = out_dir / nm("report.json"); rep = json.loads(p.read_text())
    rep["asr_similarity"] = sim; rep["steps_sec"].update(STEPS)
    p.write_text(json.dumps(rep, ensure_ascii=False, indent=1)); log("QC", sim)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", help="YYYY-MM-DD")
    ap.add_argument("--engine", default=CFG["engine"])
    ap.add_argument("--dir", help="講稿所在資料夾（預設 episodes/<日期>）")
    ap.add_argument("--weekly", action="store_true", help="每週那支：讀 weekly.md，產出檔名加 -weekly")
    ap.add_argument("--skip-qc", action="store_true")
    ap.add_argument("--qc-only", action="store_true", help="只補跑 QC（用上次的 work/）")
    a = ap.parse_args()
    global WEEKLY, HEADLINE
    WEEKLY = a.weekly
    t_start = time.time()
    out_dir = Path(a.dir).expanduser().resolve() if a.dir else episodes_dir() / a.day
    work = ROOT / "work" / (out_dir.name + ("-weekly" if WEEKLY else ""))
    if a.qc_only:
        if not whisper_on():
            sys.exit("QC 要先在 config.json 把 whisper.enabled 打開")
        rep = json.loads((out_dir / nm("report.json")).read_text())
        return run_qc(out_dir, work, json.loads((work / "props.json").read_text())["ep"]["cues"], rep["engine"])
    src = out_dir / ("weekly.md" if WEEKLY else "script.md")
    if not src.exists():
        sys.exit(f"找不到講稿 {src}")
    work.mkdir(parents=True, exist_ok=True)
    with step("讀稿"):
        sections, titles, sources, chart = parse_script(src.read_text())
    if not sections:
        sys.exit("講稿裡沒有可以念的段落（段落要用 ## 標題開頭）")
    HEADLINE = titles[0] if titles else clean(sections[0]["lines"][0])[:28]
    log(f"講稿：{len(sections)} 段，來源 {len(sources)} 條，標題候選 {len(titles)} 個，圖表：" + (f"{chart['title']}（{len(chart['points'])} 點）" if chart else "沒有／格式不對，不畫"))
    mk = None
    if HAS_MARKET:
        with step("抓收盤資料"):
            mk = market(a.day)
        log("收盤", mk["as_of"], " ".join(f"{r['name']} {r['chg']:+.2f}%" for r in mk["rows"]))
    with step("配音"):
        try:
            cues, audio = narrate(sections, a.engine, work)
        except SystemExit as e:                  # 主引擎失敗 → 備援引擎（config.json 的 fallback_engine）
            nxt = CFG.get("fallback_engine")
            if not nxt or nxt == a.engine:
                raise
            log(f"{a.engine} 失敗（{e}）→ 改用 {nxt}")
            a.engine = nxt
            cues, audio = narrate(sections, a.engine, work)
    with step("畫面＋合成（Remotion）"):
        lead = render_motion(sections, cues, audio, mk, a.day, work, out_dir / nm("video.mp4"), chart)
    with step("標題＋說明欄＋標籤＋縮圖"):
        titles = package(a.day, sections, cues, titles, sources, lead, out_dir)
        thumbnail(a.day, titles, mk, out_dir / nm("thumbnail.jpg"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out_dir / nm("video.mp4"))],
                               capture_output=True, text=True).stdout)
    rep = {"day": a.day, "kind": kind_key(), "theme": THEME["name"], "title": titles[0], "engine": a.engine, "duration_sec": round(dur, 1),
           "sentences": len(cues), "sources": len(sources), "market_as_of": mk["as_of"] if mk else None, "asr_similarity": "pending" if whisper_on() else "off",
           "steps_sec": STEPS, "files": sorted(p.name for p in out_dir.iterdir() if p.is_file() and ("-weekly" in p.name) == WEEKLY and p.name not in ("script.md", "weekly.md")),
           "build_sec": round(time.time() - t_start)}
    (out_dir / nm("report.json")).write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    log("完成", json.dumps(rep, ensure_ascii=False))
    if whisper_on() and not a.skip_qc:      # QC 不在發片的關鍵路徑上：daily.py 先上傳，再用 --qc-only 補跑
        run_qc(out_dir, work, cues, a.engine)


if __name__ == "__main__":
    main()
