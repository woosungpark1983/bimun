"""Smoke test - verifies Supabase storage adapter end-to-end.
Run once to confirm SUPABASE_URL/KEY work and the schema is applied.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import uuid
from dotenv import load_dotenv
load_dotenv()

import storage

print("[1/5] connect…")
client = storage._get_client()
print("    ok")

print("[2/5] insert test record…")
test_id = str(uuid.uuid4())
summary = {
    "contract_no": "SMOKE-TEST",
    "contractor": "테스트",
    "phone": "010-0000-0000",
    "type_label": "매장묘 / 단장",
    "category": "매장묘",
    "subcategory": "단장",
    "status": "접수됨",
    "writer": "", "designer": "", "checker": "",
    "big_amt": 0, "small_amt": 0, "stone_photo": "없음", "total": 0,
}
saved = storage.save_record(test_id, summary, {"hello": "world"})
assert saved["id"] == test_id, f"expected {test_id}, got {saved['id']}"
print(f"    ok - id={saved['id']}, created_at={saved['created_at']}")

print("[3/5] list records…")
items = storage.list_records()
assert any(r["id"] == test_id for r in items), "inserted record not in list"
print(f"    ok - {len(items)} record(s)")

print("[4/5] load by id…")
loaded = storage.load_record(test_id)
assert loaded == {"id": test_id, "hello": "world"}, f"unexpected payload: {loaded}"
print("    ok")

print("[5/5] delete…")
storage.delete_record(test_id)
loaded = storage.load_record(test_id)
assert loaded is None, "record should be deleted"
print("    ok")

print("\nALL CHECKS PASSED - Supabase storage works end-to-end.")
