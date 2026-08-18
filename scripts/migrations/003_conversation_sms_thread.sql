-- Let a conversation belong to an SMS thread.
--
-- Texts arrive minutes or hours apart, so replying usefully means finding the
-- conversation the last text belonged to. Keeping that on the conversation
-- itself (rather than in a separate thread table) reuses everything that
-- already works — history loading, project attachment, closing, memory
-- distillation — and makes "the SMS thread with this number" just a query.
--
-- Nullable by design: every existing conversation, and every browser or phone
-- conversation from here on, has no SMS number and is unaffected.
--
-- Run with:
--   uv run python scripts/run_migrations.py 003

begin;

alter table conversation
    add column if not exists sms_phone_number text;

-- The inbound webhook looks up the newest open conversation for a number on
-- every single text, so this is the hot path for the whole SMS feature.
create index if not exists conversation_sms_phone_number_idx
    on conversation (sms_phone_number, last_message_timestamp_utc desc)
    where sms_phone_number is not null;

commit;

notify pgrst, 'reload schema';
