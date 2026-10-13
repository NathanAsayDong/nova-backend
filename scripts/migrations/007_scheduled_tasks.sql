-- One-time scheduled tasks.
--
-- Responsibilities repeat on time-of-day windows; a scheduled task is the
-- other half: work that should happen once, at a specific moment ("remind me
-- at 3:15", "check the build tomorrow morning"), then be done with.
--
-- The row is kept after it runs. status walks pending -> running -> done or
-- failed (or pending -> cancelled), so Nova can say what happened to a task
-- instead of the task silently vanishing. A failed run is never retried: the
-- agent may already have sent or changed something, and re-firing it would
-- do that twice.
--
-- run_at is timestamptz, so the offset Nova supplies is honoured exactly.
-- The worker claims a row by flipping pending -> running in a single guarded
-- UPDATE, which is what keeps one task from running twice.
--
-- Run with:
--   uv run python scripts/run_migrations.py 007

begin;

create table if not exists scheduled_task (
    id           bigint generated always as identity primary key,
    name         text        not null,
    -- The agent's entire brief when it runs later with nobody present.
    description  text        not null,
    run_at       timestamptz not null,
    status       text        not null default 'pending'
                 check (status in ('pending', 'running', 'done', 'failed', 'cancelled')),
    project_id   bigint,
    report_type  text,
    created_at   timestamptz not null default now(),
    started_at   timestamptz,
    completed_at timestamptz,
    -- The agent's summary on success, the error text on failure.
    result       text
);

-- The worker's query: pending rows whose time has come, oldest first.
create index if not exists scheduled_task_due_idx
    on scheduled_task (run_at)
    where status = 'pending';

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new table until it happens to reload on its own.
notify pgrst, 'reload schema';

commit;
