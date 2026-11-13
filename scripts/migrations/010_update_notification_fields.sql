-- Notification-queue fields on the existing "update" table.
--
-- Nova's nightly self-improvement system (and the background-agent /
-- coding-task / scheduled-task paths generally) need Nova to mention
-- finished work to Nate inside the conversation, without him having to ask.
-- Rather than add a parallel "notification" table, this extends the update
-- table that already models exactly this ("Nova's way of surfacing finished
-- background work" -- src/service/update_service.py): a finished run writes
-- a row here, same as it always has, just now tagged with WHAT kind of work
-- it was and whether it SUCCEEDED or FAILED.
--
-- Everything else the feature needs already exists on this table:
--   id              -> "id" (existing primary key)
--   title + summary -> "update_message" (existing; kept as one field rather
--                      than splitting title/summary, matching how every
--                      existing caller already writes one spoken-ready line)
--   link            -> "link" (new; optional, e.g. a PR URL)
--   conversation_id -> "conversation_uuid" (existing)
--   created_at      -> "created_at" (existing)
--   delivered_at    -> reuses "is_viewed" / mark_viewed, NOT delivered_at.
--                      delivered_at already means "emailed/called/texted via
--                      report_type" (UpdateDeliveryService); conflating that
--                      with "Nova mentioned this in a conversation turn"
--                      would be a second, different kind of delivery living
--                      in the same column. is_viewed already means exactly
--                      "the user has now been told, one way or another" (see
--                      UpdateService.mark_delivered's own docstring), so the
--                      turn-injection path reuses it: undelivered == unviewed,
--                      and marking delivered == mark_update_viewed.
--
-- Run against the Supabase Postgres database:
--   uv run python scripts/run_migrations.py 010
-- or:
--   psql "$SUPABASE_DB_URL" -f scripts/migrations/010_update_notification_fields.sql

begin;

alter table "update"
    add column if not exists kind   text,
    add column if not exists status text,
    add column if not exists link  text;

-- kind/status are null for every update that predates this feature (plain
-- badge-only updates, and anything from a source other than the three below)
-- and stay null for those going forward too -- only rows from these three
-- completion paths get tagged, which is what lets the turn-injection query
-- pick out "notifications" without touching unrelated updates.
alter table "update"
    drop constraint if exists update_kind_check;
alter table "update"
    add constraint update_kind_check
    check (kind is null or kind in ('background_agent', 'coding_task', 'scheduled_task'));

alter table "update"
    drop constraint if exists update_status_check;
alter table "update"
    add constraint update_status_check
    check (status is null or status in ('success', 'failed'));

-- The turn-injection query: unviewed, kind-tagged rows, oldest first. A
-- partial index keeps that a handful-of-rows scan instead of a table scan,
-- same reasoning as update_pending_delivery_idx in 001_update_delivery.sql.
create index if not exists update_pending_notification_idx
    on "update" (created_at)
    where is_viewed = false and kind is not null;

commit;

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new columns until it happens to reload on its own.
notify pgrst, 'reload schema';
