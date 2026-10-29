from datetime import datetime, timedelta, timezone
from uuid import UUID
from src.dao.base_dao import BaseDao
from src.model.conversation import Conversation

class ConversationDao(BaseDao):
    _table = "conversation"
    _model_class = Conversation

    def get_by_uuid(self, uuid: UUID) -> Conversation | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("uuid", str(uuid))
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def _update_columns(self, uuid: UUID, columns: dict) -> Conversation | None:
        response = (
            self.client.table(self._table)
            .update(columns)
            .eq("uuid", str(uuid))
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def set_project(self, uuid: UUID, project_id: int) -> Conversation | None:
        return self._update_columns(uuid, {"project_id": project_id})

    def get_by_project(self, project_id: int) -> list[Conversation]:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def set_closed(self, uuid: UUID) -> Conversation | None:
        return self._update_columns(uuid, {"is_closed": True})

    def get_latest_open_for_sms(self, phone_number: str) -> Conversation | None:
        """
        The open SMS conversation for a number, newest first, or None.

        Ordering by last message rather than creation date is what makes a
        reply land in the thread the user was actually just in.
        """
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("sms_phone_number", phone_number)
            .eq("is_closed", False)
            .order("last_message_timestamp_utc", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def set_processed(self, uuid: UUID) -> Conversation | None:
        return self._update_columns(uuid, {"is_processed": True})

    def get_unprocessed_closed(self) -> list[Conversation]:
        """Closed conversations whose messages have not been distilled into memory yet."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("is_closed", True)
            .eq("is_processed", False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    @staticmethod
    def _is_idle(
        conversation: Conversation,
        now: datetime,
        idle_hours: float,
        sms_idle_hours: float,
    ) -> bool:
        """
        Whether a conversation has sat quiet long enough to auto-close.

        SMS threads get sms_idle_hours instead of idle_hours — sms_controller
        uses the same window to decide whether an incoming text resumes the
        existing thread, so closing it any sooner here would break that
        continuity. A conversation with no last_message_timestamp_utc (never
        actually messaged) is left alone rather than guessed at; the model
        has no created-time column to fall back on.
        """
        if conversation.is_closed:
            return False
        last = conversation.last_message_timestamp_utc
        # The dao hands back raw rows via model_class(**row) without Pydantic
        # validation (SQLModel table models skip that on init), so a str
        # ISO8601 value from Supabase (with 'Z' or '+00:00', or naive) comes
        # through as-is here instead of a datetime. Coerce it before use.
        if isinstance(last, str):
            try:
                last = datetime.fromisoformat(last.replace("Z", "+00:00"))
            except ValueError:
                last = None
        if last is None:
            print(
                f"check_for_stale_conversations: skipping {conversation.uuid}, "
                "no last_message_timestamp_utc to judge idleness from."
            )
            return False
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        threshold_hours = sms_idle_hours if conversation.sms_phone_number else idle_hours
        return now - last > timedelta(hours=threshold_hours)

    @staticmethod
    def _is_past_rollover(conversation: Conversation, rollover_cutoff_utc: datetime) -> bool:
        """
        Whether a conversation's last activity predates the daily rollover.

        Nate wants no conversation — voice, app, glasses, SMS, calls, all of
        them — to carry over from one local day to the next. rollover_cutoff_utc
        is the most recent local midnight (in NOVA_CONVERSATION_ROLLOVER_TZ)
        expressed in UTC; a conversation last touched before it belongs to a
        prior day and gets closed regardless of how recently that was (even a
        conversation active 2 minutes before midnight closes). Same null/
        already-closed handling as _is_idle.
        """
        if conversation.is_closed:
            return False
        last = conversation.last_message_timestamp_utc
        # Same str-coercion need as _is_idle: last_message_timestamp_utc
        # comes back unvalidated from the dao and may still be an ISO8601
        # string (naive or with 'Z'/'+00:00') rather than a datetime.
        if isinstance(last, str):
            try:
                last = datetime.fromisoformat(last.replace("Z", "+00:00"))
            except ValueError:
                last = None
        if last is None:
            print(
                f"check_for_stale_conversations: skipping {conversation.uuid}, "
                "no last_message_timestamp_utc to judge rollover from."
            )
            return False
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return last < rollover_cutoff_utc

    def check_for_stale_conversations(
        self,
        idle_hours: float,
        sms_idle_hours: float,
        rollover_cutoff_utc: datetime,
    ) -> None:
        """
        Close conversations that have gone idle past their threshold, or that
        are left over from a prior local day (rollover_cutoff_utc).

        Fetches every open conversation once and judges both conditions in
        Python with a timezone-aware UTC "now" (the prior version compared
        against a naive datetime.now(), which is a bug risk against
        timestamps stored in UTC) rather than issuing a .lt() query — a
        single query can't apply two different idle thresholds (SMS vs.
        non-SMS) plus the rollover cutoff at once, and this also keeps the
        decision in easily-testable places (_is_idle, _is_past_rollover).
        Recomputing rollover_cutoff_utc fresh from the current time on every
        call (see ConversationService.check_for_stale_conversations) is what
        makes this restart-safe: if the worker was down over a midnight, the
        next run's cutoff is still "the most recent local midnight before
        right now", so a conversation from two days ago still closes — there
        is no missed-event state to recover.
        """
        now = datetime.now(timezone.utc)
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("is_closed", False)
            .execute()
        )
        for row in response.data:
            try:
                conversation = self._to_model(self._model_class, row)
                if self._is_idle(
                    conversation, now, idle_hours, sms_idle_hours
                ) or self._is_past_rollover(conversation, rollover_cutoff_utc):
                    self._update_columns(conversation.uuid, {"is_closed": True})
            except Exception as e:
                print(
                    f"check_for_stale_conversations: error processing conversation "
                    f"{row.get('uuid', '<unknown>')}: {e}"
                )
                continue

    def touch_last_message(self, uuid: UUID, timestamp_utc: str) -> Conversation | None:
        return self._update_columns(uuid, {"last_message_timestamp_utc": timestamp_utc})

    def create_conversation(self, conversation: Conversation) -> Conversation:
        response = (
            self.client.table(self._table)
            .insert(conversation.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def update_conversation(self, uuid: UUID, conversation: Conversation) -> Conversation | None:
        response = (
            self.client.table(self._table)
            .update(conversation.to_payload())
            .eq("uuid", uuid)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])