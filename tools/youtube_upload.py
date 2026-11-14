#!/usr/bin/env python3
"""選配：用官方 YouTube Data API v3 上傳某天的影片。
python3 tools/youtube_upload.py auth                       # 第一次：開瀏覽器登入頻道帳號授權（只做一次）
python3 tools/youtube_upload.py 2026-11-13 [--weekly] [--privacy public|private|unlisted]
python3 tools/youtube_upload.py 2026-11-13 --dry-run        # 只檢查檔案、印出會送出的內容，不連線、不上傳
要準備：pip install google-api-python-client google-auth-oauthlib；在 Google Cloud Console 建專案、啟用 YouTube Data API v3、
建 OAuth 用戶端（桌面應用程式），把下載的 JSON 存成 <YOUTUBE_OAUTH_DIR>/youtube-client.json（預設 ~/.config/daily-video/）。
- 授權後自動產生 youtube-token.json；這兩個檔都是憑證，不要放進 repo
- 一律勾選「變造或合成內容」（containsSyntheticMedia）、非兒童內容
- 結果寫進 report(-weekly).json 的 youtube 欄位
⚠️ Google 規定：還沒通過 API 稽核的專案，用 API 上傳的影片會被鎖成私人；通過前只能先傳成私人，再到 Studio 手動公開。"""
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CFG, THEME, env, episodes_dir

LANG = THEME.get("language", "zh-TW")
CONF = Path(env("YOUTUBE_OAUTH_DIR", "~/.config/daily-video")).expanduser()
CLIENT, TOKEN = CONF / "youtube-client.json", CONF / "youtube-token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


NEED_LIBS = "上傳要先裝套件：pip install google-api-python-client google-auth-oauthlib"


def creds(interactive=False):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        sys.exit(NEED_LIBS)
    c = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if c and c.expired and c.refresh_token:
        c.refresh(Request())
    if not c or not c.valid:
        if not interactive:
            sys.exit("YouTube 還沒授權：先跑 python3 tools/youtube_upload.py auth")
        if not CLIENT.exists():
            sys.exit(f"缺 {CLIENT}：到 Google Cloud Console 建 OAuth 用戶端（桌面應用程式）、啟用 YouTube Data API v3，下載 JSON 放到這裡")
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            sys.exit(NEED_LIBS)
        c = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES).run_local_server(port=0)
    CONF.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(c.to_json()); TOKEN.chmod(0o600)
    return c


def upload(day, weekly, privacy, dry_run=False):
    d = episodes_dir() / day
    n = (lambda f: f.replace(".", "-weekly.", 1)) if weekly else (lambda f: f)
    rep_p = d / n("report.json")
    missing = [n(f) for f in ("report.json", "video.mp4", "titles.txt", "description.md", "tags.txt", "thumbnail.jpg") if not (d / n(f)).exists()]
    if missing:
        sys.exit(f"{d} 缺 {'、'.join(missing)}：先跑 python3 tools/make_day.py {day}{' --weekly' if weekly else ''}")
    rep = json.loads(rep_p.read_text())
    title = (d / n("titles.txt")).read_text().splitlines()[0].strip()[:100]
    desc = (d / n("description.md")).read_text()[:4900]
    tags = [t.strip() for t in (d / n("tags.txt")).read_text().split(",") if t.strip()][:30]
    body = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": THEME["publish"].get("youtube_category", "25"), "defaultLanguage": LANG, "defaultAudioLanguage": LANG},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
    if dry_run:      # 只檢查、不連線、不上傳
        mb = (d / n("video.mp4")).stat().st_size / 1e6
        print("乾跑（沒有上傳）：", json.dumps({"video": f"{mb:.1f} MB", "privacy": privacy, **body["snippet"], "description": desc[:60] + "…"}, ensure_ascii=False))
        print("授權檔：", "有" if TOKEN.exists() else f"還沒有（{TOKEN}）→ 先跑 python3 tools/youtube_upload.py auth")
        return
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        sys.exit(NEED_LIBS)
    yt = build("youtube", "v3", credentials=creds(), cache_discovery=False)
    t0 = time.time()
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(d / n("video.mp4")), chunksize=16 << 20, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(d / n("thumbnail.jpg")))).execute()
        thumb = "ok"
    except Exception as e:                 # 頻道沒驗證電話時不能自訂縮圖；影片照常
        thumb = f"failed: {e}"[:200]
    st = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    rep["youtube"] = {"url": f"https://youtu.be/{vid}", "privacy_requested": privacy, "privacy_now": st.get("privacyStatus"),
                      "upload_status": st.get("uploadStatus"), "published_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      "upload_sec": round(time.time() - t0, 1), "thumbnail": thumb}
    rep_p.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep["youtube"], ensure_ascii=False))
    if privacy == "public" and st.get("privacyStatus") != "public":
        sys.exit("要求公開但 YouTube 回傳的狀態不是 public（多半是 API 專案還沒通過稽核，被鎖成私人）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--privacy", default=CFG.get("upload", {}).get("privacy", "private"), choices=["public", "private", "unlisted"])
    ap.add_argument("--dry-run", action="store_true", help="只檢查檔案、印出會送出的標題／說明／標籤，不連線、不上傳")
    a = ap.parse_args()
    if a.day == "auth":
        creds(interactive=True); print("授權完成：", TOKEN)
    else:
        upload(a.day, a.weekly, a.privacy, a.dry_run)


if __name__ == "__main__":
    main()
