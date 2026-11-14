#!/usr/bin/env python3
"""排程用的總管：等講稿 →（選配）去 Google Drive 抓 → 做片 →（選配）上傳 YouTube →（選配）通知。它不會自己寫稿。
- 等 episodes/<今天>/script.md（--weekly 等 weekly.md）出現，而且 60 秒沒再被改才開工
- 過了 config.json 的 schedule.daily_deadline／weekly_deadline 還沒稿就通知一聲、結束
- 同一天同一種只會發一次；同時只會有一個在跑
python3 tools/daily.py                       # 排程用：今天的每日
python3 tools/daily.py --weekly              # 排程用：今天的每週
python3 tools/daily.py --deadline 12:15      # 臨時改截止時間
python3 tools/daily.py 2026-11-13 [--weekly] # 手動補跑某天（不等）
排程範例見 examples/launchd/。"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CFG, ROOT, THEME, episodes_dir
from notify import send

LOG = ROOT / "logs"


def last_line(r):
    out = (r.stderr or r.stdout).strip().splitlines()
    return out[-1][:200] if out else "無輸出"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", nargs="?")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--deadline", help="HH:MM，蓋掉 config.json 的截止時間")
    a = ap.parse_args()
    LOG.mkdir(exist_ok=True)
    manual = a.day is not None
    day = a.day or datetime.now().strftime("%Y-%m-%d")
    kind = THEME["badge"]["weekly" if a.weekly else "daily"]
    d = episodes_dir() / day
    s = d / ("weekly.md" if a.weekly else "script.md")
    sch, fx, up_cfg = CFG.get("schedule", {}), CFG.get("fetch", {}), CFG.get("upload", {})
    hh, mm = map(int, (a.deadline or sch.get("weekly_deadline" if a.weekly else "daily_deadline", "08:00")).split(":"))
    deadline = datetime.now() if manual else datetime.now().replace(hour=hh, minute=mm, second=0)
    settle = sch.get("settle_sec", 60)
    next_fetch, auth_warned = time.time(), False      # 登入過期只通知一次
    while True:
        if s.exists() and time.time() - s.stat().st_mtime > settle:
            break
        if not s.exists() and not manual and fx.get("enabled") and time.time() >= next_fetch:
            next_fetch = time.time() + fx.get("every_sec", 600)
            try:
                from drive_fetch import fetch
                code, msg = fetch(day, a.weekly)
            except Exception as e:      # 抓不到就照舊等本機稿；留紀錄，不讓整個流程掛掉
                code, msg = 9, f"Drive 抓稿出錯：{e}"
            print(f"{datetime.now():%H:%M} {msg}", flush=True)
            with open(LOG / "drive-fetch.log", "a") as f:
                f.write(f"{datetime.now():%m-%d %H:%M} {msg[:160]}\n")
            if code == 2 or (code == 3 and not auth_warned):
                send(f"{day} {kind}：{msg}", escalate=True)
                auth_warned = auth_warned or code == 3
            if s.exists():
                os.utime(s, (time.time() - settle - 1, time.time() - settle - 1))   # 自己原子寫好的，不用再等
                continue
        if datetime.now() >= deadline and not s.exists():
            why = "（Drive 抓不了：claude CLI 登入過期，Drive 上可能其實有稿）" if auth_warned else ""
            send(f"{day} {kind}：{hh:02d}:{mm:02d} 還沒有講稿（{s}）{why}。稿子放好後手動跑 python3 tools/daily.py {day}{' --weekly' if a.weekly else ''}", escalate=True)
            return
        time.sleep(5)
    print(f"{datetime.now():%H:%M} 收到 {s}，開工", flush=True)
    t_detect = time.time()
    W = ["--weekly"] if a.weekly else []
    py = sys.executable
    rep_p = d / ("report-weekly.json" if a.weekly else "report.json")
    try:        # 排程重疊時曾經同一支片公開兩次 → 發過就不重跑＋檔案鎖
        if json.loads(rep_p.read_text()).get("youtube"):
            print(f"{day} {kind} 已經發過片（{rep_p}），不重跑", flush=True); return
    except (FileNotFoundError, ValueError):
        pass
    import fcntl
    lock = open(LOG / f".lock-{day}{'-weekly' if a.weekly else ''}", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"{day} {kind} 另一個 daily.py 正在做，不重跑", flush=True); return
    r = subprocess.run([py, str(ROOT / "tools/make_day.py"), day, "--skip-qc", *W], capture_output=True, text=True, cwd=ROOT)
    (LOG / f"{day}{'-weekly' if a.weekly else ''}.log").write_text(r.stdout + r.stderr)
    if r.returncode or not rep_p.exists():
        send(f"{day} {kind}製作失敗（exit {r.returncode}）：{last_line(r)}｜log：{LOG}", escalate=True)
        return
    rep = json.loads(rep_p.read_text())
    up, failed = "沒有上傳（config.json 的 upload.enabled 是關的）", False
    if up_cfg.get("enabled"):
        u = subprocess.run([py, str(ROOT / "tools/youtube_upload.py"), day, *W, "--privacy", up_cfg.get("privacy", "private")], capture_output=True, text=True, cwd=ROOT)
        rep = json.loads(rep_p.read_text())
        y = rep.get("youtube")
        failed = not y
        up = (f"已上傳：{y['url']}｜{y['privacy_requested']}｜{y['published_at_local'][11:16]}｜上傳 {y['upload_sec']} 秒" if y else f"上傳失敗：{last_line(u)}")
        if u.returncode and y:
            up += f"\n⚠️ {last_line(u)}"
    total = round(time.time() - t_detect)
    m, sec = divmod(int(rep["duration_sec"]), 60)
    steps = "、".join(f"{k} {v:.0f}s" for k, v in rep.get("steps_sec", {}).items())
    send(f"{day} {kind}（{m}:{sec:02d}，聲音 {rep['engine']}）\n標題：{rep.get('title', '')}\n{up}\n"
         f"偵測到稿→完成 {total // 60} 分 {total % 60} 秒｜{steps}\n資料夾：{d}", escalate=failed)
    if CFG.get("whisper", {}).get("enabled"):      # QC 不在發片路徑上，最後補跑；分數太低再提醒
        subprocess.run([py, str(ROOT / "tools/make_day.py"), day, "--qc-only", *W], capture_output=True, text=True, cwd=ROOT)
        q = json.loads(rep_p.read_text()).get("asr_similarity")
        if isinstance(q, (int, float)) and q < 0.85:
            send(f"{day} {kind} QC：語音辨識比對只有 {q}，可能有念錯的地方，請抽聽", escalate=True)


if __name__ == "__main__":
    main()
