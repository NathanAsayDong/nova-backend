-- Coding sessions: Claude Code threads Nova starts on Nate's Mac.
--
-- The full transcript is NOT stored here. Claude Code already persists every
-- session to ~/.claude/projects on the Mac that ran it, and duplicating that
-- would mean two records that can disagree. What the tower needs is the part
-- the Mac does not know: which project a session belongs to, what Nova told
-- the user it was for, and enough recent history to answer "how's it going"
-- without waking the laptop.
--
-- coding_event is therefore a bounded, prunable tail rather than an archive —
-- the authoritative log lives on the Mac, and the branch is the deliverable.
--
-- Run with:
--   uv run python scripts/run_migrations.py 005

begin;

create table if not exists coding_session (
    id           bigserial   primary key,
    -- Nova mints this and pins Claude Code to it, so one id addresses the row,
    -- the agent's live client, and the .jsonl on disk.
    session_id   uuid        not null unique,
    title        text        not null,
    status       text        not null default 'starting',
    repo         text        not null,
    branch       text,
    cwd          text,
    instructions text        not null,
    -- Cheap deterministic rollup, rewritten on every event. This is what a
    -- spoken "how's it going" reads: it has to be instant and free, which an
    -- LLM summary is not.
    rollup       text,
    -- The model's own last word, when a turn has produced one.
    last_result  text,
    last_seq     bigint      not null default 0,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),
    closed_at    timestamptz
);

-- project.id's width is not knowable from here, and an FK whose type does not
-- match the referenced column fails at creation. Built by concatenation
-- rather than with format(): psycopg2 runs this file and treats a percent
-- sign anywhere in it -- code or comment -- as a bind placeholder, so the
-- file must contain none. (004_meetings.sql learned this the same way.)
do $$
declare
    project_id_type text;
begin
    if not exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'coding_session'
          and column_name = 'project_id'
    ) then
        select data_type into project_id_type
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'project'
          and column_name = 'id';

        if project_id_type is null then
            raise exception 'project.id not found -- is the project table missing?';
        end if;

        execute 'alter table coding_session add column project_id '
             || project_id_type
             || ' references project(id) on delete set null';
    end if;
end $$;

create index if not exists coding_session_status_idx on coding_session (status);
create index if not exists coding_session_project_idx on coding_session (project_id);

create table if not exists coding_event (
    id         bigserial   primary key,
    session_id uuid        not null references coding_session(session_id) on delete cascade,
    seq        bigint      not null,
    type       text        not null,
    payload    jsonb       not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (session_id, seq)
);

create index if not exists coding_event_session_seq_idx on coding_event (session_id, seq desc);

commit;
