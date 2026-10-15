-- People Nova may recognise through the glasses camera, and their faces.
--
-- Only people Nathan enrolled, with their agreement, are ever in here.
-- consent_note records what was agreed and how; consented_at when. A face the
-- matcher does not recognise is never written anywhere: it is "someone" in
-- the turn and gone after it.
--
-- face_sample holds SFace embeddings (128-d), never the photos they came
-- from. Deleting a person cascades to every sample, so "forget Tom" leaves
-- nothing of Tom behind.
--
-- Names are unique case-insensitively, so "tom" cannot be enrolled twice
-- under two spellings and split his samples across two rows.
--
-- Run with:
--   uv run python scripts/run_migrations.py 008

begin;

create extension if not exists vector;

create table if not exists person (
    id           bigint generated always as identity primary key,
    name         text        not null,
    consent_note text        not null,
    consented_at timestamptz not null default now(),
    created_at   timestamptz not null default now()
);

create unique index if not exists person_name_lower_key
    on person (lower(name));

create table if not exists face_sample (
    id         bigint generated always as identity primary key,
    person_id  bigint      not null references person (id) on delete cascade,
    embedding  vector(128) not null,
    created_at timestamptz not null default now()
);

create index if not exists face_sample_person_idx
    on face_sample (person_id);

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new tables until it happens to reload on its own.
notify pgrst, 'reload schema';

commit;
