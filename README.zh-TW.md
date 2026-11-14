# 每日自動出片流水線（講稿 → YouTube 影片）

[English](README.md)｜繁體中文

把一份 Markdown 講稿，自動做成一支有配音、動態圖卡、章節、字幕檔、縮圖、標題與說明欄的 16:9 影片。
講稿可以自己寫，也可以交給任何 AI 每天寫；這個專案只負責「拿到稿之後」的所有事。

- **免費就能跑**：預設用 macOS 內建語音配音，不需要任何金鑰。
- **主題可換**：內附「美股日報」和「一般新聞」兩個主題。換題材只要改一個設定檔＋一份給寫手的說明，不用改程式。
- **其他都是選配、預設關閉**：付費配音、從 Google Drive 抓稿、上傳 YouTube、Telegram 通知、排程。

> 內附的美股主題只是範例，影片內容不構成投資建議。旁白目前只支援中文（數字、日期會轉成中文念法）。

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

它會先檢查電腦缺什麼（缺了會告訴你要貼哪一行去裝），然後自動裝好、做出範例影片並打開。全程大約 3–5 分鐘，重跑也沒關係。
影片在 `episodes/2026-11-13/video.mp4`（約 1 分 40 秒）。

### 方式三：手動一步一步來

想知道每一步在做什麼，或不是用 Mac 的人看這裡。要先有：macOS、Python 3.10 以上、Node.js 18 以上、ffmpeg（`brew install ffmpeg node`）。

```bash
git clone https://github.com/mickyyang-1407/daily-video.git && cd daily-video

# 1. Python 套件
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 動畫引擎（Remotion）。第一次渲染會自動下載一個無畫面的瀏覽器
(cd remotion && npm install)

# 3. 字型（選配但建議）：下載思源黑體繁中，約 68 MB。不下載就用系統的中文字型
.venv/bin/python tools/get_fonts.py

# 4. 設定檔：先照抄範例就能跑
cp config.example.json config.json

# 5. 放一份範例講稿，做片
mkdir -p episodes/2026-11-13
cp themes/us-stocks/sample/script.md episodes/2026-11-13/
.venv/bin/python tools/make_day.py 2026-11-13
```

做完會印出 `完成 {...}`，影片在 `episodes/2026-11-13/video.mp4`（範例約 1 分 40 秒；Apple Silicon 的 Mac 大約 2 分鐘做完）。

內建語音預設用台灣中文的「美佳」（Meijia）。聽起來不對或報錯：到「系統設定 → 輔助使用 → 語音內容 → 系統聲音 → 管理聲音」下載中文（台灣）的聲音，
或用 `say -v '?'` 看這台 Mac 有哪些聲音，把名字填進 `config.json` 的 `say.voice`。

不是 macOS：把 `config.json` 的 `engine` 改成 `edge`（先 `pip install edge-tts`，免費線上語音，但走的是非官方介面，可能隨時失效），或用付費引擎。Linux／Windows 沒有實測過。

## 換成你自己的題材

一個「主題」就是 `themes/<名字>/` 一個資料夾：

| 檔案 | 用途 |
|---|---|
| `theme.json` | 頻道名、印章字、片頭標語、段落規則、畫面上的固定文字、配色、要不要抓市場資料、說明欄與標籤的寫法 |
| `PROMPT-for-writer.md` | 給「寫手 AI」的交稿說明：整份貼給它，它就會照格式寫稿 |
| `sample/script.md` | 一份範例講稿 |

做法：

1. 複製最接近的主題：`cp -r themes/plain-news themes/my-topic`（沒有數據圖卡的題材從 `plain-news` 開始；有每日行情的從 `us-stocks` 開始）。
2. 改 `themes/my-topic/theme.json`。最常改的：
   - `channel`、`stamp`（片頭蓋下去的印章字，2–3 個字最好看）、`tagline`、`badge`
   - `text`：畫面上的固定句子（片尾提醒、訂閱按鈕…）
   - `verdict`：講稿裡「判定：同意。」這種開頭會變成彩色印章；`prefix` 是前面那個詞，`options` 是可用的字和顏色。不要印章就整個拿掉
   - `palette`／`accents`：配色（`accents` 會每天輪替）
   - `publish`：說明欄第一行的 AI 揭露句、hashtag、固定標籤
   - `sections`：哪些段落標題有特殊意義（見下面「講稿格式」）
3. 改 `PROMPT-for-writer.md`，讓段落標題跟 `theme.json` 對得上。
4. `config.json` 的 `"theme"` 改成 `"my-topic"`，用你的範例稿跑一次 `make_day.py` 看畫面。

美股主題多做的事（`theme.json` 的 `data`）：用 [yfinance](https://github.com/ranaroussi/yfinance) 抓 Yahoo Finance 的真實收盤，畫指數卡、走勢圖、底部跑馬燈和個股圖卡；
講稿裡的數字只拿來念，不拿來畫圖。想做台股、日股、加密貨幣：改 `data.tickers`（Yahoo Finance 的代號）和 `data.companies`（公司名 → 代號）就好。
`"data": {"provider": "none"}` 則完全不抓資料。要接別的資料來源需要改 `tools/make_day.py` 的 `market()`。

### 講稿格式

```markdown
# 每日美股｜11/13            ← 第一行（主題的 script_head）

## 標題候選                   ← 含「標題」：3 個影片標題，不會被念
- …

## 開場                       ← 第一段＝開場大字
…

## 盤勢回顧                   ← 含「盤勢／收盤…」（sections.market）：指數卡＋走勢圖（只有開了市場資料的主題）
- 一行一條

## 今日圖表                   ← 含「圖表」：照你給的資料點畫長條／折線圖，不會被念
- 圖名：…
- 類型：長條圖
- 單位：%
- 資料點：
  - 名稱：數字
- 來源：https://…

## 大咖怎麼說                 ← 其他段落：一條一條亮起來
### 小標｜來源｜日期          ← ### 會顯示在段落標題右邊，也會變成章節
- 我們的看法：判定：部分同意。…   ← 蓋印章

## 來源                       ← 含「來源／參考」：連結會放進說明欄，不會被念
- https://…

## 不公開備註                 ← 含「不公開」：整段不念、不進畫面、不進說明欄
```

每週一支的總整理：稿子存成 `weekly.md`，指令加 `--weekly`，產出檔名會多 `-weekly`。

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
| 做片（內建語音 `say`、兩個主題、Remotion 渲染、縮圖、說明欄、字幕檔） | ✅ 實測：全新資料夾照本頁步驟從頭走完 |
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
AGENTS.md               給 AI 助手讀的操作說明
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
- **yfinance 抓不到資料** Yahoo Finance 偶爾會擋；等一下再跑，或更新 `yfinance`。

## 授權與第三方

- 本專案的程式碼、主題與範例講稿採 [MIT 授權](LICENSE)。
- [Remotion](https://www.remotion.dev/license) 有自己的授權：個人與小團隊免費，營利公司超過一定規模需要購買公司授權，使用前請讀它的條款。
- 字型 Noto Sans CJK 是 SIL Open Font License 1.1，由 `tools/get_fonts.py` 從官方 repo 下載，不隨本專案散布。
- 市場資料來自 Yahoo Finance（經 yfinance），使用範圍以 Yahoo 的條款為準。
- 各家 TTS 的輸出能不能商用、要不要標示，以各家條款為準。
