# Daily video pipeline (script → YouTube-ready video)

English｜[繁體中文](README.zh-TW.md)

Turn one Markdown script into a narrated 16:9 video with animated cards, chapters, a caption file, a thumbnail, titles and a description.
Write the script yourself or have any AI write it every day — this project handles everything that happens *after* the script exists.

- **Runs for free.** The default voice is the one built into macOS. No API keys needed.
- **Swappable themes.** Two are included: a daily US-stock recap and a plain news digest. A new topic is one config file plus one writer brief — no code changes.
- **Everything else is optional and off by default:** paid voices, fetching scripts from Google Drive, uploading to YouTube, Telegram notifications, scheduling.

> The stock theme is only an example; nothing it produces is investment advice.
> Narration is built for Mandarin Chinese (numbers, dates and times are converted to spoken Chinese). The bundled themes, sample scripts and code comments are in Traditional Chinese. Other languages would need work in `tools/make_day.py` and are untested.

## What you get

Put a `script.md` in `episodes/<date>/`, run one command, and the same folder gains:

| File | What it is |
|---|---|
| `video.mp4` | 1920×1080 video: intro → animated sections → outro, normalised to −14 LUFS |
| `thumbnail.jpg` | 1280×720 thumbnail |
| `titles.txt` | three title candidates (the first is used as the title) |
| `description.md` | description: AI disclosure line, summary, chapter timestamps, source links |
| `tags.txt`, `captions.srt` | tags and timed captions |
| `report.json` | duration, time per step, which voice was used |

## Getting started (three ways — pick one)

### Option 1 (easiest): hand it to an AI assistant

If you use [Claude Code](https://claude.com/claude-code), Codex or a similar assistant that can operate your computer, paste this:

```text
Please download https://github.com/mickyyang-1407/daily-video to my computer, set it up following its AGENTS.md, and make the sample video for me. Then ask me what topic my channel is about and build a theme for it. Explain things in plain words, and do not upload anything or spend money for me.
```

It will install everything, make the first video, and ask what you want your channel to be about.

### Option 2: run one command yourself

Open Terminal and paste these two lines:

```bash
git clone https://github.com/mickyyang-1407/daily-video.git && cd daily-video
./quickstart.sh
```

It checks what your Mac is missing (and tells you the exact line to install it), then sets everything up, builds the sample video and opens it. About 3–5 minutes; rerunning is safe. Its messages are in Traditional Chinese.
The video lands at `episodes/2026-11-13/video.mp4` (about 1 min 40 s).

### Option 3: manual steps

For when you want to see every step, or you are not on a Mac. You need macOS, Python 3.10+, Node.js 18+ and ffmpeg (`brew install ffmpeg node`).

```bash
git clone https://github.com/mickyyang-1407/daily-video.git && cd daily-video

# 1. Python packages
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Animation engine (Remotion). The first render downloads a headless browser automatically
(cd remotion && npm install)

# 3. Fonts (optional, recommended): downloads Noto Sans CJK TC, about 68 MB. Without it the system CJK font is used
.venv/bin/python tools/get_fonts.py

# 4. Config: the example works as is
cp config.example.json config.json

# 5. Drop in the sample script and build
mkdir -p episodes/2026-11-13
cp themes/us-stocks/sample/script.md episodes/2026-11-13/
.venv/bin/python tools/make_day.py 2026-11-13
```

When it prints `完成 {...}` ("done"), the video is at `episodes/2026-11-13/video.mp4` (about 1 min 40 s; roughly two minutes to build on an Apple Silicon Mac).

The default voice is "Meijia" (Taiwanese Mandarin). If it is missing, download a Chinese (Taiwan) voice in System Settings → Accessibility → Spoken Content → System Voice → Manage Voices,
or list what you have with `say -v '?'` and put the name in `say.voice` in `config.json`.

Not on macOS: set `engine` to `edge` in `config.json` (`pip install edge-tts` first — free online voices through an unofficial interface that may stop working), or use a paid engine. Linux and Windows have not been tested.

## Use your own topic

A theme is one folder, `themes/<name>/`:

| File | Purpose |
|---|---|
| `theme.json` | channel name, stamp text, taglines, section rules, fixed on-screen text, colours, whether to fetch market data, how descriptions and tags are written |
| `PROMPT-for-writer.md` | the brief for your "writer AI": paste it in and it will write scripts in the right format |
| `sample/script.md` | a sample script |

Steps:

1. Copy the closest theme: `cp -r themes/plain-news themes/my-topic` (start from `plain-news` if you have no data cards, from `us-stocks` if you cover a daily market).
2. Edit `themes/my-topic/theme.json`. The usual changes:
   - `channel`, `stamp` (the seal stamped in the intro; 2–3 characters look best), `tagline`, `badge`
   - `text`: fixed on-screen lines (outro reminder, subscribe button, …)
   - `verdict`: a line starting with e.g. `判定：同意。` becomes a coloured stamp; `prefix` is the lead word, `options` maps each allowed word to a colour. Remove the block to turn stamps off
   - `palette` / `accents`: colours (`accents` rotates daily)
   - `publish`: the AI-disclosure line that opens the description, hashtags, fixed tags
   - `sections`: which heading keywords have special meaning (see "Script format")
3. Edit `PROMPT-for-writer.md` so its headings match `theme.json`.
4. Set `"theme": "my-topic"` in `config.json` and run `make_day.py` on a sample script.

What the stock theme adds (`data` in `theme.json`): it pulls real closing prices from Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) and draws index cards, a trend chart, a bottom ticker and per-stock cards.
Numbers in the script are only read aloud, never charted. For another market, change `data.tickers` (Yahoo Finance symbols) and `data.companies` (company name → symbol).
`"data": {"provider": "none"}` fetches nothing. Any other data source means editing `market()` in `tools/make_day.py`.

