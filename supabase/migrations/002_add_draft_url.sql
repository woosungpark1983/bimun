-- Migration 002 — record the Supabase Storage URL of the 사인프로 시안 jpg
-- once it's been uploaded for a given 비문 신청서. Empty string = not yet uploaded.

alter table bimun_records add column if not exists draft_url text not null default '';

create index if not exists idx_bimun_has_draft
  on bimun_records ((draft_url <> ''));
