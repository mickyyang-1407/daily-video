"""共用：讀 .env、config.json、主題（themes/<name>/theme.json）。其他工具都從這裡拿設定，不各自寫一份。"""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path=ROOT / ".env"):
    """把 .env 的 KEY=VALUE 放進環境變數（已經存在的環境變數優先）。金鑰只放 .env，不放 config.json、不進 git。"""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.removeprefix("export ").split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def env(name, default=""):
    return os.environ.get(name, default).strip()


def _read(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        sys.exit(f"找不到 {path}")
    except ValueError as e:
        sys.exit(f"{path} 不是合法的 JSON：{e}")


load_env()
_cfg_path = ROOT / "config.json"
if not _cfg_path.exists():          # 還沒複製設定檔也能跑範例
    _cfg_path = ROOT / "config.example.json"
CFG = _read(_cfg_path)
THEME_DIR = ROOT / "themes" / CFG.get("theme", "us-stocks")
THEME = _read(THEME_DIR / "theme.json")


def episodes_dir():
    p = Path(os.path.expanduser(CFG.get("episodes_dir", "episodes")))
    return p if p.is_absolute() else ROOT / p


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)
