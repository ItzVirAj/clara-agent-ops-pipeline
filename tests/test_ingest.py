# tests/test_ingest.py
# tests ingestion + extraction together end to end

import sys
sys.path.insert(0, ".")

from pipe.ingest  import run_ingest
from pipe.extract import run_extract
import json

# ── run ingest
ing = run_ingest(
    fpath="data/demo/test_demo.txt",
    call_type="demo"
)

print("\n── ingest result ──")
for k, v in ing.items():
    if k == "raw_txt":
        print(f"  raw_txt   : {v[:80]}...")
    else:
        print(f"  {k:<10} : {v}")

# ── run extract
print("\n── running extraction ──")
memo = run_extract(ing)

print("\n── extracted memo ──")
print(json.dumps(memo, indent=2))