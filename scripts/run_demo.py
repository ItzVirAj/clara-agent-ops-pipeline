# scripts/run_demo.py
# pipeline A — process single demo file
# run: python scripts/run_demo.py <file_path>

import sys
import json
sys.path.insert(0, ".")

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path("cfg/.env"))

from pipe.ingest    import run_ingest
from pipe.extract   import run_extract
from pipe.prmpt_gen import run_prmpt_gen
from pipe.store     import reg_v1
from pipe.utils     import get_lgr

lgr = get_lgr("run_demo")


def run_demo_pipeline(fpath: str) -> dict:
    lgr.info(f"═══ PIPELINE A START | {Path(fpath).name} ═══")

    ing  = run_ingest(fpath=fpath, call_type="demo")
    memo = run_extract(ing)
    spec = run_prmpt_gen(memo)
    reg_v1(memo, spec)

    lgr.info(f"═══ PIPELINE A DONE  | acct_id: {memo['acct_id']} ═══")

    return {
        "acct_id"  : memo["acct_id"],
        "co_name"  : memo.get("co_name"),
        "open_qs"  : len(memo.get("open_qs", [])),
        "memo_path": f"out/accounts/{memo['acct_id']}/v1/memo.json",
        "spec_path": f"out/accounts/{memo['acct_id']}/v1/agent_spec.json"
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/run_demo.py <file_path>")
        print("ex   : python scripts/run_demo.py data/demo/bens_electric_demo.txt")
        sys.exit(1)

    result = run_demo_pipeline(sys.argv[1])

    print("\n── result ──")
    for k, v in result.items():
        print(f"  {k:<12}: {v}")