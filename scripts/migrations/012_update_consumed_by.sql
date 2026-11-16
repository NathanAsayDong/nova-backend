-- Audit trail for "who actually consumed this notification."
--
-- Investigating why Nate never heard coding-task completions 381-386 (all
-- is_viewed=true, none ever spoken) showed is_viewed alone can't answer "who
-- saw this and when": AgentLoop._conversation_turn marks a scope-less
-- notification viewed the instant it is folded into ANY turn's prompt
-- (agent_loop.py's _select_notifications/_build_notifications_block call
-- site), including a Sidekick ambient interjection that then silently
-- passes ("[[pass]]") and throws the whole turn away unspoken and
-- unpersisted -- see is_sidekick_pass in src/harness/agent_loop.py. The row
-- was flipped before anyone establishes the turn actually said anything.
--
-- The paired code change (not in this migration) stops marking a
-- notification viewed on a sidekick pass -- see UpdateDao.unmark_viewed /
-- UpdateService.unmark_update_viewed and its call from
-- AgentLoop._conversation_turn right where is_sidekick_pass fires. This
-- column is the other half the investigation asked for: even when a mark IS
-- legitimate, nothing recorded which turn/channel did it, so a future "did
-- Nate actually hear this" question meant re-deriving the whole trace by
-- hand (as this investigation had to). consumed_by is a short free-text tag
-- -- "chat_prompt:<conversation_uuid>", "sidekick_prompt:<conversation_uuid>",
-- "sidekick_notify_loop", "delivery:email", "delivery:sms", "delivery:speak"
-- -- set alongside is_viewed wherever it flips true, and cleared back to
-- null by unmark_viewed. Nullable and never backfilled: every row that was
-- marked viewed before this migration simply has no recorded consumer,
-- which is the honest answer for data this migration cannot retroactively
-- reconstruct.
--
-- Run with:
--   uv run python scripts/run_migrations.py 012

begin;

alter table "update"
    add column if not exists consumed_by text;

commit;

-- PostgREST answers the DAOs from a cached schema; without this it can keep
-- rejecting the new column until it happens to reload on its own.
notify pgrst, 'reload schema';
