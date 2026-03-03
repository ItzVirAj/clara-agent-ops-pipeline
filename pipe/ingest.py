# pipe/ingest.py
# ingestion layer - normalizes any input (audio or transcript) to plain text
# returns structured ingest result dict ready for extraction

import json
from pathlib import Path
from pipe.utils import (
    get_lgr, gen_acct_id, utc_now,
    detect_src_type, read_txt, get_acct_dir, write_json
)

lgr = get_lgr("ingest")


# ── audio → text ──────────────────────────────────────────
def _transcribe(fpath: Path) -> str:
    """
    runs faster-whisper on audio file
    returns raw transcript string
    model size: base — good balance of speed vs accuracy for this use case
    """
    lgr.info(f"transcribing audio: {fpath.name}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("faster-whisper not installed — run: pip install faster-whisper")

    # base model — no gpu needed, cpu is fine for 5 files
    mdl = WhisperModel("base", device="cpu", compute_type="int8")
    segs, info = mdl.transcribe(str(fpath), beam_size=5)

    lgr.info(f"detected language: {info.language} | duration: {info.duration:.1f}s")

    # join all segments into one clean string
    full_txt = " ".join(seg.text.strip() for seg in segs)
    lgr.debug(f"transcript length: {len(full_txt)} chars")

    return full_txt.strip()


# ── transcript → text ─────────────────────────────────────
def _load_transcript(fpath: Path) -> str:
    """
    loads transcript from .txt or .json file
    .txt  → returned as-is
    .json → checks for common transcript keys, falls back to full dump
    """
    lgr.info(f"loading transcript: {fpath.name}")

    ext = fpath.suffix.lower()

    if ext == ".txt":
        return read_txt(fpath)

    if ext == ".json":
        raw = read_txt(fpath)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            lgr.warning("json parse failed — treating as plain text")
            return raw

        # check common transcript keys people use
        for key in ["transcript", "text", "content", "body"]:
            if key in data and isinstance(data[key], str):
                lgr.debug(f"found transcript under key: '{key}'")
                return data[key].strip()

        # if no known key — dump full json as text for llm to handle
        lgr.warning("no known transcript key found in json — using full dump")
        return raw

    raise ValueError(f"unsupported transcript extension: {ext}")


# ── main ingest fn ────────────────────────────────────────
def run_ingest(
    fpath: str,
    acct_id: str | None = None,
    call_type: str = "demo"        # "demo" | "onboard"
) -> dict:
    """
    main ingestion entry point

    args:
        fpath     → path to input file (audio or transcript)
        acct_id   → pass existing id for onboard calls, None for new demo
        call_type → 'demo' (pipeline A) or 'onboard' (pipeline B)

    returns:
        ing_result dict with keys:
            acct_id, src_type, raw_txt, src_file, call_type, ing_at
    """
    fp = Path(fpath)

    # ── validate file exists
    if not fp.exists():
        raise FileNotFoundError(f"input file not found: {fpath}")

    lgr.info(f"ingesting | file: {fp.name} | call_type: {call_type}")

    # ── detect type
    src_type = detect_src_type(fp)
    lgr.info(f"src_type detected: {src_type}")

    # ── get or assign acct_id
    if acct_id:
        lgr.info(f"using existing acct_id: {acct_id}")
        _acct_id = acct_id
    else:
        _acct_id = gen_acct_id()
        lgr.info(f"new acct_id assigned: {_acct_id}")

    # ── extract raw text
    if src_type == "audio":
        raw_txt = _transcribe(fp)
    else:
        raw_txt = _load_transcript(fp)

    if not raw_txt:
        raise ValueError(f"empty content after ingestion: {fp.name}")

    # ── build result
    ing_result = {
        "acct_id"   : _acct_id,
        "src_type"  : src_type,
        "call_type" : call_type,
        "src_file"  : str(fp.resolve()),
        "raw_txt"   : raw_txt,
        "ing_at"    : utc_now()
    }

    # ── save raw transcript to account dir for reference
    ver = "v1" if call_type == "demo" else "v2"
    acct_dir = get_acct_dir(_acct_id, ver)
    raw_out  = acct_dir / "raw_transcript.txt"

    raw_out.write_text(raw_txt, encoding="utf-8")
    lgr.info(f"raw transcript saved → {raw_out}")

    lgr.info(f"ingest complete | acct_id: {_acct_id}")
    return ing_result