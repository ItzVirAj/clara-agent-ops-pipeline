# pipe/utils.py
# shared small helpers used across pipeline modules

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# load env once here, all modules import from utils
load_dotenv(dotenv_path=Path("cfg/.env"))

# ── logger setup ──────────────────────────────────────────
def get_lgr(name: str) -> logging.Logger:
    """
    returns a named logger writing to both console and logs/
    name → module name ex 'ingest', 'extract'
    """
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(exist_ok=True)

    lgr = logging.getLogger(name)
    lgr.setLevel(logging.DEBUG)

    # avoid duplicate handlers if called twice
    if lgr.handlers:
        return lgr

    fmt = logging.Formatter(
        "%(asctime)s | %(name)-10s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # console handler
    c_hdlr = logging.StreamHandler()
    c_hdlr.setLevel(logging.INFO)
    c_hdlr.setFormatter(fmt)

    # file handler - one log per day
    log_fname = log_dir / f"run_{datetime.now().strftime('%Y%m%d')}.log"
    f_hdlr = logging.FileHandler(log_fname, encoding="utf-8")
    f_hdlr.setLevel(logging.DEBUG)
    f_hdlr.setFormatter(fmt)

    lgr.addHandler(c_hdlr)
    lgr.addHandler(f_hdlr)

    return lgr


# ── id generation ─────────────────────────────────────────
def gen_acct_id() -> str:
    """
    generates a short unique account id
    format → ACCT-XXXXXXXX (8 char hex)
    """
    return f"ACCT-{uuid.uuid4().hex[:8].upper()}"


# ── timestamp ─────────────────────────────────────────────
def utc_now() -> str:
    """returns current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat()


# ── file helpers ──────────────────────────────────────────
def read_txt(fpath: str | Path) -> str:
    """reads a text file and returns stripped string"""
    with open(fpath, "r", encoding="utf-8") as f:
        return f.read().strip()


def write_json(data: dict, fpath: str | Path) -> None:
    """writes dict to json file, creates dirs if needed"""
    fpath = Path(fpath)
    fpath.parent.mkdir(parents=True, exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_json(fpath: str | Path) -> dict:
    """reads json file and returns dict"""
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


# ── output path builder ───────────────────────────────────
def get_acct_dir(acct_id: str, ver: str) -> Path:
    """
    returns path to versioned account output dir
    ex → out/accounts/ACCT-AB12CD34/v1
    creates dirs if they don't exist
    """
    base = Path(os.getenv("ACCT_OUT_DIR", "out/accounts"))
    p = base / acct_id / ver
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── audio file checker ────────────────────────────────────
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4"}
TXT_EXTS   = {".txt", ".json"}

def detect_src_type(fpath: str | Path) -> str:
    """
    detects if input is audio or transcript
    returns 'audio' or 'transcript'
    raises ValueError if unrecognized
    """
    ext = Path(fpath).suffix.lower()
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in TXT_EXTS:
        return "transcript"
    raise ValueError(f"unrecognized file type: {ext} — expected {AUDIO_EXTS | TXT_EXTS}")