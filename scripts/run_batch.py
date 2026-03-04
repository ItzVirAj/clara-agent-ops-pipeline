# scripts/run_batch.py
# batch runner — handles all demo + onboard pairs
# matches files by name stem (ex: bens_electric_demo.txt ↔ bens_electric_onboard.m4a)
# run: python scripts/run_batch.py

import sys
import json
from pathlib import Path
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path("cfg/.env"))

from scripts.run_demo    import run_demo_pipeline
from scripts.run_onboard import run_onboard_pipeline
from pipe.store          import list_accts
from pipe.utils          import get_lgr, utc_now, write_json

lgr = get_lgr("run_batch")

DEMO_DIR    = Path("data/demo")
ONBOARD_DIR = Path("data/onboard")
AUDIO_EXTS  = {".mp3", ".wav", ".m4a", ".flac"}
TXT_EXTS    = {".txt", ".json"}


def _get_acct_files() -> list[dict]:
    """
    pairs demo + onboard files by matching stem prefix
    ex bens_electric_demo.txt + bens_electric_onboard.m4a
    returns list of paired dicts
    """
    demo_files = [
        f for f in DEMO_DIR.iterdir()
        if f.suffix.lower() in (AUDIO_EXTS | TXT_EXTS)
        and not f.name.startswith(".")
        and "test" not in f.name
    ]

    pairs = []
    for df in demo_files:
        # extract account prefix — everything before _demo
        if "_demo" not in df.stem:
            lgr.warning(f"skipping {df.name} — no '_demo' in filename")
            continue

        prefix = df.stem.replace("_demo", "")

        # find matching onboard file
        onboard_match = None
        for ext in list(AUDIO_EXTS) + list(TXT_EXTS):
            candidate = ONBOARD_DIR / f"{prefix}_onboard{ext}"
            if candidate.exists():
                onboard_match = candidate
                break

        if not onboard_match:
            lgr.warning(f"no onboard file found for: {prefix} — skipping pair")
            continue

        pairs.append({
            "prefix"  : prefix,
            "demo"    : df,
            "onboard" : onboard_match
        })

    return pairs


def run_batch() -> dict:
    lgr.info("═══ BATCH START ═══")

    pairs = _get_acct_files()
    lgr.info(f"found {len(pairs)} account pairs to process")

    results   = []
    succeeded = 0
    failed    = 0

    for pair in pairs:
        prefix = pair["prefix"]
        lgr.info(f"── processing: {prefix} ──")

        try:
            # pipeline A
            demo_result = run_demo_pipeline(str(pair["demo"]))
            acct_id     = demo_result["acct_id"]

            # pipeline B
            onboard_result = run_onboard_pipeline(str(pair["onboard"]), acct_id)

            results.append({
                "prefix"  : prefix,
                "acct_id" : acct_id,
                "status"  : "success",
                "changes" : onboard_result["changes"],
                "open_qs" : onboard_result["open_qs"]
            })
            succeeded += 1

        except Exception as e:
            lgr.error(f"failed: {prefix} | {e}")
            results.append({
                "prefix" : prefix,
                "status" : "failed",
                "error"  : str(e)
            })
            failed += 1

    # batch summary
    summary = {
        "batch_at"  : utc_now(),
        "total"     : len(pairs),
        "succeeded" : succeeded,
        "failed"    : failed,
        "results"   : results
    }

    # save batch report
    report_path = Path("outputs/batch_report.json")
    write_json(summary, report_path)
    lgr.info(f"batch report saved → {report_path}")

    lgr.info("═══ BATCH DONE ═══")
    lgr.info(f"total: {len(pairs)} | ok: {succeeded} | failed: {failed}")

    return summary


if __name__ == "__main__":
    summary = run_batch()

    print("\n── batch summary ──")
    print(f"  total     : {summary['total']}")
    print(f"  succeeded : {summary['succeeded']}")
    print(f"  failed    : {summary['failed']}")

    print("\n── per account ──")
    for r in summary["results"]:
        status = "✓" if r["status"] == "success" else "✗"
        print(f"  {status} {r['prefix']:<30} | {r.get('acct_id','N/A')} | changes: {r.get('changes','N/A')}")