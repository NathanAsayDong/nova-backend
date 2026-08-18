-- Delivery state for updates.
--
-- Adds the columns that let an update be *delivered* (emailed, called out)
-- rather than only sitting in the badge. Existing rows predate the feature and
-- were never meant to be delivered, so they default to not_required — the
-- dispatcher's query filters on delivery_status = 'pending' and will not pick
-- up a single one of them.
--
-- Run against the Supabase Postgres database:
--   psql "$SUPABASE_DB_URL" -f scripts/migrations/001_update_delivery.sql
-- or paste into the Supabase SQL editor.

begin;

alter table "update"
    add column if not exists report_type       text,
    add column if not exists delivery_status   text    not null default 'not_required',
    add column if not exists delivery_attempts integer not null default 0,
    add column if not exists delivered_at      timestamptz,
    add column if not exists delivery_error    text,
    add column if not exists call_sid          text;

-- Values are written from the ReportType / DeliveryStatus StrEnums in
-- src/model/report_type.py. Constrained here as well so a bad write fails at
-- the database rather than surfacing as an unroutable update later.
alter table "update"
    drop constraint if exists update_report_type_check;
alter table "update"
    add constraint update_report_type_check
    check (report_type is null or report_type in ('email', 'sms', 'call', 'chat'));

alter table "update"
    drop constraint if exists update_delivery_status_check;
alter table "update"
    add constraint update_delivery_status_check
    check (delivery_status in ('not_required', 'pending', 'in_progress', 'delivered', 'failed'));

-- The dispatcher polls for due work every minute; this keeps that a partial
-- index scan over a handful of rows instead of a scan of every update ever.
create index if not exists update_pending_delivery_idx
    on "update" (created_at)
    where delivery_status = 'pending';

-- The Twilio status callback arrives with only a CallSid to identify the row.
create index if not exists update_call_sid_idx
    on "update" (call_sid)
    where call_sid is not null;

commit;

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new columns until it happens to reload on its own.
notify pgrst, 'reload schema';
