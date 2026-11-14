# Instructions for AI coding agents

You are helping someone — very likely a non-programmer — turn Markdown scripts into narrated videos with this repo.
Reply in the user's language. Explain in plain words; avoid jargon, and when you must use a tool name, say in one line what it is.

## 1. Install and make the sample video

On macOS, run this from the repo root. It checks prerequisites, installs everything, builds the sample video and prints its path:

```bash
./quickstart.sh --no-open
```

- If it lists missing tools, it prints the exact `brew install …` line. Ask the user before installing system software, then rerun.
- It is safe to rerun; finished steps are skipped. `--force` rebuilds the sample, `--fonts` also downloads Noto Sans CJK (68 MB, optional).
- Success = `episodes/2026-11-13/video.mp4` exists (about 100 s long). Tell the user where it is and offer to open it (`open <path>`).
- Not macOS: follow "Manual steps" in README.md and set `"engine": "edge"` in `config.json` (`pip install edge-tts`). This path is less tested.

Verify, don't assume: check the file exists and read `episodes/2026-11-13/report.json` (duration, engine) before saying it worked.

## 2. Build a theme for the user's topic

After the sample works, ask what the channel is about. Then:

1. Pick the starting point:
   - `themes/plain-news` — any topic without live market data (news, tech, sports, film, study notes…).
   - `themes/us-stocks` — a daily market recap with real closing prices from Yahoo Finance (other markets: change the tickers).
2. Copy it: `cp -r themes/plain-news themes/<short-name>`.
3. Edit `themes/<short-name>/theme.json`:
   - `name` (same as the folder), `channel` (channel name), `stamp` (2–3 characters for the seal in the intro), `tagline`, `badge`
   - `script_head` — the first line every script must start with
   - `text` — fixed on-screen lines (opening label, outro line, subscribe button)
   - `verdict` — `prefix` + `options` (word → colour) for the coloured stamps; delete the block if the topic has no verdicts
   - `sections` — heading keywords: `titles`, `sources`, `chart`, `private` (never published), `open`, `market`, `required`
   - `palette` / `accents` — colours
   - `publish` — AI-disclosure line, disclaimer, hashtags, tags, fallback titles
   - `data` — `{"provider": "none"}`, or for a market theme `tickers` (Yahoo symbols + display names) and `companies`
4. Rewrite `themes/<short-name>/PROMPT-for-writer.md` so every heading it tells the writer to use matches `sections` and `script_head`,
   and the verdict words match `verdict.options`. This file is what the user pastes into their "writer AI".
5. Write `themes/<short-name>/sample/script.md` in that format, with clearly fictional or verifiable content.
6. Set `"theme": "<short-name>"` in `config.json`.
7. Verify: copy the sample to `episodes/<YYYY-MM-DD>/script.md`, run `.venv/bin/python tools/make_day.py <YYYY-MM-DD>`,
   then extract a few frames (`ffmpeg -ss 10 -i episodes/<date>/video.mp4 -frames:v 1 frame.jpg`) and look at them:
   channel name, stamp, section titles and verdict stamps should all show the new theme, with no overflowing text.

Script format and what each heading does: see "Script format" in README.md. Narration is Mandarin-only for now.

## 3. Rules

- Everything beyond making a video is optional and **off by default**: paid voices, Whisper checks, Google Drive fetch, YouTube upload, Telegram, scheduling.
  Do not switch any of them on unless the user asks for that feature.
- Never upload, publish, send messages, or spend the user's money or API credits on your own initiative.
  For YouTube use `tools/youtube_upload.py <date> --dry-run` to check, and let the user run the real upload.
- Secrets live only in `.env` (git-ignored). Never put keys in `config.json`, themes, scripts, commits or chat. Do not print them.
- Do not invent facts, quotes or numbers in scripts. Content that summarises others' work needs sources in the script's sources section.
- `episodes/`, `work/`, `logs/`, `config.json` and `.env` are the user's local data — do not commit them.
- Keep changes small. To add a voice engine, add a function in `tools/tts.py` and register it in `ENGINES`; do not hard-code topic-specific text in `tools/` or `remotion/src/` — it belongs in the theme.

## 4. Where things are

| Path | What |
|---|---|
| `quickstart.sh` | one-command setup + sample video |
| `tools/make_day.py` | script → video (main program); `--weekly`, `--engine`, `--dir` |
| `tools/tts.py` | voice engines (`say`, `edge`, `breeze-api`, `minimax`, `gemini`) |
| `tools/daily.py` | scheduler entry: wait for script → build → optional upload/notify |
| `remotion/src/Video.tsx` | animation template; all text comes from the theme |
| `themes/<name>/` | `theme.json`, `PROMPT-for-writer.md`, `sample/script.md` |
| `config.example.json`, `env.example` | copy to `config.json` / `.env` |
| README.md "Test status" | what has really been tested and what has only been dry-run |
