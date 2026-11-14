# Instructions for AI coding agents

You are helping someone — very likely a non-programmer — turn Markdown scripts into narrated videos with this repo.
Reply in the user's language. Explain in plain words; avoid jargon, and when you must use a tool name, say in one line what it is.

## 1. Install and make the sample video

On macOS, run this from the repo root. It checks prerequisites, installs everything, builds the sample video and prints its path:

```bash
./quickstart.sh --no-open
```

- If it lists missing tools, it prints the exact `brew install …` line. Ask the user before installing system software, then rerun.
  Never install anything globally with npm or pip (`npm install -g …`, `pip install` outside `.venv`), even if some tool's output suggests it.
- Safe to rerun: finished steps are skipped, and it never touches the user's theme, scripts or `config.json`
  (one exception: if the configured macOS voice is missing it switches `say.voice` to one that exists).
- The sample always uses the bundled `us-stocks` theme and the free built-in voice, whatever `config.json` says, and lands in `episodes/sample/`.
  `--force` rebuilds it; `--fonts` also downloads Noto Sans CJK (68 MB, optional).
- Success = `episodes/sample/video.mp4` exists (about 100 s long). Tell the user where it is and offer to open it (`open <path>`).
- Not macOS: follow the manual steps in README.md and set `"engine": "edge"` in `config.json` (`pip install edge-tts` inside `.venv`). Less tested.

Verify, don't assume: check the file exists and read `episodes/sample/report.json` (duration, engine) before saying it worked.

## 2. Build a theme for the user's topic

After the sample works, ask what the channel is about. Then:

1. Pick the starting point:
   - `themes/plain-news` — any topic without live market data (news, tech, sports, film, coffee shops, study notes…).
   - `themes/us-stocks` — a daily market recap with real closing prices from Yahoo Finance (other markets: change the tickers).
2. Copy it: `cp -r themes/plain-news themes/<short-name>`.
3. Edit `themes/<short-name>/theme.json` (field guide below).
4. Rewrite `themes/<short-name>/PROMPT-for-writer.md` so every heading it tells the writer to use matches `sections` and `script_head`,
   and the verdict words match `verdict.prefix` / `verdict.options`. This file is what the user pastes into their "writer AI".
5. Write `themes/<short-name>/sample/script.md` in that format, with clearly fictional or verifiable content.
6. Set `"theme": "<short-name>"` in `config.json`.
7. Verify: copy the sample to `episodes/<YYYY-MM-DD>/script.md`, run `.venv/bin/python tools/make_day.py <YYYY-MM-DD>`,
   then pull a few frames into the git-ignored `work/` folder and look at them:
   ```bash
   mkdir -p work/frames
   for t in 2 8 30 60; do ffmpeg -y -v error -ss $t -i episodes/<YYYY-MM-DD>/video.mp4 -frames:v 1 work/frames/$t.jpg; done
   ```
   Channel name, stamp, colours, section titles and verdict stamps should all show the new theme, with no overflowing text.

### `theme.json` field guide

Change these for every new theme:

| Field | What it does |
|---|---|
| `name` | Must equal the folder name. |
| `channel` | Channel name shown in the intro, top bar, outro and thumbnail. Up to ~6 CJK characters looks best in the intro. |
| `stamp` | The red seal stamped in the intro and outro. 2–3 characters. Empty string = no seal. |
| `tagline.daily` / `.weekly` | One line under the channel name in the intro. |
| `badge.daily` / `.weekly` | Small black label next to the channel name (e.g. 每日重點). Also the big label on the thumbnail. |
| `script_head.daily` / `.weekly` | What the first line of every script must start with (e.g. `# 每日重點｜`). Only checked when fetching from Google Drive, but keep the writer prompt consistent with it. |
| `text.*` | Fixed on-screen sentences: `open_label` (caption above the opening line), `outro_line`, `outro_note`, `subscribe`, `subscribed`. The rest (`key_number`, `source`, `data_source`, `chart_days`, `close`, `chg_*`, `event_default`) are only used by market themes — copy as is. |
| `text.verdict_label` | The small caption next to the big stamp (e.g. 我們的判定). It is **not** matched against the script: the script line can start with anything (「我們的看法：」is just narration). Changing this needs no change in the writer prompt. |
| `verdict.prefix` + `verdict.options` | A line containing `<prefix>：<option>。` gets a coloured stamp, e.g. prefix `評價`, options `{"值得關注": "#1F7A3E", …}` → 「評價：值得關注。」. If you change these, change the writer prompt to the same words. Delete the whole `verdict` block for topics with no verdicts. |
| `palette` | Colours: `bg`, `bg2`, `panel` (paper tones), `ink` (text), `muted`, `accent` (highlight colour), `up`, `down`. |
| `accents` | **Optional list of highlight colours that rotates by day of the year.** If present, it overrides `palette.accent`, so a single test render may show a colour other than the first one. For one fixed colour, delete `accents` and set `palette.accent`. |
| `intro_line` | `true`/`false`: draw the rising trend line under the channel name in the intro. Default: `true` only when the theme fetches market data; otherwise a plain underline. |
| `publish.ai_disclosure`, `.disclaimer`, `.hashtags`, `.tags`, `.fallback_titles` | Text for the YouTube description, hashtags and tags. `{channel}`, `{hook}`, `{md}` are filled in automatically. |
| `data` | `{"provider": "none"}` for no market data. For a market theme: `tickers` (Yahoo Finance symbols + display names + `aliases`), `default_chart`, `companies` (company name → symbol), `event_labels`. |

