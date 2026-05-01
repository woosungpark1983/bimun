-- Migration 001 — add 묘 위치 (지구/열/호) summary columns so the saved-list can
-- search and display the same plot location that the paper 비문 신청서 records.
-- Run this once in Supabase SQL editor.

alter table bimun_records add column if not exists jigu text not null default '';
alter table bimun_records add column if not exists yeol text not null default '';
alter table bimun_records add column if not exists ho   text not null default '';

create index if not exists idx_bimun_jigu_yeol_ho
  on bimun_records (jigu, yeol, ho);
