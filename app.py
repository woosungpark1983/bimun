"""
비문 신청서 시스템 (Flask)
- PC 상담/작업용 2페이지 구조
- 저장소: Supabase (storage.py 어댑터 경유)
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify

# Vercel runs in UTC; force timestamps to KST so the saved-list display matches what staff expect.
_KST = timezone(timedelta(hours=9))


def _now_kst() -> str:
    return datetime.now(_KST).strftime("%Y-%m-%d %H:%M")

# Local .env support — silent no-op if python-dotenv isn't installed (e.g. on Vercel where env vars come from the dashboard).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import storage

app = Flask(__name__)

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
STONE_PHOTO_COMBOS = {
    ("단납/평장1기", "기본"), ("송수재", "개인"), ("송수재", "부부"),
    ("평장부부B", "기본"), ("평장부부P", "기본"), ("평장4기", "기본"),
}
STAFF_LIST = ["", "이성규", "이재민", "진승현", "우승협", "윤은영", "김애진", "김경란", "김민재", "김현", "임병현", "김동현", "박동석", "강세범", "배건호"]
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
        front_only_hanja = c in ["단납/평장1기", "쌍납/평장부부A", "송수재", "평장1기P"]
        RULES[f"{c}||{s}"] = {
            "price_group": group,
            "slots": slots,
            "has_side": (c == "매장묘") or (c == "평장부부B" and s == "2번"),
            "stone_photo": c in STONE_PHOTO_CATEGORIES,
            "front_style": "maejang" if (c == "매장묘" or (c == "평장부부B" and s == "2번")) else "standard",
            # 한자 표현 가능 범위: 계산용이 아니라 시안 표현 방식 제어용
            "front_hanja": True,
            "side_hanja": (not front_only_hanja) and ((c == "매장묘") or (c == "평장부부B" and s == "2번")),
            "back_hanja": not front_only_hanja,
            "needs_orientation": (c == "4기" and s == "B"),
            "family_phrase": c in ["8기", "12기B", "24기", "다기형"],
        }


def _read_index():
    """List view — delegates to Supabase. Errors return [] so the page still renders."""
    try:
        return storage.list_records()
    except Exception as e:
        app.logger.warning("storage.list_records failed: %s", e)
        return []


def count_chars(text):
    return len(str(text or "").replace(" ", "").replace("\n", "").replace("\r", ""))


def _is_hanja(ch):
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF) or (0xF900 <= cp <= 0xFAFF)


def count_chars_split(text):
    """Returns (hanja_count, other_count) for non-whitespace chars."""
    t = str(text or "").replace(" ", "").replace("\n", "").replace("\r", "")
    hanja = sum(1 for c in t if _is_hanja(c))
    return hanja, len(t) - hanja


def _bongwan_suffix(bongwan, hanja_suf, kor_suf):
    """Returns suffix count (0 if already appended)."""
    t = str(bongwan or "").strip()
    if not t:
        return 0
    if t.endswith(hanja_suf) or t.endswith(kor_suf):
        return 0
    return 1  # always 1 char suffix


def get_rule(category, subcategory):
    return RULES.get(f"{category}||{subcategory}") or RULES["매장묘||단장"]


def calc_summary(form):
    category = form.get("category", "매장묘")
    subcategory = form.get("subcategory", "단장")
    rule = get_rule(category, subcategory)
    pg = PRICE_GROUPS[rule["price_group"]]

    bk_u = pg["big_korean"]
    bh_u = pg["big_chinese"]
    sk_u = pg["small_korean"]
    sh_u = pg["small_chinese"]

    # Separate hanja vs other (Korean/numbers) counts
    big_h, big_o = 0, 0
    small_h, small_o = 0, 0
    side_h, side_o = 0, 0
    back_h, back_o = 0, 0

    def _add_big(text, extra_other=0):
        nonlocal big_h, big_o
        h, o = count_chars_split(text)
        big_h += h; big_o += o + extra_other

    def _add_small(text, extra_other=0):
        nonlocal small_h, small_o
        h, o = count_chars_split(text)
        small_h += h; small_o += o + extra_other

    def _add_side(text, extra_other=0):
        nonlocal side_h, side_o
        h, o = count_chars_split(text)
        side_h += h; side_o += o + extra_other

    def _add_back(text, extra_other=0):
        nonlocal back_h, back_o
        h, o = count_chars_split(text)
        back_h += h; back_o += o + extra_other

    try:
        slot_count = int(form.get("slot_count") or 1)
    except Exception:
        slot_count = 1
    slot_count = max(1, min(slot_count, 10))

    if rule.get("front_style") == "maejang":
        # 문자별 자동감지 (탭 기준 강제 없음)
        if form.get("religion_mark"):
            big_o += 1

        jidmyo_val = str(form.get("jidmyo", "") or "")
        if jidmyo_val == "있음":        # 구형 데이터 호환
            big_o += 2
        elif jidmyo_val not in ("없음", ""):
            _add_big(jidmyo_val)

        male_title = str(form.get("male_title", "") or "")
        female_title = str(form.get("female_title", "") or "")
        m_bon = str(form.get("male_bongwan") or "")
        f_bon = str(form.get("female_bongwan") or "")

        if male_title and male_title != "없음":
            _add_big(male_title)
            _add_big(m_bon)
            ms = m_bon.strip()
            if ms and not ms.endswith("公") and not ms.endswith("공"):
                if _is_hanja(ms[-1]): big_h += 1
                else: big_o += 1
            _add_big(form.get("male_name"))
        if female_title and female_title != "없음":
            _add_big(female_title)
            _add_big(f_bon)
            fs = f_bon.strip()
            if fs and not fs.endswith("氏") and not fs.endswith("씨"):
                if _is_hanja(fs[-1]): big_h += 1
                else: big_o += 1
            _add_big(form.get("female_name"))
    else:
        if form.get("religion_mark"):
            big_o += 1
        _add_big(form.get("front_extra"))
        if rule.get("family_phrase") and form.get("family_bongwan"):
            h, o = count_chars_split(form.get("family_bongwan"))
            big_h += h; big_o += o + 5  # 고정 5자

        for i in range(1, slot_count + 1):
            _add_big(form.get(f"f{i}_name"))
            _add_big(form.get(f"f{i}_baptism"))
            birth = form.get(f"f{i}_birth")
            death = form.get(f"f{i}_death")
            btype = form.get(f"f{i}_birth_type", "생")
            dtype = form.get(f"f{i}_death_type", "졸")
            if birth:
                _add_small(birth)
                if btype != "없음":
                    _add_small(btype)
            if death:
                _add_small(death)
                if (dtype or "졸") != "없음":
                    _add_small(dtype or "졸")

    if rule.get("has_side"):
        for prefix in ["s1", "s2"]:
            birth = form.get(f"{prefix}_birth")
            death = form.get(f"{prefix}_death")
            btype = form.get(f"{prefix}_birth_type", "생")
            dtype = form.get(f"{prefix}_death_type", "졸")
            if birth:
                _add_side(birth)
                if btype != "없음":
                    _add_side(btype)
            if death:
                _add_side(death)
                if (dtype or "졸") != "없음":
                    _add_side(dtype or "졸")

    for key, prefix_len in [
        ("son_text", 1), ("daughter_in_law_text", 2), ("grandson_text", 1),
        ("daughter_text", 1), ("son_in_law_text", 2), ("maternal_grandchild_text", 2),
    ]:
        if form.get(key):
            _add_back(form.get(key), extra_other=prefix_len)
    _add_back(form.get("etc_text"))

    stone_enabled = (category, subcategory) in STONE_PHOTO_COMBOS

    # 스톤포토는 고인별 선택 개수로 계산한다.
    # 예: 고인 2명 선택 → 120,000원 × 2 = 240,000원
    stone_count = 0
    if stone_enabled:
        try:
            stone_count = int(form.get("stone_photo_count") or 0)
        except Exception:
            stone_count = 0
        if stone_count <= 0:
            # 프론트에서 f1_stone_photo, f2_stone_photo ... 로 넘어오는 값 집계
            for i in range(1, slot_count + 1):
                if str(form.get(f"f{i}_stone_photo") or "") in ["yes", "추가", "있음", "on", "true", "1"]:
                    stone_count += 1
        # 구형 저장 데이터/구형 체크박스 호환
        if stone_count <= 0 and form.get("stone_photo") in ["yes", "추가", "있음"]:
            stone_count = 1
    stone_added = stone_enabled and stone_count > 0

    big_k_amt = big_o * bk_u;  big_h_amt = big_h * bh_u
    small_k_amt = small_o * sk_u; small_h_amt = small_h * sh_u
    side_k_amt = side_o * sk_u;  side_h_amt = side_h * sh_u
    back_k_amt = back_o * sk_u;  back_h_amt = back_h * sh_u

    big_cnt = big_o + big_h;    big_amt = big_k_amt + big_h_amt
    small_cnt = small_o + small_h; small_amt = small_k_amt + small_h_amt
    side_cnt = side_o + side_h;  side_amt = side_k_amt + side_h_amt
    back_cnt = back_o + back_h;  back_amt = back_k_amt + back_h_amt

    # 작은글자 통합 (전면소+측면+후면)
    all_small_k = small_o + side_o + back_o
    all_small_h = small_h + side_h + back_h
    all_small_k_amt = all_small_k * sk_u
    all_small_h_amt = all_small_h * sh_u

    stone_amt = pg["stone_photo_price"] * stone_count if stone_added else 0
    total = big_amt + small_amt + side_amt + back_amt + stone_amt

    return {
        "big_cnt": big_cnt, "big_amt": big_amt,
        "big_korean_cnt": big_o, "big_korean_unit": bk_u, "big_korean_amt": big_k_amt,
        "big_hanja_cnt": big_h, "big_hanja_unit": bh_u, "big_hanja_amt": big_h_amt,
        "small_cnt": small_cnt, "small_amt": small_amt,
        "small_korean_cnt": all_small_k, "small_korean_unit": sk_u, "small_korean_amt": all_small_k_amt,
        "small_hanja_cnt": all_small_h, "small_hanja_unit": sh_u, "small_hanja_amt": all_small_h_amt,
        "side_cnt": side_cnt, "side_amt": side_amt,
        "back_cnt": back_cnt, "back_amt": back_amt,
        "stone_enabled": stone_enabled,
        "stone_added": stone_added,
        "stone_count": stone_count,
        "stone_unit": pg["stone_photo_price"],
        "stone_amt": stone_amt,
        "total": total,
        "price_group": rule["price_group"],
        "has_side": rule["has_side"],
    }


def make_summary_item(data, item_id=None, created_at=None):
    summary = calc_summary(data)
    category = data.get("category", "")
    subcategory = data.get("subcategory", "")
    now = created_at or _now_kst()
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
        "stone_photo": f"추가 {summary.get('stone_count', 1)}개" if summary["stone_added"] else "없음",
        "total": summary["total"],
        "jigu": data.get("jigu", ""),
        "yeol": data.get("yeol", ""),
        "ho": data.get("ho", ""),
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
    created_at = data.get("created_at") or _now_kst()
    data["id"] = item_id
    data["created_at"] = created_at
    data["updated_at"] = _now_kst()

    summary_item = make_summary_item(data, item_id=item_id, created_at=created_at)
    saved = storage.save_record(item_id, summary_item, data)
    return jsonify({"ok": True, "id": item_id, "item": saved})


@app.route("/api/list")
def api_list():
    return jsonify(_read_index())


@app.route("/api/load/<item_id>")
def api_load(item_id):
    payload = storage.load_record(item_id)
    if payload is None:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "data": payload})


@app.route("/api/delete/<item_id>", methods=["POST"])
def api_delete(item_id):
    storage.delete_record(item_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
