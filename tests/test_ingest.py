# tests/test_ingest.py
import sys
sys.path.insert(0, ".")

from pipe.ingest import run_ingest

result = run_ingest(
    fpath="data/demo/test_demo.txt",
    call_type="demo"
)

print("\n── ingest result ──")
for k, v in result.items():
    if k == "raw_txt":
        print(f"  raw_txt  : {v[:80]}...")
    else:
        print(f"  {k:<10}: {v}")