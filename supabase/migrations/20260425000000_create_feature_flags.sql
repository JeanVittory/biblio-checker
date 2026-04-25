-- Feature flags table — runtime toggles read by the frontend without redeploy.
-- Read/write restricted to service_role; flags are NOT exposed to anon clients.
create table public.feature_flags (
  flag_key text primary key,
  enabled boolean not null default false,
  description text,
  updated_at timestamptz not null default now()
);

create or replace function public.touch_feature_flags_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger feature_flags_set_updated_at
  before update on public.feature_flags
  for each row execute function public.touch_feature_flags_updated_at();

alter table public.feature_flags enable row level security;

create policy "service_role_full_access" on public.feature_flags
  for all
  to service_role
  using (true)
  with check (true);

insert into public.feature_flags (flag_key, enabled, description)
values (
  'upload_enabled',
  false,
  'Allows arbitrary document upload on /app and the primary landing CTAs. When false, only the demo/sample flow is available.'
)
on conflict (flag_key) do nothing;
