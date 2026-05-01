-- bimun records — single table replacing saved_data/*.json + saved_data/_index.json
-- Run this in Supabase SQL editor once after creating the project.

create extension if not exists "uuid-ossp";

create table if not exists bimun_records (
  id uuid primary key default uuid_generate_v4(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- Summary fields surfaced in the saved-list drawer (kept as columns for cheap filtering/sorting)
  contract_no text not null default '',
  contractor  text not null default '',
  phone       text not null default '',
  type_label  text not null default '',
  category    text not null default '',
  subcategory text not null default '',
  status      text not null default '접수됨',
  writer      text not null default '',
  designer    text not null default '',
  checker     text not null default '',
  big_amt     integer not null default 0,
  small_amt   integer not null default 0,
  stone_photo text not null default '없음',
  total       integer not null default 0,

  -- Full form payload (everything else the form captures)
  data jsonb not null default '{}'::jsonb
);

create index if not exists idx_bimun_created_at  on bimun_records (created_at desc);
create index if not exists idx_bimun_contract_no on bimun_records (contract_no);
create index if not exists idx_bimun_contractor  on bimun_records (contractor);
create index if not exists idx_bimun_status      on bimun_records (status);

-- Internal staff tool — RLS off. If multi-tenant later, enable RLS and add policies.
alter table bimun_records disable row level security;

-- Auto-bump updated_at on UPDATE
create or replace function bimun_records_set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_bimun_records_updated_at on bimun_records;
create trigger trg_bimun_records_updated_at
  before update on bimun_records
  for each row execute function bimun_records_set_updated_at();
