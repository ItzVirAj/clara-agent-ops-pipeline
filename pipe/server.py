# pipe/server.py
# flask backend — serves dashboard + triggers pipeline runs

import os
import sys
import json
import threading
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path("cfg/.env"))

from pipe.store  import list_accts, init_db
from pipe.utils  import get_lgr, read_json

lgr = Flask(__name__)
lgr.config["PROPAGATE_EXCEPTIONS"] = True

app = Flask(__name__)
BASE = Path(__file__).parent.parent  # project root
OUTPUTS = BASE / "outputs"
log     = get_lgr("server")

RUN_LOG = {}   # acct_id or "batch" → list of log lines


# ── static dashboard files ────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(OUTPUTS), "dashboard.html")

@app.route("/dashboard.css")
def css():
    return send_from_directory(str(OUTPUTS), "dashboard.css")

@app.route("/dashboard.js")
def js():
    return send_from_directory(str(OUTPUTS), "dashboard.js")


# ── api: get all accounts from sqlite ────────────────────
@app.route("/api/accounts")
def api_accounts():
    try:
        init_db()
        accts = list_accts()
        return jsonify({"ok": True, "accounts": accts})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── api: get batch report ─────────────────────────────────
@app.route("/api/batch_report")
def api_batch_report():
    rpt = OUTPUTS / "batch_report.json"
    if not rpt.exists():
        return jsonify({"ok": False, "error": "batch_report.json not found"})
    return jsonify({"ok": True, "report": read_json(rpt)})


# ── api: get changelog for account ───────────────────────
@app.route("/api/changelog/<acct_id>")
def api_changelog(acct_id):
    cl = OUTPUTS / "accounts" / acct_id / "changelog.json"
    if not cl.exists():
        return jsonify({"ok": False, "error": "changelog not found"})
    return jsonify({"ok": True, "changelog": read_json(cl)})


# ── api: get memo for account ─────────────────────────────
@app.route("/api/memo/<acct_id>/<ver>")
def api_memo(acct_id, ver):
    memo = OUTPUTS / "accounts" / acct_id / ver / "memo.json"
    if not memo.exists():
        return jsonify({"ok": False, "error": "memo not found"})
    return jsonify({"ok": True, "memo": read_json(memo)})


# ── api: get run log ──────────────────────────────────────
@app.route("/api/log/<run_key>")
def api_log(run_key):
    lines = RUN_LOG.get(run_key, [])
    return jsonify({"ok": True, "lines": lines})


# ── api: run batch ────────────────────────────────────────
@app.route("/api/run/batch", methods=["POST"])
def api_run_batch():
    RUN_LOG["batch"] = []

    def _run():
        try:
            from scripts.run_batch import run_batch
            RUN_LOG["batch"].append("═══ BATCH START ═══")
            summary = run_batch()
            RUN_LOG["batch"].append(f"═══ BATCH DONE — {summary['succeeded']}/{summary['total']} succeeded ═══")
        except Exception as e:
            RUN_LOG["batch"].append(f"ERROR: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "run_key": "batch"})


# ── api: run demo pipeline (pipeline A) ───────────────────
@app.route("/api/run/demo", methods=["POST"])
def api_run_demo():
    data  = request.json or {}
    fpath = data.get("fpath")

    if not fpath:
        return jsonify({"ok": False, "error": "fpath required"}), 400

    run_key = f"demo_{Path(fpath).stem}"
    RUN_LOG[run_key] = []

    def _run():
        try:
            from scripts.run_demo import run_demo_pipeline
            RUN_LOG[run_key].append(f"Starting Pipeline A → {fpath}")
            result = run_demo_pipeline(fpath)
            RUN_LOG[run_key].append(f"Done — acct_id: {result['acct_id']}")
            RUN_LOG[run_key].append(f"Open Qs: {result['open_qs']}")
            RUN_LOG[run_key].append(f"ACCT_ID:{result['acct_id']}")
        except Exception as e:
            RUN_LOG[run_key].append(f"ERROR: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "run_key": run_key})


# ── api: run onboard pipeline (pipeline B) ────────────────
@app.route("/api/run/onboard", methods=["POST"])
def api_run_onboard():
    data    = request.json or {}
    fpath   = data.get("fpath")
    acct_id = data.get("acct_id")

    if not fpath or not acct_id:
        return jsonify({"ok": False, "error": "fpath and acct_id required"}), 400

    run_key = f"onboard_{acct_id}"
    RUN_LOG[run_key] = []

    def _run():
        try:
            from scripts.run_onboard import run_onboard_pipeline
            RUN_LOG[run_key].append(f"Starting Pipeline B → {fpath}")
            result = run_onboard_pipeline(fpath, acct_id)
            RUN_LOG[run_key].append(f"Done — changes: {result['changes']}")
            RUN_LOG[run_key].append(f"Open Qs remaining: {result['open_qs']}")
        except Exception as e:
            RUN_LOG[run_key].append(f"ERROR: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "run_key": run_key})


# ── api: list data files ──────────────────────────────────
@app.route("/api/files")
def api_files():
    demo_dir    = Path(os.getenv("DATA_DEMO_DIR",    "data/demo"))
    onboard_dir = Path(os.getenv("DATA_ONBOARD_DIR", "data/onboard"))

    audio_exts = {".mp3", ".wav", ".m4a", ".flac"}
    txt_exts   = {".txt", ".json"}
    all_exts   = audio_exts | txt_exts

    def _list(d):
        if not d.exists():
            return []
        return [
            f.name for f in d.iterdir()
            if f.suffix.lower() in all_exts
            and not f.name.startswith(".")
            and "gitkeep" not in f.name
        ]

    return jsonify({
        "ok"     : True,
        "demo"   : sorted(_list(demo_dir)),
        "onboard": sorted(_list(onboard_dir))
    })


# ── start server ──────────────────────────────────────────
if __name__ == "__main__":
    log.info("starting Clara dashboard at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)