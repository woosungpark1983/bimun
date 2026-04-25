"""
비문 신청서 시스템 (Flask)
- PC 상담/작업용 2페이지 구조
- 저장 데이터 중심
- 저장 파일: saved_data/*.json, saved_data/_index.json
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "saved_data")
os.makedirs(SAVE_DIR, exist_ok=True)
INDEX_FILE = os.path.join(SAVE_DIR, "_index.json")

CATALOG = {
    "매장묘": ["단장", "쌍분"],
    "단납/평장1기": ["기본"],
    "쌍납/평장부부A": ["기본"],
    "송수재": ["개인", "부부"],
    "부부A": ["기본"],
    "납골정": ["기본"],
    "평장부부B": ["기본", "1번", "2번", "3번", "4번"],
    "평장1기P": ["기본"],
    "4기": ["A", "B", "C", "P", "R"],
    "평장부부P": ["기본"],
    "평장4기": ["기본"],
    "평장4기P": ["기본"],
    "8기": ["기본"],
    "다기형": ["12A", "20기", "30기"],
    "12기B": ["기본"],
    "24기": ["기본"],
}

PRICE_GROUPS = {
    "A": {"big_korean": 8000, "big_chinese": 12000, "small_korean": 4000, "small_chinese": 6000, "stone_photo_price": 120000},
    "B": {"big_korean": 10000, "big_chinese": 15000, "small_korean": 5000, "small_chinese": 7500, "stone_photo_price": 120000},
    "C": {"big_korean": 16000, "big_chinese": 24000, "small_korean": 8000, "small_chinese": 12000, "stone_photo_price": 120000},
}

STONE_PHOTO_CATEGORIES = ["단납/평장1기", "송수재", "평장부부B", "평장부부P", "평장4기"]
STAFF_LIST = ["", "이성규", "이재민", "진승현", "우승협", "윤은영", "김애진", "김경란", "김민재", "김현"]
STATUS_LIST = ["접수됨", "시안문자발송", "고객확인완료", "완료"]

# 기존 가격군 기준 유지용 간단 룰
RULES = {}
for c, subs in CATALOG.items():
    for s in subs:
        group = "A"
        if c in ["매장묘", "단납/평장1기", "쌍납/평장부부A"]:
            group = "B"
        if c in ["평장1기P", "평장부부P", "평장4기P", "8기", "다기형", "12기B", "24기"] or (c == "4기" and s == "P"):
            group = "C"
        slots = 1
        if c in ["쌍납/평장부부A", "송수재", "부부A", "납골정", "평장부부B", "평장부부P"] or (c == "매장묘" and s == "쌍분"):
            slots = 2
        if c in ["4기", "평장4기", "평장4기P"]:
            slots = 4
        if c in ["8기", "다기형", "12기B", "24기"]:
            slots = 5
        RULES[f"{c}||{s}"] = {
            "price_group": group,
            "slots": slots,
            "has_side": (c == "매장묘") or (c == "평장부부B" and s == "2번"),
            "stone_photo": c in STONE_PHOTO_CATEGORIES,
        }


def _read_index():
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_index(items):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def count_chars(text):
    return len(str(text or "").replace(" ", "").replace("\n", "").replace("\r", ""))


def get_rule(category, subcategory):
    return RULES.get(f"{category}||{subcategory}") or RULES["매장묘||단장"]


def calc_summary(form):
    category = form.get("category", "매장묘")
    subcategory = form.get("subcategory", "단장")
    rule = get_rule(category, subcategory)
    pg = PRICE_GROUPS[rule["price_group"]]

    front_type = form.get("front_type", "korean")
    side_type = form.get("side_type", "korean")
    back_type = form.get("back_type", "korean")

    big_unit = pg["big_korean"] if front_type == "korean" else pg["big_chinese"]
    small_unit = pg["small_korean"] if front_type == "korean" else pg["small_chinese"]
    side_unit = pg["small_korean"] if side_type == "korean" else pg["small_chinese"]
    back_unit = pg["small_korean"] if back_type == "korean" else pg["small_chinese"]

    big_cnt = 0
    small_cnt = 0
    side_cnt = 0
    back_cnt = 0

    if form.get("religion_mark"):
        big_cnt += 1
    big_cnt += count_chars(form.get("front_extra"))

    try:
        slot_count = int(form.get("slot_count") or rule.get("slots") or 1)
    except Exception:
        slot_count = rule.get("slots", 1)
    slot_count = max(1, min(slot_count, 10))

    for i in range(1, slot_count + 1):
        big_cnt += count_chars(form.get(f"f{i}_name"))
        big_cnt += count_chars(form.get(f"f{i}_baptism"))
        birth = form.get(f"f{i}_birth")
        death = form.get(f"f{i}_death")
        btype = form.get(f"f{i}_birth_type", "생")
        dtype = form.get(f"f{i}_death_type", "졸")
        if birth:
            small_cnt += count_chars(birth) + (0 if btype == "없음" else count_chars(btype))
        if death:
            small_cnt += count_chars(death) + (0 if dtype == "없음" else count_chars(dtype or "졸"))

    if rule.get("has_side"):
        for prefix in ["s1", "s2"]:
            birth = form.get(f"{prefix}_birth")
            death = form.get(f"{prefix}_death")
            btype = form.get(f"{prefix}_birth_type", "생")
            dtype = form.get(f"{prefix}_death_type", "졸")
            if birth:
                side_cnt += count_chars(birth) + (0 if btype == "없음" else count_chars(btype))
            if death:
                side_cnt += count_chars(death) + (0 if dtype == "없음" else count_chars(dtype or "졸"))

    for key, prefix_len in [
        ("son_text", 1), ("daughter_in_law_text", 2), ("grandson_text", 1),
        ("daughter_text", 1), ("son_in_law_text", 2), ("maternal_grandchild_text", 2),
    ]:
        if form.get(key):
            back_cnt += prefix_len + count_chars(form.get(key))
    back_cnt += count_chars(form.get("etc_text"))

    stone_enabled = category in STONE_PHOTO_CATEGORIES
    stone_added = stone_enabled and form.get("stone_photo") in ["yes", "추가", "있음"]

    big_amt = big_cnt * big_unit
    small_amt = small_cnt * small_unit
    side_amt = side_cnt * side_unit
    back_amt = back_cnt * back_unit
    stone_amt = pg["stone_photo_price"] if stone_added else 0
    total = big_amt + small_amt + side_amt + back_amt + stone_amt

    return {
        "big_cnt": big_cnt, "big_unit": big_unit, "big_amt": big_amt,
        "small_cnt": small_cnt, "small_unit": small_unit, "small_amt": small_amt,
        "side_cnt": side_cnt, "side_unit": side_unit, "side_amt": side_amt,
        "back_cnt": back_cnt, "back_unit": back_unit, "back_amt": back_amt,
        "stone_enabled": stone_enabled,
        "stone_added": stone_added,
        "stone_amt": stone_amt,
        "total": total,
        "price_group": rule["price_group"],
        "has_side": rule["has_side"],
    }


def make_summary_item(data, item_id=None, created_at=None):
    summary = calc_summary(data)
    category = data.get("category", "")
    subcategory = data.get("subcategory", "")
    now = created_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "id": item_id or str(uuid.uuid4()),
        "created_at": now,
        "contract_no": data.get("contract_no", ""),
        "contractor": data.get("contractor", ""),
        "phone": data.get("phone", ""),
        "type_label": f"{category} / {subcategory}" if subcategory else category,
        "category": category,
        "subcategory": subcategory,
        "status": data.get("status", "접수됨"),
        "writer": data.get("writer", ""),
        "designer": data.get("designer", ""),
        "checker": data.get("checker", ""),
        "big_amt": summary["big_amt"],
        "small_amt": summary["small_amt"] + summary["side_amt"] + summary["back_amt"],
        "stone_photo": "추가" if summary["stone_added"] else "없음",
        "total": summary["total"],
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        catalog=CATALOG,
        rules=RULES,
        staff_list=STAFF_LIST,
        status_list=STATUS_LIST,
        stone_categories=STONE_PHOTO_CATEGORIES,
        saved_list=_read_index(),
    )


@app.route("/api/calc", methods=["POST"])
def api_calc():
    data = request.get_json(force=True) or {}
    return jsonify(calc_summary(data))


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.get_json(force=True) or {}
    item_id = data.get("id") or str(uuid.uuid4())
    created_at = data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M")
    data["id"] = item_id
    data["created_at"] = created_at
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(os.path.join(SAVE_DIR, f"{item_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    items = _read_index()
    summary_item = make_summary_item(data, item_id=item_id, created_at=created_at)
    items = [x for x in items if x.get("id") != item_id]
    items.insert(0, summary_item)
    _write_index(items)
    return jsonify({"ok": True, "id": item_id, "item": summary_item})


@app.route("/api/list")
def api_list():
    return jsonify(_read_index())


@app.route("/api/load/<item_id>")
def api_load(item_id):
    path = os.path.join(SAVE_DIR, f"{item_id}.json")
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "not found"}), 404
    with open(path, "r", encoding="utf-8") as f:
        return jsonify({"ok": True, "data": json.load(f)})


@app.route("/api/delete/<item_id>", methods=["POST"])
def api_delete(item_id):
    path = os.path.join(SAVE_DIR, f"{item_id}.json")
    if os.path.exists(path):
        os.remove(path)
    items = [x for x in _read_index() if x.get("id") != item_id]
    _write_index(items)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
