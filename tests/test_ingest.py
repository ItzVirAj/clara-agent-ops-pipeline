# tests/test_ingest.py
import sys, json
sys.path.insert(0, ".")

from pipe.ingest    import run_ingest
from pipe.extract   import run_extract
from pipe.prmpt_gen import run_prmpt_gen
from pipe.store     import reg_v1, reg_v2, get_acct, list_accts
from pipe.patch     import run_patch

# ─────────────────────────────────────────────
# PIPELINE A — demo call
# ─────────────────────────────────────────────
print("\n══ PIPELINE A ══")
ing_v1  = run_ingest(fpath="data/demo/test_demo.txt", call_type="demo")
memo_v1 = run_extract(ing_v1)
spec_v1 = run_prmpt_gen(memo_v1)
reg_v1(memo_v1, spec_v1)

acct_id = memo_v1["acct_id"]
print(f"\n  acct_id : {acct_id}")
print(f"  status  : {get_acct(acct_id)['status']}")

# ─────────────────────────────────────────────
# PIPELINE B — onboarding call (simulated)
# we reuse same file but pretend it's onboard
# with extra fields filled in
# ─────────────────────────────────────────────
print("\n══ PIPELINE B — patch simulation ══")

# simulate onboard extraction adding new fields
v2_extra = {
    "co_phone"  : "312-555-0000",
    "co_addr"   : "123 Main St, Chicago IL 60601",
    "svcs"      : ["fire alarm inspection", "sprinkler service", "suppression systems"],
    "xfer_rules": {
        "timeout_sec": 30,
        "retry_count": 2,
        "fail_msg"   : "I'm sorry, I couldn't reach our team. Someone will call you back shortly."
    },
    "non_emrg_routing": {
        "type"        : "transfer",
        "contact_name": "Office",
        "contact_ph"  : "312-555-0000",
        "notes"       : "transfer to main office line"
    },
    "aft_hrs_flow" : "After hours: check emergency → transfer on-call → fallback message",
    "biz_hrs_flow" : "Business hours: route to office → transfer tech if needed",
    "integrations" : ["ServiceTrade"],
    "open_qs"      : []
}

v2_memo_raw, changelog = run_patch(acct_id, v2_extra)
spec_v2 = run_prmpt_gen(v2_memo_raw)
reg_v2(v2_memo_raw, spec_v2)

print(f"\n  changes  : {changelog['total_changes']}")
print(f"  status   : {get_acct(acct_id)['status']}")

print("\n── changelog ──")
for c in changelog["changes"]:
    print(f"  [{c['action']}] {c['field']}")

print("\n── all accounts in db ──")
for a in list_accts():
    print(f"  {a['acct_id']} | {a['co_name']} | {a['status']}")