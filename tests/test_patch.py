# tests/test_patch.py
# tests patch engine — diff logic, deep patch, skip fields

import sys, copy
sys.path.insert(0, ".")

from pipe.patch import _diff, _deep_patch, SKIP_FIELDS

print("── test_patch ──")

# test 1: diff — filled (v1 null, v2 has value)
chg = _diff(None, "Chicago", "co_addr")
assert chg is not None,            "should detect fill"
assert chg["action"] == "filled",  f"wrong action: {chg['action']}"
assert chg["v2"]     == "Chicago", f"wrong v2: {chg['v2']}"
print(" diff detects filled field")

# test 2: diff — updated (both have values, different)
chg2 = _diff("old value", "new value", "co_name")
assert chg2 is not None,             "should detect update"
assert chg2["action"] == "updated",  f"wrong action: {chg2['action']}"
print("diff detects updated field")

# test 3: diff — no change (same value)
chg3 = _diff("same", "same", "co_name")
assert chg3 is None, "should return None for no change"
print("diff returns None for unchanged field")

# test 4: diff — v2 empty, keep v1
chg4 = _diff("keep this", None, "co_name")
assert chg4 is None, "should return None when v2 is empty"
print("diff keeps v1 when v2 is empty")

# test 5: deep patch fills nulls
v1 = {"co_name": None, "timezone": "America/Chicago", "svcs": []}
v2 = {"co_name": "Test Co", "svcs": ["electrical"]}
patched, changes = _deep_patch(v1, v2)
assert patched["co_name"]  == "Test Co",           f"co_name wrong: {patched['co_name']}"
assert patched["timezone"] == "America/Chicago",   "timezone should be unchanged"
assert patched["svcs"]     == ["electrical"],      f"svcs wrong: {patched['svcs']}"
assert len(changes) == 2,                          f"expected 2 changes, got {len(changes)}"
print("deep patch fills nulls, preserves existing")

# test 6: deep patch handles nested objects
v1_n = {"emrg_routing": {"primary_name": "Ben", "primary_ph": None}}
v2_n = {"emrg_routing": {"primary_ph": "403-555-0101"}}
patched_n, changes_n = _deep_patch(v1_n, v2_n)
assert patched_n["emrg_routing"]["primary_name"] == "Ben",          "primary_name should be preserved"
assert patched_n["emrg_routing"]["primary_ph"]   == "403-555-0101", "primary_ph should be filled"
print("deep patch handles nested objects")

# test 7: skip fields are defined
assert "acct_id"    in SKIP_FIELDS, "acct_id should be in skip fields"
assert "memo_ver"   in SKIP_FIELDS, "memo_ver should be in skip fields"
assert "created_at" in SKIP_FIELDS, "created_at should be in skip fields"
print("skip fields defined correctly")

print("\nall patch tests passed")