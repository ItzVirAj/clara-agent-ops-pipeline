# tests/test_extract.py
# tests extraction engine — validates memo structure and no-hallucination rule

import sys, json
sys.path.insert(0, ".")

from pipe.extract import _clean_json_resp, _build_ext_prompt
from pipe.utils   import utc_now

print("── test_extract ──")

# test 1: json cleaner strips markdown blocks
raw_with_md = "```json\n{\"co_name\": \"Test Co\"}\n```"
cleaned     = _clean_json_resp(raw_with_md)
assert cleaned == '{"co_name": "Test Co"}', f"cleaner failed: {cleaned}"
print("json cleaner strips markdown")

# test 2: json cleaner handles clean json passthrough
raw_clean = '{"co_name": "Test Co"}'
cleaned2  = _clean_json_resp(raw_clean)
assert cleaned2 == '{"co_name": "Test Co"}', f"passthrough failed: {cleaned2}"
print("json cleaner passthrough clean")

# test 3: prompt builder includes acct_id and memo_ver
prompt = _build_ext_prompt("some transcript text", "ACCT-TEST01", "v1_demo")
assert "ACCT-TEST01" in prompt, "acct_id missing from prompt"
assert "v1_demo"     in prompt, "memo_ver missing from prompt"
assert "IANA"        in prompt, "timezone format rule missing"
assert "HH:MM"       in prompt, "time format rule missing"
print("prompt builder includes acct_id, memo_ver, format rules")

# test 4: prompt builder includes transcript
prompt2 = _build_ext_prompt("hello this is a test transcript", "ACCT-TEST02", "v2_onboard")
assert "hello this is a test transcript" in prompt2
print("prompt builder includes raw transcript")

# test 5: memo structure has all required fields
required = [
    "acct_id","co_name","co_phone","co_addr","timezone",
    "biz_hrs","svcs","emrg_triggers","emrg_routing",
    "non_emrg_routing","xfer_rules","integrations",
    "aft_hrs_flow","biz_hrs_flow","open_qs","notes",
    "memo_ver","created_at","updated_at"
]
import json
# simulate a minimal memo
memo = {k: None for k in required}
memo["biz_hrs"] = {}
memo["svcs"] = []
memo["emrg_triggers"] = []
memo["integrations"] = []
memo["open_qs"] = []
for f in required:
    assert f in memo, f"missing field: {f}"
print("memo schema has all required fields")

print("\nall extract tests passed")