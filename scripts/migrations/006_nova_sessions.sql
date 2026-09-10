-- Login sessions for the hosted frontend.
--
-- Nova has exactly one user, and that user's credentials live in the API's
-- environment rather than in a table. What this table holds is the thing that
-- must outlive a process restart: which bearer tokens are currently valid.
--
-- The token itself is never stored. The row keeps a SHA-256 of it, so a read
-- of this table (a leaked dump, a stray SELECT in a screenshot) yields nothing
-- a browser could present. The browser holds the only copy.
--
-- Sessions slide: every authenticated request past a threshold refreshes
-- expires_at, so a device in daily use stays logged in and one left in a
-- drawer lapses. revoked_at is set by "sign out" and "sign out everywhere";
-- a revoked row is kept rather than deleted so the history is readable.
--
-- Run with:
--   uv run python scripts/run_migrations.py 006

begin;

create table if not exists nova_sessions (
    id           uuid        primary key default gen_random_uuid(),
    token_hash   text        not null unique,
    created_at   timestamptz not null default now(),
    expires_at   timestamptz not null,
    last_seen_at timestamptz not null default now(),
    -- What logged in, for the "your devices" list. Informational only.
    user_agent   text,
    ip           text,
    revoked_at   timestamptz
);

create index if not exists nova_sessions_expires_idx on nova_sessions (expires_at);

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new table until it happens to reload on its own.
notify pgrst, 'reload schema';

commit;
