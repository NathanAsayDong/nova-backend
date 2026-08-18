-- Meeting mode: capture, transcript, retrieval chunks, and notes.
--
-- Nova gains a second mode. In agent mode it listens for a turn and answers;
-- in meeting mode it does nothing but transcribe, and a meeting row is what
-- says which mode it is in — status = 'recording' IS meeting mode, so the
-- state survives a restart and there is no in-memory flag to drift.
--
-- Meetings hang off project so a project's meetings, conversations, and memory
-- all sit under the same roof; project_id is nullable for meetings that belong
-- to nothing in particular.
--
-- Run with:
--   uv run python scripts/run_migrations.py 004

begin;

create extension if not exists vector;

create table if not exists meeting (
    id         bigserial   primary key,
    uuid       uuid        not null unique default gen_random_uuid(),
    title      text,
    status     text        not null default 'recording',
    started_at timestamptz not null default now(),
    ended_at   timestamptz,
    audio_path text
);

-- project.id's width is not knowable from here (it predates these migrations),
-- and an FK whose type does not match the referenced column fails at creation.
-- Read the type and build the column from it rather than betting on bigint.
do $$
declare
    project_id_type text;
begin
    if not exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'meeting'
          and column_name = 'project_id'
    ) then
        select data_type into project_id_type
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'project'
          and column_name = 'id';

        if project_id_type is null then
            raise exception 'project.id not found — is the project table missing?';
        end if;

        -- Built by concatenation rather than with format(). psycopg2 runs
        -- this file and treats a percent sign anywhere in it -- code or
        -- comment -- as a bind placeholder, so the file must contain none.
        -- project_id_type comes from the catalog, not from user input.
        execute 'alter table meeting add column project_id '
             || project_id_type
             || ' references project(id) on delete set null';
    end if;
end $$;

alter table meeting drop constraint if exists meeting_status_check;
alter table meeting
    add constraint meeting_status_check
    check (status in ('recording', 'processing', 'complete', 'failed'));

-- "Is there a meeting running right now" is asked on every client poll and on
-- every start_meeting call, so keep it a one-row partial index scan.
create unique index if not exists meeting_single_active_idx
    on meeting ((status)) where status = 'recording';

create index if not exists meeting_project_idx on meeting (project_id, started_at desc);
create index if not exists meeting_started_idx on meeting (started_at desc);

-- One committed window of transcript. No speaker columns: diarization was
-- considered and deliberately dropped, so a segment is timed text and nothing
-- more. start_ms/end_ms are offsets from the start of the recording.
create table if not exists meeting_segment (
    id         bigserial primary key,
    meeting_id bigint    not null references meeting(id) on delete cascade,
    start_ms   integer   not null,
    end_ms     integer   not null,
    text       text      not null
);
create index if not exists meeting_segment_meeting_idx
    on meeting_segment (meeting_id, start_ms);

-- Retrieval passages: segments rolled up to something worth embedding.
-- 1536 dims to match EmbeddingService (text-embedding-3-small) and the
-- existing memory_chunk column, so one pgvector setup serves both.
create table if not exists meeting_chunk (
    id         bigserial primary key,
    meeting_id bigint    not null references meeting(id) on delete cascade,
    content    text      not null,
    embedding  vector(1536),
    start_ms   integer   not null,
    end_ms     integer   not null
);
create index if not exists meeting_chunk_meeting_idx on meeting_chunk (meeting_id);

create table if not exists meeting_notes (
    id           bigserial   primary key,
    meeting_id   bigint      not null references meeting(id) on delete cascade,
    summary_md   text        not null,
    decisions    jsonb       not null default '[]'::jsonb,
    action_items jsonb       not null default '[]'::jsonb,
    model        text,
    created_at   timestamptz not null default now()
);
create index if not exists meeting_notes_meeting_idx
    on meeting_notes (meeting_id, created_at desc);

commit;

-- Nearest-neighbour search over meeting passages, mirroring the
-- match_memory_chunks function MemoryChunkDao already calls. The filters are
-- applied before the ordering on purpose: filtering afterwards would rank
-- every passage ever recorded and then throw most of the work away.
create or replace function match_meeting_chunks(
    query_embedding vector(1536),
    match_count     int         default 5,
    filter_project  bigint      default null,
    filter_meeting  bigint      default null,
    since           timestamptz default null
)
returns table (
    id            bigint,
    meeting_id    bigint,
    meeting_uuid  uuid,
    meeting_title text,
    started_at    timestamptz,
    content       text,
    start_ms      integer,
    end_ms        integer,
    similarity    double precision
)
language sql
stable
as $$
    select c.id,
           c.meeting_id,
           m.uuid,
           m.title,
           m.started_at,
           c.content,
           c.start_ms,
           c.end_ms,
           1 - (c.embedding <=> query_embedding) as similarity
    from meeting_chunk c
    join meeting m on m.id = c.meeting_id
    where c.embedding is not null
      and (filter_project is null or m.project_id = filter_project)
      and (filter_meeting is null or m.id = filter_meeting)
      and (since is null or m.started_at >= since)
    order by c.embedding <=> query_embedding
    limit match_count;
$$;

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new tables until it happens to reload on its own.
notify pgrst, 'reload schema';