### Script format

```markdown
# 每日美股｜11/13            ← first line (the theme's script_head)

## 標題候選                   ← contains "標題": three video titles, not narrated
- …

## 開場                       ← first section = big opening line
…

## 盤勢回顧                   ← matches sections.market: index cards + chart (market themes only)
- one item per line

## 今日圖表                   ← contains "圖表": bar/line chart from the points you give, not narrated
- 圖名：…                     (title)
- 類型：長條圖                 (bar; 折線圖 = line)
- 單位：%                     (unit)
- 資料點：                    (points)
  - label：number
- 來源：https://…             (source)

## 大咖怎麼說                 ← any other section: items light up one by one
### subtitle｜source｜date    ← ### shows next to the section title and becomes a chapter
- 我們的看法：判定：部分同意。…   ← stamps the verdict

## 來源                       ← contains "來源/參考": links go into the description, not narrated
- https://…

## 不公開備註                 ← contains "不公開": never narrated, shown, or published
```

For a weekly wrap-up, save the script as `weekly.md` and add `--weekly`; outputs get a `-weekly` suffix.

## Optional features (all off by default)

Keys go in `.env` (`cp env.example .env`; it is git-ignored). Switches live in `config.json`.

| Feature | How to turn it on | What you need |
|---|---|---|
| **Paid voices** | set `engine` to `breeze-api`, `minimax` or `gemini` | that provider's API key in `.env`. BreezeBlue also needs `BREEZE_VOICE_ID` (`tools/breeze_voice.py` can design a voice from a text description). `fallback_engine` names a backup engine |
| **Auto-retake + listening check** | `whisper.enabled: true` | `pip install openai-whisper pypinyin opencc-python-reimplemented`. Each sentence is transcribed by Whisper and compared by pinyin; misread sentences are re-synthesised (`<engine>.retakes`), and the whole narration gets a score in `report.json` |
| **Intro/outro sound** | fill in `jingle` in `config.json` (see the top of `tools/jingle.py`) | two audio files of your own in `remotion/public/brand/`. No audio ships with this repo; the intro and outro are silent by default |
| **Scheduling** | run `tools/daily.py`; example in `examples/launchd/` | it waits for the script (untouched for 60 s), builds, then uploads/notifies as configured. Past the deadline with no script it only notifies — it never writes a script itself |
| **Fetch scripts from Google Drive** | `fetch.enabled: true` | either (a) the simple way: install Google Drive for desktop and point `episodes_dir` at the synced folder — no need for this feature; or (b) `tools/drive_fetch.py`, which needs a logged-in [Claude Code](https://claude.com/claude-code) CLI with the Google Drive connector enabled on claude.ai |
| **Upload to YouTube** | `upload.enabled: true`; `upload.privacy` defaults to `private` | the official YouTube Data API: a Google Cloud project with an OAuth client, `pip install google-api-python-client google-auth-oauthlib`, then run `tools/youtube_upload.py auth` once. Steps and limits are at the top of `tools/youtube_upload.py` |
| **Telegram notifications** | `notify.telegram: true` | create a bot with @BotFather, put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` |
| **Channel avatar / banner / logo** | command at the top of `remotion/src/Brand.tsx` | renders channel art in the same style |

Google locks videos uploaded through an API project that has not passed its audit to private, so until then you upload as private and press Publish in YouTube Studio yourself.
Uploads are always marked as "altered or synthetic content". To monetise AI-generated videos, the content needs your own analysis and viewpoint — not a translation or a read-out of someone else's work.

## Test status (stated plainly)

| Feature | Status |
|---|---|
| Building a video (built-in `say` voice, both themes, Remotion render, thumbnail, description, captions) | ✅ Tested end to end from a fresh clone, following this page |
| One-command setup `./quickstart.sh` | ✅ Tested: a fresh clone plus this one command produces the video; missing tools are listed with the install line |
| Scheduler entry `tools/daily.py`, manual mode | ✅ Tested |
| Free online voice `edge` | ✅ Tested: produces audio |
| Auto-retake + listening check (Whisper) | ✅ The listening check and the per-sentence check are tested; retakes are not (the built-in voice is deterministic, so they never trigger) |
| Falling back to the backup engine when the main one fails | ✅ Tested |
| Fetching from Google Drive, `tools/drive_fetch.py` | ✅ Tested: fetched the day's script; a date with no script reports "not there yet" |
| Paid voices `breeze-api`, `minimax`, `gemini` | ⚠️ Only checked that a missing key tells you which one to set, and that a wrong key prints the service's error instead of crashing. **Never run with a real key** |
| YouTube upload, `tools/youtube_upload.py` | ⚠️ Dry run only: `--dry-run` checks the files and prints the title/description/tags it would send; missing files and missing authorisation give clear messages. **No real upload has been made** |
| Telegram notifications | ⚠️ Dry run only: a missing token is reported; `NOTIFY_DRY_RUN=1` prints instead of sending. **No real message has been sent** |
| Jingle generator `tools/jingle.py`, voice design `tools/breeze_voice.py` | ❌ Untested (need paid keys) |
| Linux, Windows | ❌ Untested |

Issues are welcome.

## Layout

```
quickstart.sh           one-command setup + sample video
AGENTS.md               instructions for AI coding agents
tools/make_day.py       script → video (main program)
tools/tts.py            voice engines (add new ones here)
tools/daily.py          scheduler entry: wait for script → build → upload → notify
tools/…                 everything else is optional; each file starts with usage notes
remotion/src/Video.tsx  the animation template (React)
themes/                 themes
episodes/<date>/        your scripts and outputs (git-ignored)
work/                   scratch: per-sentence voice cache, render data (git-ignored, safe to delete)
```

## FAQ

- **Does re-running re-synthesise everything?** No. Sentences are cached; only changed ones are redone.
- **Rendering is slow.** Set `render.concurrency` in `config.json` (by default Remotion decides).
- **I want burned-in subtitles.** `burn_subtitles: true`. By default captions go to `captions.srt` for YouTube CC.
- **yfinance returns nothing.** Yahoo Finance throttles now and then; retry later or upgrade `yfinance`.

## License and third parties

- This project's code, themes and sample scripts are released under the [MIT License](LICENSE).
- [Remotion](https://www.remotion.dev/license) has its own license: free for individuals and small teams, a company license is required for larger for-profit organisations. Read its terms before use.
- Noto Sans CJK is under the SIL Open Font License 1.1; `tools/get_fonts.py` downloads it from the official repository and it is not redistributed here.
- Market data comes from Yahoo Finance via yfinance and is subject to Yahoo's terms.
- Whether TTS output may be used commercially, and what attribution it needs, depends on each provider's terms.
