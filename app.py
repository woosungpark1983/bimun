"""
비문 신청서 계산기 (Flask)
저장 경로 변경:
  SAVE_DIR = r"\\NAS서버\공유폴더\bimun"   (윈도우 NAS)
  SAVE_DIR = "/mnt/nas/bimun"              (리눅스 마운트)
"""

import os, json, uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

SAVE_DIR   = os.path.join(os.path.dirname(__file__), "saved_data")
os.makedirs(SAVE_DIR, exist_ok=True)
INDEX_FILE = os.path.join(SAVE_DIR, "_index.json")

# ─────────────────────────────────────────────
CATALOG = {
    "매장묘":         ["단장", "쌍분"],
    "단납/평장1기":   ["기본"],
    "쌍납/평장부부A": ["기본"],
    "송수재":         ["개인", "부부"],
    "부부A":          ["기본"],
    "납골정":         ["기본"],
    "평장부부B":      ["기본", "1번", "2번", "3번", "4번"],
    "평장1기P":       ["기본"],
    "4기":            ["A", "B", "C", "P", "R"],
    "평장부부P":      ["기본"],
    "평장4기":        ["기본"],
    "평장4기P":       ["기본"],
    "8기":            ["기본"],
    "다기형":         ["12A", "20기", "30기"],
    "12기B":          ["기본"],
    "24기":           ["기본"],
}

PRICE_GROUPS = {
    "A": {"big_korean": 8000,  "big_chinese": 12000, "small_korean": 4000, "small_chinese": 6000,  "stone_photo_price": 120000},
    "B": {"big_korean": 10000, "big_chinese": 15000, "small_korean": 5000, "small_chinese": 7500,  "stone_photo_price": 120000},
    "C": {"big_korean": 16000, "big_chinese": 24000, "small_korean": 8000, "small_chinese": 12000, "stone_photo_price": 120000},
}

