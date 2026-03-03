# tests/test_ingest.py
# tests ingestion layer — file detection, id generation, text loading

import sys
sys.path.insert(0, ".")

from pipe.utils  import detect_src_type, gen_acct_id, utc_now
from pathlib     import Path

print("── test_ingest ──")

# test 1: audio detection
for ext in [".mp3", ".wav", ".m4a", ".flac"]:
    fake = Path(f"fake_file{ext}")
    assert detect_src_type(fake) == "audio", f"failed for {ext}"
print("audio extensions detected")

# test 2: transcript detection
for ext in [".txt", ".json"]:
    fake = Path(f"fake_file{ext}")
    assert detect_src_type(fake) == "transcript", f"failed for {ext}"
print("transcript extensions detected")

# test 3: unknown extension raises
try:
    detect_src_type(Path("fake.xyz"))
    assert False, "should have raised"
except ValueError:
    pass
print("unknown extension raises ValueError")

# test 4: acct_id format
for _ in range(5):
    aid = gen_acct_id()
    assert aid.startswith("ACCT-"),       f"wrong prefix: {aid}"
    assert len(aid) == 13,                f"wrong length: {aid}"
    assert aid[5:].isalnum(),             f"not alphanumeric: {aid}"
    assert aid[5:] == aid[5:].upper(),    f"not uppercase: {aid}"
print("acct_id format correct")

# test 5: utc_now returns iso string
ts = utc_now()
assert "T"  in ts, "not ISO format"
assert "+"  in ts or "Z" in ts, "no timezone info"
print("utc_now returns ISO timestamp")

print("\nall ingest tests passed")