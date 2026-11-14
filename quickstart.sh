#!/bin/bash
# 一行裝好並做出第一支範例影片（macOS）。
# 重跑是安全的：已經裝好的會跳過；不會改你的 config.json（唯一例外：設定的內建語音這台 Mac 沒有時，會換成有的那個）、
# 不會動你的主題和講稿。範例影片固定做在 episodes/sample/，用內附的美股範例主題和免費的內建語音。
#   ./quickstart.sh            裝好 → 做範例影片 → 打開影片
#   ./quickstart.sh --fonts    另外下載思源黑體（約 68 MB；不下載就用系統的中文字型）
#   ./quickstart.sh --no-open  做完不要自動打開影片
#   ./quickstart.sh --force    範例影片已經有了也重做一次
set -euo pipefail
cd "$(dirname "$0")"

FONTS=0; OPEN=1; FORCE=0
for a in "$@"; do
  case "$a" in
    --fonts) FONTS=1 ;;
    --no-open) OPEN=0 ;;
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "不認得的參數：$a（可用：--fonts --no-open --force）"; exit 2 ;;
  esac
done

# Homebrew 裝的工具有時不在 PATH 裡（剛裝完 Homebrew、或從別的程式啟動時）→ 自己補上
if [ -z "${QUICKSTART_STRICT_PATH:-}" ]; then
  for d in /opt/homebrew/bin /usr/local/bin; do
    [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
  done
  export PATH
fi

say_step() { printf '\n▶ %s\n' "$1"; }
DAY=2026-11-13      # 範例講稿的日期（範例用的是這一天的真實收盤）
export NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false      # 不要印「npm 有新版，請全域更新」那種通知，免得被照做

# ── 1. 檢查需要的東西 ──
say_step "檢查這台電腦有沒有需要的工具"
missing=(); brew_pkgs=()
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }      # ver_ge 現有 最低

if command -v python3 >/dev/null 2>&1; then
  pv=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
  if ver_ge "$pv" 3.10; then echo "  ✓ Python $pv"; else missing+=("Python 太舊（現在 $pv，需要 3.10 以上）"); brew_pkgs+=(python); fi
else missing+=("沒有 Python"); brew_pkgs+=(python); fi

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  nv=$(node -v | sed 's/^v//')
  if ver_ge "$nv" 18.0; then echo "  ✓ Node.js $nv"; else missing+=("Node.js 太舊（現在 $nv，需要 18 以上）"); brew_pkgs+=(node); fi
else missing+=("沒有 Node.js"); brew_pkgs+=(node); fi

if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then echo "  ✓ ffmpeg"
else missing+=("沒有 ffmpeg（處理聲音和影片用的工具）"); brew_pkgs+=(ffmpeg); fi

