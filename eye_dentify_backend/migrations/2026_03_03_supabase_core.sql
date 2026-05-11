-- Supabase core schema for eye_dentify_db
-- Run after 2026_02_04_alert_lifecycle.sql

create extension if not exists "pgcrypto";

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique,
    full_name text not null,
    role text not null default 'user',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Keep compatibility with legacy integer camera_id and new UUID id.
create table if not exists public.cameras (
    id uuid primary key default gen_random_uuid(),
    camera_id bigserial unique,
    name text not null,
    camera_name text,
    location text,
    location_name text,
    lat double precision,
    lng double precision,
    latitude double precision,
    longitude double precision,
    status text default 'active',
    api_key text,
    camera_reliability_score numeric default 1.0,
    created_at timestamptz default now()
);

create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null,
    body text not null,
    type text not null default 'system',
    read_at timestamptz,
    created_at timestamptz default now(),
    metadata jsonb default '{}'::jsonb
);

create table if not exists public.device_tokens (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    token text not null unique,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

alter table if exists public.alerts
    add column if not exists ai_summary text,
    add column if not exists dismissed_at timestamptz,
    add column if not exists read_at timestamptz,
    add column if not exists acknowledged_at timestamptz;

alter table if exists public.detections
    add column if not exists source text default 'camera',
    add column if not exists verified_at timestamptz;

-- RLS
alter table public.profiles enable row level security;
alter table public.missing_persons enable row level security;
alter table public.alerts enable row level security;
alter table public.media enable row level security;
alter table public.detections enable row level security;
alter table public.system_logs enable row level security;
alter table public.cameras enable row level security;
alter table public.device_tokens enable row level security;
alter table public.notifications enable row level security;

drop policy if exists "profiles_self_select" on public.profiles;
create policy "profiles_self_select"
on public.profiles
for select
using (auth.uid() = id);

drop policy if exists "profiles_self_update" on public.profiles;
create policy "profiles_self_update"
on public.profiles
for update
using (auth.uid() = id)
with check (auth.uid() = id);

drop policy if exists "missing_persons_owner_all" on public.missing_persons;
create policy "missing_persons_owner_all"
on public.missing_persons
for all
using (auth.uid()::text = user_id::text)
with check (auth.uid()::text = user_id::text);

drop policy if exists "alerts_owner_select" on public.alerts;
create policy "alerts_owner_select"
on public.alerts
for select
using (auth.uid()::text = user_id::text);

drop policy if exists "alerts_owner_update" on public.alerts;
create policy "alerts_owner_update"
on public.alerts
for update
using (auth.uid()::text = user_id::text)
with check (auth.uid()::text = user_id::text);

drop policy if exists "media_owner_all" on public.media;
create policy "media_owner_all"
on public.media
for all
using (
    exists (
        select 1 from public.missing_persons mp
        where mp.missing_person_id = media.missing_person_id
        and mp.user_id::text = auth.uid()::text
    )
)
with check (
    exists (
        select 1 from public.missing_persons mp
        where mp.missing_person_id = media.missing_person_id
        and mp.user_id::text = auth.uid()::text
    )
);

drop policy if exists "notifications_owner_all" on public.notifications;
create policy "notifications_owner_all"
on public.notifications
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "device_tokens_owner_all" on public.device_tokens;
create policy "device_tokens_owner_all"
on public.device_tokens
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "detections_service_role_all" on public.detections;
create policy "detections_service_role_all"
on public.detections
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "alerts_service_role_all" on public.alerts;
create policy "alerts_service_role_all"
on public.alerts
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "system_logs_service_role_all" on public.system_logs;
create policy "system_logs_service_role_all"
on public.system_logs
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "cameras_service_role_all" on public.cameras;
create policy "cameras_service_role_all"
on public.cameras
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
