"""通知（選配，預設全關）：Telegram Bot、macOS 通知中心。不管有沒有開，都會寫一行到 logs/notify.log。
Telegram：跟 @BotFather 建一個 bot 拿 token，把 bot 加進聊天後查 chat id，寫進 .env 的 TELEGRAM_BOT_TOKEN、TELEGRAM_CHAT_ID，
再把 config.json 的 notify.telegram 改成 true。
環境變數 NOTIFY_DRY_RUN=1：只印出會送什麼，不真的送。"""
import json, subprocess, urllib.parse, urllib.request
from datetime import datetime

from common import CFG, ROOT, THEME, env


def send(text, escalate=False):
    n = CFG.get("notify", {})
    msg = f"{'⚠️ ' if escalate else ''}{THEME['channel']}｜{text}\n{datetime.now():%m/%d %H:%M}"
    logs = ROOT / "logs"; logs.mkdir(exist_ok=True)
    with open(logs / "notify.log", "a") as f:
        f.write(f"{datetime.now():%m-%d %H:%M} {'ESC ' if escalate else ''}{text}\n")
    print(msg, flush=True)
    if n.get("telegram"):
        token, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
        if not (token and chat):
            print("notify.telegram 開著，但 .env 沒有 TELEGRAM_BOT_TOKEN／TELEGRAM_CHAT_ID", flush=True)
        else:
            data = urllib.parse.urlencode({"chat_id": chat, "text": msg, "disable_web_page_preview": "true"}).encode()
            if env("NOTIFY_DRY_RUN"):
                print(f"乾跑（沒有送出）：Telegram chat {chat}，{len(data)} bytes", flush=True)
            else:
                try:
                    urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=15)
                except Exception as e:
                    print("telegram 送不出去：", type(e).__name__, getattr(e, "code", ""), flush=True)      # 不印 e 全文：錯誤訊息裡會帶網址（含 token）
    if n.get("macos"):
        subprocess.run(["osascript", "-e", f"display notification {json.dumps(text[:180], ensure_ascii=False)} with title {json.dumps(THEME['channel'], ensure_ascii=False)}"], check=False)