TEMPLATE_RULES = {
    "매장묘||단장":         {"price_group":"B","front_style":"maejang", "slots":1,"needs_size":True, "has_side":True, "family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":True, "back_hanja":True, "stone_photo":False},
    "매장묘||쌍분":         {"price_group":"B","front_style":"maejang", "slots":2,"needs_size":True, "has_side":True, "family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":True, "back_hanja":True, "stone_photo":False},
    "단납/평장1기||기본":   {"price_group":"B","front_style":"standard","slots":1,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":False,"stone_photo":False},
    "쌍납/평장부부A||기본": {"price_group":"B","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":False,"stone_photo":False},
    "송수재||개인":         {"price_group":"A","front_style":"standard","slots":1,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":False,"stone_photo":False},
    "송수재||부부":         {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":False,"stone_photo":False},
    "부부A||기본":          {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "납골정||기본":         {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장부부B||기본":      {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":True},
    "평장부부B||1번":       {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장부부B||2번":       {"price_group":"A","front_style":"maejang", "slots":2,"needs_size":False,"has_side":True, "family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":True, "back_hanja":True, "stone_photo":False},
    "평장부부B||3번":       {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장부부B||4번":       {"price_group":"A","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장1기P||기본":       {"price_group":"C","front_style":"standard","slots":1,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":False,"stone_photo":False},
    "4기||A":              {"price_group":"A","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "4기||B":              {"price_group":"A","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":True, "front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "4기||C":              {"price_group":"A","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "4기||P":              {"price_group":"C","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "4기||R":              {"price_group":"A","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장부부P||기본":      {"price_group":"C","front_style":"standard","slots":2,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장4기||기본":        {"price_group":"A","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "평장4기P||기본":       {"price_group":"C","front_style":"standard","slots":4,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "8기||기본":            {"price_group":"C","front_style":"standard","slots":5,"needs_size":False,"has_side":False,"family_phrase":True, "needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "다기형||12A":          {"price_group":"C","front_style":"standard","slots":5,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "다기형||20기":         {"price_group":"C","front_style":"standard","slots":5,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "다기형||30기":         {"price_group":"C","front_style":"standard","slots":5,"needs_size":False,"has_side":False,"family_phrase":False,"needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "12기B||기본":          {"price_group":"C","front_style":"standard","slots":5,"needs_size":False,"has_side":False,"family_phrase":True, "needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
    "24기||기본":           {"price_group":"C","front_style":"standard","slots":5,"needs_size":False,"has_side":False,"family_phrase":True, "needs_orientation":False,"front_hanja":True, "side_hanja":False,"back_hanja":True, "stone_photo":False},
}

# ─────────────────────────────────────────────
def count_chars(text):
    if not text:
        return 0
    return len(str(text).replace(" ", "").replace("\n", "").replace("\r", ""))

def get_rule(category, subcategory):
    return TEMPLATE_RULES.get(f"{category}||{subcategory}", TEMPLATE_RULES["매장묘||단장"])

def make_template_label(category, subcategory, size_type="", orientation=""):
    parts = [category, subcategory]
    if category == "매장묘" and size_type:
        parts.append(size_type)
    if category == "4기" and subcategory == "B" and orientation:
        parts.append(orientation)
    return " / ".join(p for p in parts if p)

def make_save_name(form):
    contract   = str(form.get("contract_no",  "") or "").strip()
    contractor = str(form.get("contractor",    "") or "").strip()
    label      = str(form.get("template_label","") or "").strip()
    parts = []
    if contract:   parts.append(f"#{contract}")
    if contractor: parts.append(contractor)
    name = " ".join(parts)
    if label:
        name = f"{name} ({label})" if name else f"({label})"
    return name or "저장된 신청서"

def default_form():
    f = {
        "contract_no":"", "contractor":"",
        "category":"매장묘", "subcategory":"단장",
        "template_label":"", "size_type":"2.5", "orientation":"",
        "stone_photo":"no",
        "jigu":"", "yeol":"", "ho":"",
        "male_title":"없음", "male_bongwan":"", "male_name":"",
        "female_title":"없음", "female_bongwan":"", "female_name":"",
        "religion_mark":"",
        "jidmyo":"있음",
        # [수정] front_extra 하나로 통일 (maejang/standard 공용)
        "front_extra":"",
        "s1_birth":"", "s1_birth_type":"생", "s1_birth_enabled":"no", "s1_death":"", "s1_death_type":"졸",
        "s2_birth":"", "s2_birth_type":"생", "s2_birth_enabled":"no", "s2_death":"", "s2_death_type":"졸",
        "son_text":"", "daughter_in_law_text":"", "grandson_text":"",
        "daughter_text":"", "son_in_law_text":"", "maternal_grandchild_text":"",
        "etc_text":"", "family_phrase":"",
        "front_type":"korean", "side_type":"korean", "back_type":"korean",
        "memo":"",
        "writer":"", "designer":"", "checker":"",
        "status":"접수됨", "work_memo":"",
        "slot_count":"1", "_current_step":"0",
        "signature_main":"",
        "signature_sign3_0":"",
        "signature_sign3_1":"",
        "signature_sign3_2":"",
    }
    # 고인별 필드 (최대 10명, 세례명 포함)
    for i in range(1, 11):
        f[f"f{i}_name"]       = ""
        f[f"f{i}_baptism"]    = ""   # ← 고인별 세례명 (큰글씨)
        f[f"f{i}_birth"]      = ""
        f[f"f{i}_birth_type"] = "생"
        f[f"f{i}_birth_enabled"] = "no"
        f[f"f{i}_death"]      = ""
        f[f"f{i}_death_type"] = "졸"
    return f

# ─────────────────────────────────────────────
# 계산 로직
# [핵심수정] front_extra: name 충돌 제거, 고인별 세례명(f{i}_baptism) 큰글씨 계산
# ─────────────────────────────────────────────
def calc_summary(form):
    rule = get_rule(form["category"], form["subcategory"])
    pg   = PRICE_GROUPS[rule["price_group"]]

    ft = str(form.get("front_type", "korean") or "korean")
    st = str(form.get("side_type",  "korean") or "korean")
    bt = str(form.get("back_type",  "korean") or "korean")

    if form["category"] == "평장4기" and form.get("stone_photo") == "yes":
        bt = "korean"

    big_u    = pg["big_korean"]   if ft == "korean" else pg["big_chinese"]
    sm_front = pg["small_korean"] if ft == "korean" else pg["small_chinese"]
    sm_side  = pg["small_korean"] if st == "korean" else pg["small_chinese"]
    sm_back  = pg["small_korean"] if bt == "korean" else pg["small_chinese"]

    big_cnt = sm_front_cnt = side_cnt = back_cnt = 0

    # 공용 front_extra (maejang/standard 모두)
    extra = str(form.get("front_extra", "") or "").strip()

    if rule["front_style"] == "maejang":
        if form.get("religion_mark", ""):
            big_cnt += 1
        if str(form.get("jidmyo", "있음") or "있음") in ["있음", "유", "yes", "true"]:
            big_cnt += 2  # 지묘
        if extra:
            big_cnt += count_chars(extra)

        if str(form.get("male_title", "없음")) != "없음":
            big_cnt += count_chars(form.get("male_title", ""))
            big_cnt += count_chars(form.get("male_bongwan", ""))
            big_cnt += count_chars(form.get("male_name", ""))
            big_cnt += 1  # 공

        if str(form.get("female_title", "없음")) != "없음":
            big_cnt += count_chars(form.get("female_title", ""))
            big_cnt += count_chars(form.get("female_bongwan", ""))
            big_cnt += count_chars(form.get("female_name", ""))
            big_cnt += 1  # 씨

        if rule["has_side"]:
            for prefix in ["s1", "s2"]:
                b  = str(form.get(f"{prefix}_birth", "") or "")
                d  = str(form.get(f"{prefix}_death", "") or "")
                dt = str(form.get(f"{prefix}_death_type", "졸") or "졸")
                if dt == "없음":
                    dt = "졸"
                bt_expr = str(form.get(f"{prefix}_birth_type", "없음") or "없음")
                if b.strip():
                    side_cnt += count_chars(b) + (0 if bt_expr == "없음" else count_chars(bt_expr))
                if d.strip():
                    side_cnt += count_chars(d) + count_chars(dt)

    else:  # standard
        if form.get("religion_mark", ""):
            big_cnt += 1
        if rule["family_phrase"]:
            fp = str(form.get("family_phrase", "") or "")
            if fp.strip():
                big_cnt += count_chars(fp) + 5
        if extra:
            big_cnt += count_chars(extra)

        try:
            slot_count = int(form.get("slot_count", 1))
        except (ValueError, TypeError):
            slot_count = 1
        slot_count = min(max(slot_count, 1), 10)

        for i in range(1, slot_count + 1):
            name     = str(form.get(f"f{i}_name",    "") or "")
            baptism  = str(form.get(f"f{i}_baptism", "") or "")  # 고인별 세례명
            birth    = str(form.get(f"f{i}_birth",   "") or "")
            btype    = str(form.get(f"f{i}_birth_type", "없음") or "없음")
            death    = str(form.get(f"f{i}_death",   "") or "")
            dtype    = str(form.get(f"f{i}_death_type", "졸") or "졸")
            if dtype == "없음":
                dtype = "졸"

            if name.strip():
                big_cnt += count_chars(name)
            if baptism.strip():
                big_cnt += count_chars(baptism)   # 세례명도 큰글씨
            if birth.strip():
                sm_front_cnt += count_chars(birth) + (0 if btype == "없음" else count_chars(btype))
            if death.strip():
                sm_front_cnt += count_chars(death) + count_chars(dtype)

    # 후면
    BACK_FIELDS = [
        ("son_text",1),("daughter_in_law_text",2),("grandson_text",1),
        ("daughter_text",1),("son_in_law_text",2),("maternal_grandchild_text",2),
    ]
    for field, plen in BACK_FIELDS:
        v = str(form.get(field, "") or "")
        if v.strip():
            back_cnt += plen + count_chars(v)
    etc = str(form.get("etc_text", "") or "")
    if etc.strip():
        back_cnt += count_chars(etc)

    big_amt      = big_cnt      * big_u
    sm_front_amt = sm_front_cnt * sm_front
    side_amt     = side_cnt     * sm_side
    back_amt     = back_cnt     * sm_back
    stone_amt    = pg["stone_photo_price"] if (rule["stone_photo"] and form.get("stone_photo") == "yes") else 0
    total_amt    = big_amt + sm_front_amt + side_amt + back_amt + stone_amt

    fl = "한글" if ft == "korean" else "한자"
    sl = "한글" if st == "korean" else "한자"
    bl = "한글" if bt == "korean" else "한자"

    lines = [(f"전면 큰글자 ({fl})", big_cnt, big_u, big_amt)]
    if sm_front_cnt:
        lines.append((f"전면 작은글자 ({fl})", sm_front_cnt, sm_front, sm_front_amt))
    if rule["has_side"]:
        lines.append((f"측면 ({sl})", side_cnt, sm_side, side_amt))
    lines.append((f"후면 ({bl})", back_cnt, sm_back, back_amt))
    if stone_amt:
        lines.append(("스톤포토", None, None, stone_amt))

    return {
        "lines":    lines,
        "total":    total_amt,
        "big_cnt":  big_cnt,
        "sm_cnt":   sm_front_cnt + side_cnt + back_cnt,
        "big_amt":  big_amt,
        "sm_amt":   sm_front_amt + side_amt + back_amt,
        "stone_amt":stone_amt,
    }

# ─────────────────────────────────────────────
def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(idx):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home():
    today   = datetime.now()
    form    = default_form()
    summary = None
    load_id = request.args.get("load")

    # 새로 작성하기: 빈 폼 반환 (대분류/세부유형 등 모두 초기화)
    if request.method == "GET" and request.args.get("new") == "1":
        return render_template("index.html",
            form=form, summary=None, today=today,
            catalog_json=json.dumps(CATALOG, ensure_ascii=False),
            rules_json=json.dumps(TEMPLATE_RULES, ensure_ascii=False),
            saved_list=load_index(),
            save_dir=os.path.abspath(SAVE_DIR),
            just_saved="0",
        )

    if load_id:
        idx   = load_index()
        entry = next((e for e in idx if e["id"] == load_id), None)
        if entry:
            fp = os.path.join(SAVE_DIR, entry["filename"])
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                form.update(saved.get("form", {}))
                form["_current_step"] = "1"
                summary = calc_summary(form)

    if request.method == "POST":
        action = request.form.get("_action") or request.form.get("action") or "calc"
        form["_current_step"] = request.form.get("_current_step", form.get("_current_step", "0"))

        # 모든 폼 필드 수집
        for k in list(form.keys()):
            form[k] = request.form.get(k, form[k])

        # slot_count
        try:
            slot_count = int(request.form.get("slot_count", 1))
        except (ValueError, TypeError):
            slot_count = 1
        form["slot_count"] = str(slot_count)

        # 고인 슬롯 명시적 수집 (세례명 포함)
        for i in range(1, 11):
            form[f"f{i}_name"]       = request.form.get(f"f{i}_name",       "")
            form[f"f{i}_baptism"]    = request.form.get(f"f{i}_baptism",    "")
            form[f"f{i}_birth"]      = request.form.get(f"f{i}_birth",      "")
            form[f"f{i}_birth_type"] = request.form.get(f"f{i}_birth_type", "생")
            form[f"f{i}_birth_enabled"] = request.form.get(f"f{i}_birth_enabled", "no")
            form[f"f{i}_death"]      = request.form.get(f"f{i}_death",      "")
            form[f"f{i}_death_type"] = request.form.get(f"f{i}_death_type", "졸")

        # [핵심] front_extra: 단일 필드명으로 수집
        form["front_extra"] = request.form.get("front_extra", "")

        # 서명 이미지(data URL) 저장
        form["signature_main"] = request.form.get("signature_main", form.get("signature_main", ""))
        form["signature_sign3_0"] = request.form.get("signature_sign3_0", form.get("signature_sign3_0", ""))
        form["signature_sign3_1"] = request.form.get("signature_sign3_1", form.get("signature_sign3_1", ""))
        form["signature_sign3_2"] = request.form.get("signature_sign3_2", form.get("signature_sign3_2", ""))
        # religion_mark: maejang/standard 두 select가 있으므로 getlist 첫 번째 비어있지 않은 값 사용
        rm_vals = [v for v in request.form.getlist("religion_mark") if v]
        form["religion_mark"] = rm_vals[0] if rm_vals else ""

        for _death_key in ["s1_death_type", "s2_death_type"]:
            if form.get(_death_key, "졸") == "없음":
                form[_death_key] = "졸"

        form["template_label"] = make_template_label(
            form["category"], form["subcategory"],
            form["size_type"], form["orientation"]
        )
        summary = calc_summary(form)

        if action == "save":
            rid      = str(uuid.uuid4())[:8]
            now_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            now_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname    = f"{now_file}_{rid}.json"
            save_name = make_save_name(form)

            entry = {
                "id":             rid,
                "created_at":     now_str,
                "save_name":      save_name,
                "category":       form["category"],
                "subcategory":    form["subcategory"],
                "template_label": form["template_label"],
                "contractor":     form["contractor"],
                "contract_no":    form["contract_no"],
                "memo":           form.get("memo", ""),
                "writer":         form.get("writer", ""),
                "designer":       form.get("designer", ""),
                "checker":        form.get("checker", ""),
                "status":         form.get("status", "접수됨"),
                "work_memo":      form.get("work_memo", ""),
                "total_amt":      summary["total"],
                "big_cnt":        summary["big_cnt"],
                "sm_cnt":         summary["sm_cnt"],
                "stone_amt":      summary.get("stone_amt", 0),
                "sign_write":     bool(form.get("signature_sign3_0")),
                "sign_work":      bool(form.get("signature_sign3_1")),
                "sign_check":     bool(form.get("signature_sign3_2")),
                "filename":       fname,
            }
            full = {"id":rid,"created_at":now_str,"save_name":save_name,"form":form,"summary":summary["lines"]}
            with open(os.path.join(SAVE_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(full, f, ensure_ascii=False, indent=2)
            idx = load_index()
            idx.insert(0, entry)
            save_index(idx)
            return redirect(url_for("home", load=rid, saved=1))

    if not form["template_label"]:
        for _death_key in ["s1_death_type", "s2_death_type"]:
            if form.get(_death_key, "졸") == "없음":
                form[_death_key] = "졸"

        form["template_label"] = make_template_label(
            form["category"], form["subcategory"],
            form["size_type"], form["orientation"]
        )

    return render_template("index.html",
        form=form, summary=summary, today=today,
        catalog_json=json.dumps(CATALOG, ensure_ascii=False),
        rules_json=json.dumps(TEMPLATE_RULES, ensure_ascii=False),
        saved_list=load_index(),
        save_dir=os.path.abspath(SAVE_DIR),
        just_saved=request.args.get("saved", "0"),
    )


@app.route("/api/delete/<rid>", methods=["DELETE"])
def api_delete(rid):
    idx   = load_index()
    entry = next((e for e in idx if e["id"] == rid), None)
    if entry:
        fp = os.path.join(SAVE_DIR, entry["filename"])
        if os.path.exists(fp):
            os.remove(fp)
        idx = [e for e in idx if e["id"] != rid]
        save_index(idx)
    return jsonify({"ok": True})


@app.route("/api/savedir")
def api_savedir():
    return jsonify({"path": os.path.abspath(SAVE_DIR)})


if __name__ == "__main__":
    print(f"\n✅ 비문 신청서 계산기")
    print(f"   저장경로: {os.path.abspath(SAVE_DIR)}")
    print(f"   주소:     http://127.0.0.1:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
