"""P2 smoke test - upload flow end-to-end."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import base64
import uuid
import urllib.request
from dotenv import load_dotenv
load_dotenv()

import storage

# Minimal valid 1x1 JPEG (~125 bytes)
jpg_b64 = (
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
    "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB/8AAEQgAAQABAwERAAIRAQMRAf/EABQAAQAA"
    "AAAAAAAAAAAAAAAAAAr/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AKpgB//Z"
)
jpg = base64.b64decode(jpg_b64)
print(f"Test JPEG: {len(jpg)} bytes")

test_id = str(uuid.uuid4())
summary = {
    "contract_no": "P2-TEST", "contractor": "P2", "phone": "010",
    "type_label": "평장부부B / 기본", "category": "평장부부B", "subcategory": "기본",
    "status": "접수됨", "writer": "", "designer": "", "checker": "",
    "big_amt": 0, "small_amt": 0, "stone_photo": "없음", "total": 0,
    "jigu": "", "yeol": "", "ho": "",
}
storage.save_record(test_id, summary, {"hello": "world"})
print(f"Created record {test_id}")

url = storage.upload_draft(test_id, jpg, "image/jpeg")
print(f"Uploaded draft URL: {url}")

items = storage.list_records()
mine = [r for r in items if r["id"] == test_id][0]
print(f"List has draft_url: {mine['draft_url']}")

with urllib.request.urlopen(url, timeout=10) as r:
    body = r.read()
    print(f"Public URL fetched: HTTP {r.status}, {len(body)} bytes")

storage.delete_record(test_id)
print("Cleaned up (record + draft).")
print("\nALL CHECKS PASSED")
