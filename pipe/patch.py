# pipe/patch.py
# v1 → v2 merge engine
# patches v1 memo with onboarding data, produces v2 memo + changelog

import copy
from pathlib import Path
from pipe.utils import get_lgr, utc_now, write_json, get_acct_dir, read_json

lgr = get_lgr("patch")


# ── field differ ──────────────────────────────────────────
def _diff(v1_val, v2_val, field: str) -> dict | None:
    """
    compares v1 vs v2 value for a field
    returns change entry or None if no change
    """
    # normalize empties
    empty = (None, [], {}, "")

    v1_empty = v1_val in empty or v1_val == {}
    v2_empty = v2_val in empty or v2_val == {}

    if v2_empty:
        # v2 didn't provide this field — keep v1
        return None

    if v1_empty and not v2_empty:
        return {
            "field"  : field,
            "action" : "filled",
            "v1"     : v1_val,
            "v2"     : v2_val
        }

    if v1_val != v2_val:
        return {
            "field"  : field,
            "action" : "updated",
            "v1"     : v1_val,
            "v2"     : v2_val
        }

    return None  # unchanged


# ── deep patch ────────────────────────────────────────────
def _deep_patch(v1: dict, v2: dict, parent: str = "") -> tuple[dict, list]:
    """
    recursively patches v1 with v2 values
    returns (patched_dict, changes_list)
    only overwrites if v2 has a real value
    """
    patched = copy.deepcopy(v1)
    changes = []

    for key, v2_val in v2.items():
        full_key = f"{parent}.{key}" if parent else key
        v1_val   = v1.get(key)

        if isinstance(v2_val, dict) and isinstance(v1_val, dict):
            # recurse into nested objects
            sub_patched, sub_changes = _deep_patch(v1_val, v2_val, full_key)
            patched[key] = sub_patched
            changes.extend(sub_changes)
        else:
            chg = _diff(v1_val, v2_val, full_key)
            if chg:
                patched[key] = v2_val
                changes.append(chg)

    return patched, changes


# ── skip fields during patch ──────────────────────────────
# these are controlled by pipeline — never overwritten by v2 data
SKIP_FIELDS = {"acct_id", "memo_ver", "created_at"}


# ── main patch fn ─────────────────────────────────────────
def run_patch(acct_id: str, v2_memo_raw: dict) -> tuple[dict, dict]:
    """
    loads v1 memo, patches with v2 extraction result
    produces v2 memo + changelog

    args:
        acct_id     → account to patch
        v2_memo_raw → raw memo dict from run_extract() on onboard call

    returns:
        (v2_memo, changelog)
        saves both to out/accounts/<acct_id>/v2/
    """
    lgr.info(f"patching v1 → v2 | acct_id: {acct_id}")

    # ── load v1 memo
    v1_path = get_acct_dir(acct_id, "v1") / "memo.json"
    if not v1_path.exists():
        raise FileNotFoundError(
            f"v1 memo not found for {acct_id} — run demo pipeline first"
        )

    v1_memo = read_json(v1_path)
    lgr.info(f"v1 memo loaded → {v1_path}")

    # ── strip skip fields from v2 before patching
    v2_clean = {
        k: v for k, v in v2_memo_raw.items()
        if k not in SKIP_FIELDS
    }

    # ── patch
    patched, changes = _deep_patch(v1_memo, v2_clean)

    # ── force v2 metadata
    patched["acct_id"]   = acct_id
    patched["memo_ver"]  = "v2_onboard"
    patched["updated_at"] = utc_now()

    # ── build changelog
    changelog = {
        "acct_id"    : acct_id,
        "patch_at"   : utc_now(),
        "v1_memo"    : str(v1_path),
        "total_changes": len(changes),
        "changes"    : changes,
        "open_qs_remaining": patched.get("open_qs", [])
    }

    lgr.info(f"patch complete | changes: {len(changes)}")
    for c in changes:
        lgr.info(f"  [{c['action']}] {c['field']}")

    # ── save v2 memo + changelog
    v2_dir = get_acct_dir(acct_id, "v2")
    write_json(patched,   v2_dir / "memo.json")
    write_json(changelog, v2_dir.parent / "changelog.json")

    lgr.info(f"v2 memo saved    → {v2_dir / 'memo.json'}")
    lgr.info(f"changelog saved  → {v2_dir.parent / 'changelog.json'}")

    return patched, changelog