if [ ${#missing[@]} -gt 0 ]; then
  echo
  echo "還缺下面這些，先裝好再重跑一次 ./quickstart.sh："
  for m in "${missing[@]}"; do echo "  ✗ $m"; done
  echo
  if command -v brew >/dev/null 2>&1; then
    echo "在終端機貼這一行就會裝好："
    echo "  brew install ${brew_pkgs[*]}"
  else
    echo "這台電腦還沒有 Homebrew（Mac 上安裝工具用的程式）。先到 https://brew.sh 照首頁那一行裝好，再貼："
    echo "  brew install ${brew_pkgs[*]}"
  fi
  exit 1
fi

if ! command -v say >/dev/null 2>&1; then
  echo
  echo "這台電腦沒有 macOS 內建語音（say）。這個腳本只支援 macOS；"
  echo "其他系統請照 README 的「手動步驟」，並把 config.json 的 engine 改成 edge。"
  exit 1
fi

# ── 2. 安裝 ──
say_step "安裝 Python 套件（第一次約 1 分鐘）"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
echo "  ✓ 好了"

say_step "安裝動畫引擎 Remotion（第一次約 1 分鐘）"
if [ -d remotion/node_modules/remotion ]; then echo "  ✓ 已經裝過"
else (cd remotion && { npm ci --no-audit --no-fund --loglevel=error || npm install --no-audit --no-fund --loglevel=error; }); echo "  ✓ 好了"; fi   # npm ci＝照鎖定的版本裝，不會改動 package-lock.json

if [ "$FONTS" = 1 ]; then
  say_step "下載字型"
  .venv/bin/python tools/get_fonts.py
fi

# ── 3. 設定檔與配音聲音 ──
say_step "準備設定檔"
if [ -f config.json ]; then echo "  ✓ 已經有 config.json，不動它"
else cp config.example.json config.json; echo "  ✓ 建好 config.json（照抄範例）"; fi

if true; then      # 範例片一定用內建語音，所以不管 config.json 的 engine 是什麼都要確認聲音在
  VOICE=$(.venv/bin/python -c 'import json; print(json.load(open("config.json")).get("say", {}).get("voice", ""))')
  voices=$(say -v '?' 2>/dev/null || true)
  if [ -n "$VOICE" ] && ! printf '%s\n' "$voices" | grep -q "^$VOICE "; then
    # 聲音清單每行長這樣：「名字   zh_TW    # 試聽句」→ 取語系代碼前面那一段當名字
    alt=$(printf '%s\n' "$voices" | grep ' zh_TW ' | head -1 | sed -E 's/[[:space:]]+zh_[A-Z]+[[:space:]].*$//' || true)
    [ -n "$alt" ] || alt=$(printf '%s\n' "$voices" | grep ' zh_' | head -1 | sed -E 's/[[:space:]]+zh_[A-Z]+[[:space:]].*$//' || true)
    if [ -n "$alt" ]; then
      .venv/bin/python - "$alt" <<'PY'
import json, sys
c = json.load(open("config.json")); c.setdefault("say", {})["voice"] = sys.argv[1]
json.dump(c, open("config.json", "w"), ensure_ascii=False, indent=2)
PY
      echo "  這台 Mac 沒有「$VOICE」這個聲音，改用「$alt」（已寫進 config.json）"
    else
      echo
      echo "這台 Mac 還沒有中文語音。請到："
      echo "  系統設定 → 輔助使用 → 語音內容 → 系統聲音 → 管理聲音 → 中文（台灣）→ 下載「美佳」"
      echo "下載完再重跑一次 ./quickstart.sh"
      exit 1
    fi
  else
    echo "  ✓ 配音聲音：${VOICE:-系統預設}"
  fi
fi

# ── 4. 做第一支範例影片 ──
# 範例片固定用內附的美股範例主題＋免費的內建語音，放在 episodes/sample/。
# 不管你把 config.json 的主題或配音改成什麼，這一步都不會用到你的主題、不會花到付費額度，也不會動你自己的講稿。
SAMPLE_THEME=us-stocks
EP="episodes/sample"
OUT="$EP/video.mp4"
if [ -f "$OUT" ] && [ "$FORCE" = 0 ]; then
  say_step "範例影片已經做過了（要重做加 --force）"
else
  say_step "做第一支範例影片（約 2–4 分鐘，第一次會多下載一個無畫面的瀏覽器）"
  mkdir -p "$EP"
  cp "themes/$SAMPLE_THEME/sample/script.md" "$EP/script.md"
  if ! DAILY_VIDEO_THEME=$SAMPLE_THEME .venv/bin/python tools/make_day.py "$DAY" --dir "$EP" --engine say 2>&1 | grep -v -E 'Warning|inplace|pandas\.pydata|^\s*(quotes|data)\.'; then
    echo
    echo "做片失敗了。上面最後幾行是原因；常見的是網路不通（抓不到收盤資料）——等一下再跑一次 ./quickstart.sh 就好。"
    exit 1
  fi
fi

[ -f "$OUT" ] || { echo "沒有做出影片（$OUT 不存在）。請把上面的訊息貼到 GitHub issue。"; exit 1; }
FULL="$(pwd)/$OUT"
echo
echo "✅ 完成！你的第一支影片在："
echo "   $FULL"
echo "   同一個資料夾還有縮圖、標題、說明欄、標籤、字幕檔。"
echo
echo "下一步：換成自己的題材，兩種做法"
echo "   自己改 → 看 README.zh-TW.md 的「換成你自己的題材」和「每天怎麼出一支片」"
echo "   請 AI 改 → 在這個資料夾打開 Claude Code 或 Codex，貼這句話："
echo "     「請照 AGENTS.md 第 2 節，幫我建立一個新主題。我的頻道想做的題材是：＿＿＿＿」"
[ "$OPEN" = 1 ] && open "$FULL" || true
