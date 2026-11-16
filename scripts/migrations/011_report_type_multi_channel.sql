-- Multi-channel reporting: report_type can now name several channels at
-- once, plus the new 'speak' channel (proactive Sidekick speech).
--
-- report_type has always been free text, never a Postgres enum, but
-- "update" carries a CHECK constraint pinning it to exactly four bare
-- values. That constraint has to go: a report_type is still read the same
-- way for every existing single-channel row (see
-- src.model.report_type.normalize_report_types), but a row asking for
-- several channels now stores a JSON array in the same text column (e.g.
-- '["chat", "speak"]'), which the old constraint would reject outright.
-- Validation moves to the application layer (normalize_report_types /
-- UpdateService._validate_report_type and its three siblings on
-- Responsibility, ScheduledTask, and CodingSession) -- exactly how
-- scheduled_task.report_type and responsibility.report_type already worked
-- even before this migration, since neither ever had a CHECK at all.
--
-- Existing rows are untouched: a bare 'email'/'sms'/'call'/'chat' value is
-- still valid text, still decodes to a single-item channel list, and the
-- column stays nullable, so there is nothing to backfill and no risk of a
-- NOT NULL violation.
--
-- coding_session gets a new report_type column it never had before --
-- nullable, so every existing row simply reads back as "no report type",
-- same as a row that explicitly omitted one.
--
-- Run with:
--   uv run python scripts/run_migrations.py 011

begin;

alter table "update"
    drop constraint if exists update_report_type_check;

alter table coding_session
    add column if not exists report_type text;

commit;

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new column until it happens to reload on its own.
notify pgrst, 'reload schema';
