# tests/test_prmpt_gen.py
# tests prompt generator — biz_hrs formatter, spec structure

import sys
sys.path.insert(0, ".")

from pipe.prmpt_gen import _biz_hrs_str, _build_spec
from pipe.utils     import utc_now

print("── test_prmpt_gen ──")

# test 1: biz_hrs_str with active days
biz = {
    "mon": {"open": "08:00", "close": "17:00", "active": True},
    "tue": {"open": "08:00", "close": "17:00", "active": True},
    "wed": {"open": "08:00", "close": "17:00", "active": True},
    "thu": {"open": "08:00", "close": "17:00", "active": True},
    "fri": {"open": "08:00", "close": "17:00", "active": True},
    "sat": {"open": None,    "close": None,    "active": False},
    "sun": {"open": None,    "close": None,    "active": False},
}
hrs_str = _biz_hrs_str(biz)
assert "08:00" in hrs_str, f"open time missing: {hrs_str}"
assert "17:00" in hrs_str, f"close time missing: {hrs_str}"
assert "Mon"   in hrs_str, f"Mon missing: {hrs_str}"
print(f"biz_hrs_str: {hrs_str}")

# test 2: biz_hrs_str with empty dict
empty_str = _biz_hrs_str({})
assert empty_str == "Not specified", f"empty should return 'Not specified': {empty_str}"
print("biz_hrs_str handles empty dict")

# test 3: biz_hrs_str with no active days
no_active = {
    "mon": {"open": None, "close": None, "active": False},
    "sat": {"open": None, "close": None, "active": False},
}
no_active_str = _biz_hrs_str(no_active)
assert no_active_str == "Not specified", f"no active should be 'Not specified': {no_active_str}"
print("biz_hrs_str handles no active days")

# test 4: spec structure has all required fields
memo = {
    "acct_id"        : "ACCT-TEST01",
    "co_name"        : "Test Electric",
    "biz_hrs"        : biz,
    "emrg_triggers"  : ["fire alarm", "power outage"],
    "emrg_routing"   : {"primary_ph": "555-0101"},
    "non_emrg_routing": {"contact_ph": "555-0202"},
    "xfer_rules"     : {"timeout_sec": 30, "retry_count": 2, "fail_msg": "Sorry, try again."},
    "memo_ver"       : "v1_demo"
}
spec = _build_spec(memo, "You are Clara...", "v1_demo")

required_keys = [
    "acct_id","agent_name","voice_style","lang",
    "sys_prompt","key_vars","xfer_protocol","fallbk",
    "spec_ver","created_at","updated_at"
]
for k in required_keys:
    assert k in spec, f"missing key in spec: {k}"
print("spec has all required fields")

# test 5: spec values populated correctly
assert spec["acct_id"]              == "ACCT-TEST01",      "acct_id wrong"
assert spec["agent_name"]           == "Clara — Test Electric", "agent_name wrong"
assert spec["lang"]                 == "en-US",            "lang wrong"
assert spec["xfer_protocol"]["emrg"]["ph"] == "555-0101",  "emrg ph wrong"
assert spec["fallbk"]["collect_cb"] == True,               "collect_cb wrong"
print("spec values populated correctly")

print("\nall prmpt_gen tests passed")