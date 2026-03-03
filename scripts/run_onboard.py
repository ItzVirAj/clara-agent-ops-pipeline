# scripts/run_onboard.py
# pipeline B — process single onboarding file
# run: python scripts/run_onboard.py <file_path> <acct_id>

import sys
import json
sys.path.insert(0, ".")

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path("cfg/.env"))

from pipe.ingest    import run_ingest
from pipe.extract   import run_extract
from pipe.patch     import run_patch
from pipe.prmpt_gen import run_prmpt_gen
from pipe.store     import reg_v2, get_acct
from pipe.utils     import get_lgr

lgr = get_lgr("run_onboard")


def run_onboard_pipeline(fpath: str, acct_id: str) -> dict:
    lgr.info(f"═══ PIPELINE B START | {Path(fpath).name} | {acct_id} ═══")

    # verify v1 exists
    acct = get_acct(acct_id)
    if not acct:
        raise ValueError(
            f"acct_id {acct_id} not found in registry — run demo pipeline first"
        )

    # ingest + extract onboard call
    ing      = run_ingest(fpath=fpath, acct_id=acct_id, call_type="onboard")
    memo_raw = run_extract(ing)

    # patch v1 → v2
    v2_memo, changelog = run_patch(acct_id, memo_raw)

    # generate v2 spec
    spec_v2 = run_prmpt_gen(v2_memo)

    # register v2
    reg_v2(v2_memo, spec_v2)

    lgr.info(f"═══ PIPELINE B DONE  | acct_id: {acct_id} ═══")

    return {
        "acct_id"    : acct_id,
        "co_name"    : v2_memo.get("co_name"),
        "changes"    : changelog["total_changes"],
        "open_qs"    : len(changelog.get("open_qs_remaining", [])),
        "memo_path"  : f"out/accounts/{acct_id}/v2/memo.json",
        "spec_path"  : f"out/accounts/{acct_id}/v2/agent_spec.json",
        "changelog"  : f"out/accounts/{acct_id}/changelog.json"
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python scripts/run_onboard.py <file_path> <acct_id>")
        print("ex   : python scripts/run_onboard.py data/onboard/bens_electric_onboard.m4a ACCT-B318046B")
        sys.exit(1)

    result = run_onboard_pipeline(sys.argv[1], sys.argv[2])

    print("\n── result ──")
    for k, v in result.items():
        print(f"  {k:<12}: {v}")