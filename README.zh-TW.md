# daily-video：把任何題材的講稿，每天自動做成一支影片

[English](README.md)｜繁體中文

給它一份文字講稿，它就做出一支有配音、動態畫面、章節、字幕檔、縮圖、標題與說明欄的 16:9 影片，可以直接上傳 YouTube。
講稿可以自己寫，也可以交給任何 AI 每天寫；這個工具負責「拿到稿之後」的所有事。

- **什麼題材都能套**：新聞整理、學習筆記、店家消息、每日行情……換題材只要改一個設定檔＋一份給寫手 AI 的說明，不用改程式。
- **免費就能跑**：預設用 macOS 內建語音配音，不需要任何金鑰。
- **其他都是選配、預設關閉**：付費配音、從 Google Drive 抓稿、上傳 YouTube、Telegram 通知、排程。

> 旁白目前只支援中文（數字、日期會轉成中文念法）。

## 內附的範例主題

每個主題都有自己的頻道名、印章、配色、給寫手 AI 的交稿說明和一份範例講稿。挑一個最接近的複製去改。

| 主題 | 一句話 | 適合什麼題材 |
|---|---|---|
| `general`（預設） | 最中性的版型，沒有任何題材設定 | 任何題材的起點：新聞整理、公告、讀書筆記、戰報 |
| `tech-news` | 每天幾則新聞＋「值得關注／再觀察／炒作居多」印章 | 科技、AI、產業新聞，任何「新聞＋短評」 |
| `cafe-daily` | 暖色版型＋「值得去／看心情／先不用」印章 | 咖啡店、美食、旅遊、選物等生活類 |
| `word-a-day` | 一集只講一件事＋難度印章 | 每日單字、每日一題、歷史上的今天等學習類 |
| `us-stocks` | 自動抓真實收盤，畫數據卡、走勢圖、跑馬燈 | 有每日數據的題材：股市、匯率、加密貨幣（此主題的內容不構成投資建議） |

## 會做出什麼

`episodes/<日期>/` 裡放一份 `script.md`，跑一行指令，同一個資料夾會多出：

| 檔案 | 內容 |
|---|---|
| `video.mp4` | 1920×1080 影片：片頭 → 各段動畫 → 片尾，整片響度 −14 LUFS |
| `thumbnail.jpg` | 1280×720 縮圖 |
| `titles.txt` | 3 個標題候選（第一個當正式標題） |
| `description.md` | 說明欄：AI 揭露句、摘要、章節時間、來源連結 |
| `tags.txt`、`captions.srt` | 標籤、CC 字幕（有時間碼） |
| `report.json` | 這一集的長度、各步驟花多久、用哪個聲音 |

## 開始用（三種方式，挑一種）

### 方式一（最簡單）：交給 AI 助手

