-- Rename update.conversation_id -> update.conversation_uuid.
--
-- The column has always held a conversation *uuid*, and every other table
-- that links to a conversation calls it conversation_uuid (see
-- message.conversation_uuid). The Update model, UpdateService, and the
-- /updates API all use conversation_uuid too — the database was the only
-- place still saying conversation_id, so an insert carrying a linked
-- conversation failed with PGRST204 while an unlinked one silently worked
-- (to_payload drops None fields).
--
-- Safe to run: the column is only renamed, never dropped, and the table is
-- empty. Reverse with the inverse rename if anything else depends on the old
-- name.
--
-- Run against the Supabase Postgres database:
--   psql "$SUPABASE_DB_URL" -f scripts/migrations/002_update_conversation_uuid.sql

begin;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'update'
          and column_name = 'conversation_id'
    ) and not exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'update'
          and column_name = 'conversation_uuid'
    ) then
        alter table "update" rename column conversation_id to conversation_uuid;
    end if;
end $$;

commit;

-- PostgREST answers the DAOs and serves columns from a cached schema; without
-- this it can keep rejecting the new name until it happens to reload.
notify pgrst, 'reload schema';