Usually copy as is:

| Field | What it does |
|---|---|
| `language` | Language code written into the YouTube upload metadata (`zh-TW`). Nothing else reads it. |
| `speak_numbers` | `"zh"` converts digits, dates, times and percentages to spoken Chinese before narration (2026 年 → 二零二六年, 12.5% → 百分之十二點五). Any other value leaves digits for the voice engine to read. Keep `"zh"` for Mandarin. |
| `sections.titles`, `.sources`, `.chart`, `.private`, `.open`, `.market` | Keyword lists matched against `##` headings: titles (never narrated), sources (links go to the description), chart (drawn, not narrated), private (dropped entirely), open (big opening line), market (index cards; leave `[]` without market data). |
| `sections.required` | Headings a script must contain. Only enforced when fetching from Google Drive — a script missing one is rejected and saved as `*.drive-rejected`. `make_day.py` itself does not check it. |
| `trend_words.up` / `.down` | Words coloured green / red on screen (上漲, 下跌…), and the `%` numbers after them. Use `{"up": [], "down": []}` for topics where this makes no sense. |
| `say_as` | Pronunciation fixes: `"all": {"written": "spoken"}` applies to every voice, `"<engine>": {...}` to one engine. Subtitles keep the written form. Start with `{"all": {}}` and add entries when you hear a misreading. |
| `publish.tag_keywords` | If one of these words appears in the script, it is added to that episode's tags. |
| `publish.youtube_category` | YouTube's numeric category id, used only by the API upload: `25` News & Politics, `27` Education, `28` Science & Technology, `24` Entertainment, `22` People & Blogs, `17` Sports, `10` Music. |
| `publish.chapters_label`, `.sources_label`, `.no_sources` | Headings inside the description. |

## 3. The daily routine (walk the user through this)

1. **Give the writer its brief (once).** Paste the whole `themes/<short-name>/PROMPT-for-writer.md` into a chat AI that can browse the web
   (Claude, ChatGPT, Gemini, Grok…), or into a scheduled agent if the user wants it hands-off.
2. **Each day, get the script** and save it as plain text at `episodes/<YYYY-MM-DD>/script.md` (a weekly wrap-up is `weekly.md` in the same folder).
   The folder name is the date the program uses — it is shown on screen, in the thumbnail, and decides which market close is fetched.
   The date in the script's first line is only text; keep the two the same so nothing looks odd.
3. **Build:** `.venv/bin/python tools/make_day.py <YYYY-MM-DD>` (add `--weekly` for `weekly.md`).
4. **Collect the results** in `episodes/<YYYY-MM-DD>/`: `video.mp4`, `thumbnail.jpg`, `titles.txt` (first line = title), `description.md`, `tags.txt`, `captions.srt`.
   Upload them to YouTube by hand, or see the optional upload in README.md.
5. Fixing a script and rerunning the same command only re-voices the changed sentences.

Hands-off scheduling (`tools/daily.py` + `examples/launchd/`) and Google Drive fetch are optional — offer them only if the user asks.

## 4. Rules

- Everything beyond making a video is optional and **off by default**: paid voices, Whisper checks, Google Drive fetch, YouTube upload, Telegram, scheduling.
  Do not switch any of them on unless the user asks for that feature.
- Never upload, publish, send messages, or spend the user's money or API credits on your own initiative.
  For YouTube use `tools/youtube_upload.py <date> --dry-run` to check, and let the user run the real upload.
- Secrets live only in `.env` (git-ignored). Never put keys in `config.json`, themes, scripts, commits or chat. Do not print them.
- Do not invent facts, quotes or numbers in scripts. Content that summarises others' work needs sources in the script's sources section.
- `episodes/`, `work/`, `logs/`, `config.json` and `.env` are the user's local data — do not commit them. Put scratch files in `work/`.
- Keep changes small. To add a voice engine, add a function in `tools/tts.py` and register it in `ENGINES`; do not hard-code topic-specific text in `tools/` or `remotion/src/` — it belongs in the theme.

## 5. Where things are

| Path | What |
|---|---|
| `quickstart.sh` | one-command setup + sample video (`episodes/sample/`) |
| `tools/make_day.py` | script → video (main program); `--weekly`, `--engine`, `--dir` |
| `tools/tts.py` | voice engines (`say`, `edge`, `breeze-api`, `minimax`, `gemini`) |
| `tools/daily.py` | scheduler entry: wait for script → build → optional upload/notify |
| `remotion/src/Video.tsx` | animation template; all text comes from the theme |
| `themes/<name>/` | `theme.json`, `PROMPT-for-writer.md`, `sample/script.md` |
| `config.example.json`, `env.example` | copy to `config.json` / `.env` |
| README.md "Test status" | what has really been tested and what has only been dry-run |
