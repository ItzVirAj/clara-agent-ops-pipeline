# tests/test_ingest.py
import sys, json
sys.path.insert(0, ".")

from pipe.ingest    import run_ingest
from pipe.extract   import run_extract
from pipe.prmpt_gen import run_prmpt_gen

ing  = run_ingest(fpath="data/demo/test_demo.txt", call_type="demo")

print("\n── extract ──")
memo = run_extract(ing)

print("\n── prmpt gen ──")
spec = run_prmpt_gen(memo)

print("\n── spec summary ──")
for k, v in spec.items():
    if k == "sys_prompt":
        print(f"  sys_prompt : {str(v)[:100]}...")
    else:
        print(f"  {k:<14}: {v}")

print("\n── prompt preview ──")
print(spec["sys_prompt"][:600])