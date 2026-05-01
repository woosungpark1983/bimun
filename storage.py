"""Supabase-backed storage for bimun records.

Replaces the previous saved_data/*.json + _index.json files. The five public
functions below are the only ones app.py talks to — they map 1:1 onto the old
behavior so the API contract with the frontend is unchanged.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from supabase import Client, create_client

# Display all timestamps in Korea Standard Time — Supabase stores timestamptz in UTC
# but the app and customer-facing list have always shown local KST.
_KST = timezone(timedelta(hours=9))

_TABLE = "bimun_records"
_DRAFT_BUCKET = "bimun-drafts"

_SUMMARY_COLS = (
    "id,created_at,contract_no,contractor,phone,type_label,"
    "category,subcategory,status,writer,designer,checker,"
    "big_amt,small_amt,stone_photo,total,"
    "jigu,yeol,ho,draft_url"
)

_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_KEY", "").strip()
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY env vars are required. "
                "Copy .env.example to .env (local) or set them in Vercel project settings."
            )
        _client = create_client(url, key)
    return _client


def _fmt_ts(ts: Optional[str]) -> str:
    """Format a Supabase timestamptz ISO string as 'YYYY-MM-DD HH:MM' in KST."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_KST).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return ts[:16] if len(ts) >= 16 else ts


def _to_summary(row: dict) -> dict:
    return {
        "id":          row.get("id", ""),
        "created_at":  _fmt_ts(row.get("created_at")),
        "contract_no": row.get("contract_no", ""),
        "contractor":  row.get("contractor", ""),
        "phone":       row.get("phone", ""),
        "type_label":  row.get("type_label", ""),
        "category":    row.get("category", ""),
        "subcategory": row.get("subcategory", ""),
        "status":      row.get("status", "접수됨"),
        "writer":      row.get("writer", ""),
        "designer":    row.get("designer", ""),
        "checker":     row.get("checker", ""),
        "big_amt":     row.get("big_amt", 0),
        "small_amt":   row.get("small_amt", 0),
        "stone_photo": row.get("stone_photo", "없음"),
        "total":       row.get("total", 0),
        "jigu":        row.get("jigu", ""),
        "yeol":        row.get("yeol", ""),
        "ho":          row.get("ho", ""),
        "draft_url":   row.get("draft_url", ""),
    }


def list_records() -> list[dict]:
    """Return summary rows ordered newest-first. Used by /api/list and the index page."""
    res = (
        _get_client()
        .table(_TABLE)
        .select(_SUMMARY_COLS)
        .order("created_at", desc=True)
        .execute()
    )
    return [_to_summary(r) for r in (res.data or [])]


def save_record(item_id: str, summary_item: dict, full_data: dict) -> dict:
    """Upsert one record. summary_item provides the indexed columns; full_data is the
    complete form payload stored as JSONB."""
    row = {
        "id":          item_id,
        "contract_no": summary_item.get("contract_no", "") or "",
        "contractor":  summary_item.get("contractor", "") or "",
        "phone":       summary_item.get("phone", "") or "",
        "type_label":  summary_item.get("type_label", "") or "",
        "category":    summary_item.get("category", "") or "",
        "subcategory": summary_item.get("subcategory", "") or "",
        "status":      summary_item.get("status", "접수됨") or "접수됨",
        "writer":      summary_item.get("writer", "") or "",
        "designer":    summary_item.get("designer", "") or "",
        "checker":     summary_item.get("checker", "") or "",
        "big_amt":     int(summary_item.get("big_amt", 0) or 0),
        "small_amt":   int(summary_item.get("small_amt", 0) or 0),
        "stone_photo": summary_item.get("stone_photo", "없음") or "없음",
        "total":       int(summary_item.get("total", 0) or 0),
        "jigu":        summary_item.get("jigu", "") or "",
        "yeol":        summary_item.get("yeol", "") or "",
        "ho":          summary_item.get("ho", "") or "",
        "data":        full_data,
    }
    res = _get_client().table(_TABLE).upsert(row).execute()
    saved = (res.data or [row])[0]
    return _to_summary(saved)


def load_record(item_id: str) -> Optional[dict]:
    """Return the full form payload for a single record, or None if not found."""
    res = (
        _get_client()
        .table(_TABLE)
        .select("id,data")
        .eq("id", item_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    payload: dict[str, Any] = dict(rows[0].get("data") or {})
    payload["id"] = rows[0].get("id", item_id)
    return payload


def delete_record(item_id: str) -> None:
    # Best-effort: remove any uploaded 시안 from Storage first, then drop the row.
    try:
        delete_draft(item_id)
    except Exception:
        pass
    _get_client().table(_TABLE).delete().eq("id", item_id).execute()


# ── Storage operations (시안 jpg) — service_role required to manage bucket objects ──

def _get_admin_client() -> Client:
    """Service-role client for privileged ops (Storage uploads, schema-bypass writes)."""
    sk = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    url = os.environ.get("SUPABASE_URL", "").strip()
    if not sk or not url:
        raise RuntimeError(
            "SUPABASE_SERVICE_KEY and SUPABASE_URL are required for admin operations. "
            "Add SUPABASE_SERVICE_KEY to .env (local) and to Vercel project settings."
        )
    return create_client(url, sk)


def upload_draft(item_id: str, file_bytes: bytes, content_type: str) -> str:
    """Upload a 사인프로 시안 image, return its public URL, and persist to draft_url."""
    admin = _get_admin_client()
    storage_api = admin.storage.from_(_DRAFT_BUCKET)
    # Always upsert under the record id so re-uploads replace the previous file.
    storage_api.upload(
        item_id,
        file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    public_url = storage_api.get_public_url(item_id).rstrip("?")
    # Cache-bust so browsers don't show the previous draft after a replace.
    public_url = f"{public_url}?v={item_id[:8]}-{len(file_bytes)}"
    admin.table(_TABLE).update({"draft_url": public_url}).eq("id", item_id).execute()
    return public_url


def delete_draft(item_id: str) -> None:
    """Remove the 시안 image from Storage and clear draft_url. Silent if not present."""
    admin = _get_admin_client()
    try:
        admin.storage.from_(_DRAFT_BUCKET).remove([item_id])
    except Exception:
        pass
    admin.table(_TABLE).update({"draft_url": ""}).eq("id", item_id).execute()
