# pipe/prmpt_gen.py
# builds agent_spec.json + agent_prompt.txt from memo

import os
from google import genai
from pipe.utils import get_lgr, utc_now, write_json, get_acct_dir

lgr = get_lgr("prmpt_gen")


# ── helpers ───────────────────────────────────────────────

def _gmni():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError("GEMINI_API_KEY missing")
    return genai.Client(api_key=key)


def _biz_hrs_str(b):
    if not b:
        return "Not specified"

    day_map = {"mon":"Mon","tue":"Tue","wed":"Wed",
               "thu":"Thu","fri":"Fri","sat":"Sat","sun":"Sun"}

    active = {d:f"{v['open']}-{v['close']}"
              for d,v in b.items()
              if v.get("active") and v.get("open")}

    if not active:
        return "Not specified"

    grp = {}
    for d,h in active.items():
        grp.setdefault(h, []).append(day_map[d])

    return ", ".join(f"{'/'.join(days)} {hrs}" for hrs,days in grp.items())


# ── build gemini prompt ───────────────────────────────────

def _build_prompt(m):
    co   = m.get("co_name","the company")
    tz   = m.get("timezone","local time")
    hrs  = _biz_hrs_str(m.get("biz_hrs",{}))
    svcs = ", ".join(m.get("svcs",[])) or "service trade"
    trg  = ", ".join(m.get("emrg_triggers",[])) or "not specified"

    e    = m.get("emrg_routing",{})
    x    = m.get("xfer_rules",{})

    pri_n = e.get("primary_name","on-call tech")
    pri_p = e.get("primary_ph","PRIMARY_PHONE")
    sec_n = e.get("secondary_name")
    sec_p = e.get("secondary_ph")

    t_out = x.get("timeout_sec",30)
    retry = x.get("retry_count",1)
    fail  = x.get("fail_msg",
        f"I'm sorry, I couldn't reach our team. "
        f"Someone from {co} will follow up soon.")

    sec_line = (
        f"- If {pri_n} doesn't answer in {t_out}s, transfer to {sec_n} at {sec_p}"
        if sec_n and sec_p else ""
    )

    return f"""
You are Clara, an AI phone agent for {co}.

CONTEXT
Company: {co}
Services: {svcs}
Business hours: {hrs} ({tz})
Emergency triggers: {trg}
Primary contact: {pri_n} at {pri_p}
{sec_line}
Timeout: {t_out}s | Retries: {retry}
Fail message: "{fail}"

INSTRUCTIONS
- Greet → ask purpose → collect name + callback
- Detect emergency vs non-emergency

BUSINESS HOURS
Emergency → transfer primary → secondary → fail message if needed
Non-emergency → collect details → confirm follow-up

AFTER HOURS
Emergency → collect name + number + address → transfer → fail if needed
Non-emergency → collect details → confirm next business day follow-up

RULES
- Never mention technical terms
- Always repeat callback number
- Stay calm and professional
- Never invent company info
""".strip()


# ── build agent spec ──────────────────────────────────────

def _build_spec(m, sys_prompt, ver):
    co = m.get("co_name","the company")
    hrs_str = _biz_hrs_str(m.get("biz_hrs",{}))
    e = m.get("emrg_routing",{})
    ne = m.get("non_emrg_routing",{})
    x = m.get("xfer_rules",{})

    return {
        "acct_id": m["acct_id"],
        "agent_name": f"Clara — {co}",
        "voice_style": "professional, warm, concise",
        "lang": "en-US",
        "sys_prompt": sys_prompt,
        "key_vars": {
            "co_name": co,
            "biz_hrs_str": hrs_str,
            "emrg_list_str": ", ".join(m.get("emrg_triggers",[])),
            "after_hrs_msg": f"Our hours are {hrs_str}. We will follow up next business day."
        },
        "xfer_protocol": {
            "emrg": {"ph": e.get("primary_ph","")},
            "non_emrg": {"ph": ne.get("contact_ph","")},
            "timeout_sec": x.get("timeout_sec",30),
            "retry_count": x.get("retry_count",1)
        },
        "fallbk": {
            "fail_msg": x.get("fail_msg","Transfer failed. We will follow up."),
            "collect_cb": True,
            "assure_followup": True
        },
        "spec_ver": ver,
        "created_at": utc_now(),
        "updated_at": None
    }


# ── main entry ────────────────────────────────────────────

def run_prmpt_gen(memo: dict) -> dict:
    acct_id = memo["acct_id"]
    memo_ver = memo.get("memo_ver","v1_demo")
    spec_ver = "v1_demo" if "v1" in memo_ver else "v2_onboard"
    out_ver  = "v1" if "v1" in memo_ver else "v2"

    lgr.info(f"gen agent spec | {acct_id} | {spec_ver}")

    client = _gmni()
    sys_prompt = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=_build_prompt(memo)
    ).text.strip()

    spec = _build_spec(memo, sys_prompt, spec_ver)

    acct_dir = get_acct_dir(acct_id, out_ver)
    write_json(spec, acct_dir / "agent_spec.json")
    (acct_dir / "agent_prompt.txt").write_text(sys_prompt, encoding="utf-8")

    return spec