如果你有 [Claude Code](https://claude.com/claude-code) 或 Codex 這類會自己操作電腦的 AI 助手，把下面這段話整段貼給它：

```text
請幫我把 https://github.com/mickyyang-1407/daily-video 下載到我的電腦，照裡面的 AGENTS.md 裝好，做出範例影片給我看。做好之後問我想做什麼題材的頻道，再幫我建立自己的主題。過程用白話跟我說明，不要替我上傳或花錢。
```

它會幫你裝好、做出第一支影片，再問你想做什麼題材。

### 方式二：自己跑一行指令

打開「終端機」，貼這兩行：

```bash
git clone https://github.com/mickyyang-1407/daily-video.git && cd daily-video
./quickstart.sh
```

它會先檢查電腦缺什麼（缺了會告訴你要貼哪一行去裝），然後自動裝好、做出範例影片並打開。全程大約 3–5 分鐘。
影片在 `episodes/sample/video.mp4`（約 1 分半）。

重跑是安全的：裝好的會跳過，不會動你的主題、講稿和 `config.json`。範例影片固定用內附的通用主題和免費的內建語音，就算你之後換了主題或付費配音，重跑它也不會用到你的設定、不會花錢。

### 方式三：手動一步一步來

想知道每一步在做什麼，或不是用 Mac 的人看這裡。要先有：macOS、Python 3.10 以上、Node.js 18 以上、ffmpeg（`brew install ffmpeg node`）。

```bash
git clone https://github.com/mickyyang-1407/daily-video.git && cd daily-video

# 1. Python 套件
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 動畫引擎（Remotion）。第一次渲染會自動下載一個無畫面的瀏覽器
(cd remotion && npm ci)

# 3. 字型（選配）：下載思源黑體繁中，約 68 MB。不下載就用系統的中文字型
.venv/bin/python tools/get_fonts.py

# 4. 設定檔：先照抄範例就能跑
cp config.example.json config.json

# 5. 放一份範例講稿，做片（資料夾名字就是影片上顯示的日期）
mkdir -p episodes/2026-11-13
cp themes/general/sample/script.md episodes/2026-11-13/
.venv/bin/python tools/make_day.py 2026-11-13
```

做完會印出 `完成 {...}`，影片在 `episodes/2026-11-13/video.mp4`（Apple Silicon 的 Mac 大約 2 分鐘做完）。
想看別的範例主題：把 `config.json` 的 `"theme"` 改成上表任何一個名字，換成那個主題的 `sample/script.md` 再跑一次。

內建語音預設用台灣中文的「美佳」（Meijia）。聽起來不對或報錯：到「系統設定 → 輔助使用 → 語音內容 → 系統聲音 → 管理聲音」下載中文（台灣）的聲音，
或用 `say -v '?'` 看這台 Mac 有哪些聲音，把名字填進 `config.json` 的 `say.voice`。

不是 macOS：把 `config.json` 的 `engine` 改成 `edge`（先 `pip install edge-tts`，免費線上語音，但走的是非官方介面，可能隨時失效），或用付費引擎。Linux／Windows 沒有實測過。

## 換成你自己的題材

一個「主題」就是 `themes/<名字>/` 一個資料夾：

| 檔案 | 用途 |
|---|---|
| `theme.json` | 頻道名、印章字、片頭標語、段落規則、畫面上的固定文字、配色、說明欄與標籤的寫法 |
| `PROMPT-for-writer.md` | 給「寫手 AI」的交稿說明：整份貼給它，它就會照格式寫稿 |
| `sample/script.md` | 一份範例講稿 |

做法：

1. 從上面的表挑最接近的主題複製：`cp -r themes/general themes/my-topic`。
2. 改 `themes/my-topic/theme.json`。最常改的：
   - `name`（跟資料夾同名）、`channel`（頻道名）、`stamp`（片頭蓋下去的印章字，2–3 個字最好看）、`tagline`、`badge`
   - `text`：畫面上的固定句子（開場上方的小標、片尾提醒、訂閱按鈕…）
   - `verdict`：講稿裡「評價：推薦。」這種句子會變成彩色印章；`prefix` 是前面那個詞，`options` 是可用的字和顏色。不要印章就整個拿掉
   - `palette`：配色。`accent` 是重點色、`stamp` 是印章的顏色
   - `accents`（可以不填）：一串重點色，**每天輪替**。有填的話會蓋掉 `palette.accent`，所以試做那天看到的可能不是第一個顏色；想固定一個顏色就不要填
   - `intro_line`：片頭頻道名下面要不要畫一條往上的走勢折線（`true`／`false`）。不填的話，只有抓每日數據的主題會畫
   - `publish`：說明欄第一行的 AI 揭露句、hashtag、固定標籤
   - `sections`：哪些段落標題有特殊意義（見下面「講稿格式」）
3. 改 `PROMPT-for-writer.md`，讓段落標題、印章用字跟 `theme.json` 對得上。
4. `config.json` 的 `"theme"` 改成 `"my-topic"`，用你的範例稿跑一次 `make_day.py` 看畫面。

每個欄位的完整說明在 [AGENTS.md](AGENTS.md) 的欄位表。

### 講稿格式

```markdown
# 每日重點｜11/13            ← 第一行（主題的 script_head）

## 標題候選                   ← 含「標題」：3 個影片標題，不會被念
- …

## 開場                       ← 第一段＝開場大字
…

## 今日重點                   ← 一般段落：標題隨你取，裡面一條一條亮起來
- 一行一條

## 今日圖表                   ← 含「圖表」：照你給的資料點畫長條／折線圖，不會被念
- 圖名：…
- 類型：長條圖
- 單位：%
- 資料點：
  - 名稱：數字
- 來源：https://…

## 我們怎麼看
### 小標｜來源｜日期          ← ### 會顯示在段落標題右邊，也會變成章節
- 我們的看法：評價：推薦。…   ← 蓋印章

## 結尾

## 來源                       ← 含「來源／參考」：連結會放進說明欄，不會被念
- https://…

## 不公開備註                 ← 含「不公開」：整段不念、不進畫面、不進說明欄
```

每週一支的總整理：稿子存成 `weekly.md`，指令加 `--weekly`，產出檔名會多 `-weekly`。

### 每天怎麼出一支片

1. **把交稿說明交給寫手 AI（只做一次）**：打開一個會上網查資料的聊天 AI（Claude、ChatGPT、Gemini、Grok 都可以），把 `themes/<你的主題>/PROMPT-for-writer.md` 整份貼給它。
2. **每天拿稿**：請它照格式寫出當天的講稿，把全文存成純文字檔 `episodes/<日期>/script.md`，日期寫成 `2026-11-13` 這種格式。
   資料夾的日期就是程式用的日期（畫面右上角、縮圖都看它）；講稿第一行的日期只是文字，兩個寫一樣就不會怪。
3. **做片**：`.venv/bin/python tools/make_day.py 2026-11-13`
4. **拿成品**：同一個資料夾的 `video.mp4`、`thumbnail.jpg`、`titles.txt`（第一行當標題）、`description.md`（貼進說明欄）、`tags.txt`、`captions.srt`（字幕），自己上傳到 YouTube。
5. 稿子改了再跑同一行就好，只會重念改過的句子。

想全自動（定時等稿、做片、上傳、通知）再看下面的選配功能。

### 有每日數據的題材（`us-stocks` 主題）

這個主題多做一件事：用 [yfinance](https://github.com/ranaroussi/yfinance) 抓 Yahoo Finance 的真實收盤，畫數據卡、走勢圖、底部跑馬燈和個別項目的圖卡；講稿裡的數字只拿來念，不拿來畫圖。
想做別的市場（台股、日股、匯率、加密貨幣）：複製 `themes/us-stocks`，改 `theme.json` 的 `data.tickers`（Yahoo Finance 的代號）和 `data.companies`（名稱 → 代號）。
它的範例講稿用的是 2026-11-13 這一天，所以要放在 `episodes/2026-11-13/`。要接別的資料來源需要改 `tools/make_day.py` 的 `market()`。此主題產出的內容不構成投資建議。

## 選配功能（預設全部關閉）

金鑰一律放在 `.env`（`cp env.example .env`，這個檔不會進 git），開關在 `config.json`。

| 功能 | 怎麼開 | 要準備什麼 |
|---|---|---|
| **付費配音** | `config.json` 的 `engine` 改成 `breeze-api`／`minimax`／`gemini` | 各家的 API 金鑰寫進 `.env`。BreezeBlue 另外要 `BREEZE_VOICE_ID`（可用 `tools/breeze_voice.py` 用文字描述設計一個聲音）。`fallback_engine` 可以填主引擎失敗時的備援 |
| **念錯自動重念＋聽寫檢查** | `whisper.enabled: true` | `pip install openai-whisper pypinyin opencc-python-reimplemented`。每句給 Whisper 聽寫、比拼音，沒念對的重念（`<引擎>.retakes`）；做完再對整支旁白打一個分數寫進 `report.json` |
| **片頭／片尾音效** | `config.json` 填 `jingle`（寫法見 `tools/jingle.py` 開頭） | 自備兩個音效檔放進 `remotion/public/brand/`。這個 repo 不附音效；預設片頭片尾是無聲的 |
| **排程** | 用 `tools/daily.py`，範例在 `examples/launchd/` | 它會等講稿出現（60 秒沒再被改才開工）、做片、再依設定上傳與通知；過了截止時間沒稿只會通知，不會自己寫稿 |
| **從 Google Drive 抓稿** | `fetch.enabled: true` | 兩條路擇一：(a) 最簡單：裝「Google Drive 電腦版」，把 `episodes_dir` 指到同步下來的資料夾，不用開這個功能；(b) `tools/drive_fetch.py`：需要已登入的 [Claude Code](https://claude.com/claude-code) 指令列工具，並在 claude.ai 接上 Google Drive 連接器 |
| **上傳 YouTube** | `upload.enabled: true`，`upload.privacy` 預設 `private` | 走官方的 YouTube Data API：Google Cloud 專案＋OAuth 用戶端、`pip install google-api-python-client google-auth-oauthlib`，先跑一次 `tools/youtube_upload.py auth`。步驟與限制寫在 `tools/youtube_upload.py` 開頭 |
| **Telegram 通知** | `notify.telegram: true` | 跟 @BotFather 建 bot，把 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` 寫進 `.env` |
| **頻道頭像／橫幅／logo** | `remotion/src/Brand.tsx` 開頭有指令 | 用同一套版型產生頻道美術 |

Google 規定：還沒通過稽核的 API 專案，上傳的影片會被鎖成私人；通過之前就是先傳成私人，再自己到 YouTube Studio 按公開。
上傳的影片一律勾選「變造或合成內容」。AI 生成內容要能營利，內容必須有自己的整理與觀點，不能只是翻譯或朗讀別人的東西。

## 測試狀態（照實寫）

| 功能 | 狀態 |
|---|---|
| 做片（內建語音 `say`、五個內附主題各做出一支、縮圖、說明欄、字幕檔） | ✅ 實測 |
| 一行安裝 `./quickstart.sh` | ✅ 實測：全新資料夾只跑這一行就做出影片；缺工具時會列出要裝什麼 |
| 排程總管 `tools/daily.py` 手動模式 | ✅ 實測 |
| 免費線上語音 `edge` | ✅ 實測：念出聲音檔 |
| 念錯重念＋聽寫檢查（Whisper） | ✅ 實測聽寫檢查與逐句檢查；「重念」沒有實測（內建語音每次念的都一樣，用不到） |
| 主引擎失敗自動換備援引擎 | ✅ 實測 |
| 從 Google Drive 抓稿 `tools/drive_fetch.py` | ✅ 實測：抓到當天的稿；不存在的日期會清楚回報「還沒有」 |
| 付費配音 `breeze-api`、`minimax`、`gemini` | ⚠️ 只驗到：沒填金鑰會提示要填哪一個；填錯金鑰會印出服務回的錯誤、不會當掉。**沒有用真的金鑰念過** |
| 上傳 YouTube `tools/youtube_upload.py` | ⚠️ 只乾跑：`--dry-run` 檢查檔案、印出會送出的標題／說明／標籤；缺檔、沒授權都有清楚提示。**沒有真的上傳過** |
| Telegram 通知 | ⚠️ 只乾跑：沒填 token 會提示；`NOTIFY_DRY_RUN=1` 只印不送。**沒有真的送過訊息** |
| 片頭片尾音效產生器 `tools/jingle.py`、聲音設計 `tools/breeze_voice.py` | ❌ 沒測（要付費金鑰） |
| Linux、Windows | ❌ 沒測 |

遇到問題歡迎開 issue。

## 資料夾

```
quickstart.sh           一行裝好＋做出範例影片
AGENTS.md               給 AI 助手讀的操作說明（含主題檔每個欄位的解釋）
tools/make_day.py       講稿 → 影片（主程式）
tools/tts.py            配音引擎（要加新的引擎改這裡）
tools/daily.py          排程總管：等稿 → 做片 → 上傳 → 通知
tools/…                 其餘都是選配工具，每個檔案開頭有說明
remotion/src/Video.tsx  影片的動畫版型（React）
themes/                 主題
episodes/<日期>/         你的講稿與成品（不進 git）
work/                   暫存：每句配音的快取、渲染用資料（不進 git，可以刪）
```

## 常見問題

- **改了講稿重跑會全部重新配音嗎？** 不會。每句有快取，只重念改過的句子。
- **做片很慢** `config.json` 的 `render.concurrency` 可以指定同時渲染幾格（預設讓 Remotion 自己決定）。
- **字幕要燒進畫面** `burn_subtitles: true`。預設不燒，用 `captions.srt` 當 YouTube 的 CC 字幕。
- **配色跟我設的不一樣** 主題檔有填 `accents` 的話重點色會每天輪替；想固定就把 `accents` 拿掉，只留 `palette.accent`。

## 授權與第三方

- 本專案的程式碼、主題與範例講稿採 [MIT 授權](LICENSE)。
- [Remotion](https://www.remotion.dev/license) 有自己的授權：個人與小團隊免費，營利公司超過一定規模需要購買公司授權，使用前請讀它的條款。
- 字型 Noto Sans CJK 是 SIL Open Font License 1.1，由 `tools/get_fonts.py` 從官方 repo 下載，不隨本專案散布。
- `us-stocks` 主題的資料來自 Yahoo Finance（經 yfinance），使用範圍以 Yahoo 的條款為準。
- 各家 TTS 的輸出能不能商用、要不要標示，以各家條款為準。
