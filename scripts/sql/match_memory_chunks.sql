-- Nearest-neighbor lookup for memory chunks, called by MemoryChunkDao via
-- PostgREST rpc. Run this in the Supabase SQL editor.
--
-- Scoping: filter_project_id null -> search all memory; otherwise match that
-- project's chunks plus general (project-less) chunks.
--
-- Also required for the memory system:
--   alter table memory_chunk alter column project_id drop not null;

create or replace function match_memory_chunks(
  query_embedding vector(1536),
  match_count int default 5,
  filter_project_id int default null
)
returns table (
  id int,
  content text,
  project_id int,
  similarity float
)
language sql
stable
as $$
  select
    mc.id,
    mc.content,
    mc.project_id,
    1 - (mc.embedding <=> query_embedding) as similarity
  from memory_chunk mc
  where mc.embedding is not null
    and (
      filter_project_id is null
      or mc.project_id = filter_project_id
      or mc.project_id is null
    )
  order by mc.embedding <=> query_embedding
  limit match_count;
$$;
