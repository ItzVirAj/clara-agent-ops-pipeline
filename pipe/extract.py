# pipe/extract.py

import os
import json
import re

from google import genai
from pipe.utils import (
    get_lgr, utc_now, write_json, get_acct_dir
)

lgr = get_lgr("extract")


# ── gemini client setup ───────────────────────────────────
def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set in cfg/.env")
    return genai.Client(api_key=api_key)


# ── extraction prompt builder ─────────────────────────────
def _build_ext_prompt(raw_txt: str, acct_id: str, memo_ver: str) -> str:
    """
    builds the extraction prompt sent to gemini
    strict instructions to prevent hallucination
    """
    return f"""
You are a data extraction assistant for Clara Answers, an AI voice agent platform for service trade businesses.

Your job is to extract structured information from a call transcript and return it as a single valid JSON object.

STRICT RULES:
1. Only extract information explicitly stated in the transcript
2. If a field is not mentioned or unclear, set it to null
3. Never guess, infer, or invent any detail
4. timezone must be IANA format ex America/Chicago, America/New_York, America/Denver, America/Los_Angeles
5. biz_hrs open/close must be HH:MM 24hr format ex 08:00 not 8am
6. For open_qs list every piece of information that is missing but needed to configure the voice agent
7. Return ONLY the JSON object — no explanation, no markdown, no code blocks

TRANSCRIPT:
{raw_txt}

Extract into this exact JSON structure:
{{
  "acct_id": "{acct_id}",
  "co_name": null,
  "co_phone": null,
  "co_addr": null,
  "timezone": null,
  "biz_hrs": {{
    "mon": {{"open": null, "close": null, "active": null}},
    "tue": {{"open": null, "close": null, "active": null}},
    "wed": {{"open": null, "close": null, "active": null}},
    "thu": {{"open": null, "close": null, "active": null}},
    "fri": {{"open": null, "close": null, "active": null}},
    "sat": {{"open": null, "close": null, "active": null}},
    "sun": {{"open": null, "close": null, "active": null}}
  }},
  "svcs": [],
  "emrg_triggers": [],
  "emrg_routing": {{
    "primary_name": null,
    "primary_ph": null,
    "secondary_name": null,
    "secondary_ph": null,
    "order": null
  }},
  "non_emrg_routing": {{
    "type": null,
    "contact_name": null,
    "contact_ph": null,
    "notes": null
  }},
  "xfer_rules": {{
    "timeout_sec": null,
    "retry_count": null,
    "fail_msg": null
  }},
  "integrations": [],
  "aft_hrs_flow": null,
  "biz_hrs_flow": null,
  "open_qs": [],
  "notes": null,
  "memo_ver": "{memo_ver}",
  "created_at": "{utc_now()}",
  "updated_at": null
}}

Fill in every field you can find evidence for in the transcript.
Leave null for anything not mentioned.
For open_qs add a clear question for every field that is null and would be required to configure the agent.
""".strip()


# ── json cleaner ──────────────────────────────────────────
def _clean_json_resp(raw_resp: str) -> str:
    """
    gemini sometimes wraps response in markdown code blocks
    strips them out to get raw json string
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_resp.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return cleaned.strip()


# ── main extract fn ───────────────────────────────────────
def run_extract(ing_result: dict) -> dict:
    """
    main extraction entry point

    args:
        ing_result → output dict from run_ingest()

    returns:
        memo dict matching account_schema.json structure
        also saves memo.json to account versioned dir
    """
    acct_id   = ing_result["acct_id"]
    raw_txt   = ing_result["raw_txt"]
    call_type = ing_result["call_type"]
    memo_ver  = "v1_demo" if call_type == "demo" else "v2_onboard"

    lgr.info(f"starting extraction | acct_id: {acct_id} | memo_ver: {memo_ver}")

    # ── build prompt
    prompt = _build_ext_prompt(raw_txt, acct_id, memo_ver)
    lgr.debug(f"prompt built — {len(prompt)} chars")

    # ── call gemini
    lgr.info("calling gemini 2.5 flash for extraction...")
    try:
        client   = _get_gemini_client()
        response = client.models.generate_content(
            model    = "gemini-2.5-flash",
            contents = prompt
        )
        raw_resp = response.text
        lgr.debug(f"raw gemini response length: {len(raw_resp)} chars")
    except Exception as e:
        lgr.error(f"gemini call failed: {e}")
        raise

    # ── clean and parse response
    try:
        cleaned = _clean_json_resp(raw_resp)
        memo    = json.loads(cleaned)
        lgr.info("gemini response parsed successfully")
    except json.JSONDecodeError as e:
        lgr.error(f"json parse failed — raw response:\n{raw_resp}")
        raise ValueError(f"gemini returned invalid json: {e}")

    # ── force correct acct_id and memo_ver (never trust llm for these)
    memo["acct_id"]  = acct_id
    memo["memo_ver"] = memo_ver

    # ── log extraction summary
    filled    = [k for k, v in memo.items() if v not in (None, [], {})]
    null_flds = [k for k, v in memo.items() if v in (None, [], {})]
    open_qs   = memo.get("open_qs", [])

    lgr.info(f"fields filled: {len(filled)} | null fields: {len(null_flds)} | open_qs: {len(open_qs)}")

    if open_qs:
        lgr.info("open questions flagged:")
        for q in open_qs:
            lgr.info(f"  ↳ {q}")

    # ── save memo.json
    ver      = "v1" if call_type == "demo" else "v2"
    acct_dir = get_acct_dir(acct_id, ver)
    out_path = acct_dir / "memo.json"
    write_json(memo, out_path)
    lgr.info(f"memo saved → {out_path}")

    return memo