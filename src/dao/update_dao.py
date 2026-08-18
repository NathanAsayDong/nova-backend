from datetime import datetime, timezone

from src.dao.base_dao import BaseDao
from src.model.report_type import DeliveryStatus
from src.model.update import Update


class UpdateDao(BaseDao):
    _table = "update"
    _model_class = Update

    def get(self, id: int) -> Update | None:
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(self._model_class, response.data)

    def get_all(self) -> list[Update]:
        response = (
            self.client.table(self._table)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def get_unviewed(self) -> list[Update]:
        """Unviewed updates, oldest first so they read chronologically."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("is_viewed", False)
            .order("created_at", desc=False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def create(self, entity: Update) -> Update:
        response = (
            self.client.table(self._table)
            .insert(entity.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def mark_viewed(self, id: int) -> Update | None:
        response = (
            self.client.table(self._table)
            .update({"is_viewed": True})
            .eq("id", id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def mark_all_viewed(self) -> list[Update]:
        """Mark every unviewed update as viewed; returns the rows that flipped."""
        response = (
            self.client.table(self._table)
            .update({"is_viewed": True})
            .eq("is_viewed", False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data or []]

    def delete(self, id: int) -> None:
        self.client.table(self._table).delete().eq("id", id).execute()

    # ---------- delivery ----------

    def get_pending_deliveries(self) -> list[Update]:
        """
        Updates waiting to be delivered, oldest first.

        Only rows the spawning agent explicitly flagged for delivery reach
        PENDING; a plain badge-only update sits at NOT_REQUIRED and is never
        returned here.
        """
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("delivery_status", DeliveryStatus.PENDING.value)
            .order("created_at", desc=False)
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data or []]

    def get_by_call_sid(self, call_sid: str) -> Update | None:
        """Find the update a given Twilio call was placed to deliver."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("call_sid", call_sid)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def claim_for_delivery(self, id: int) -> Update | None:
        """
        Take ownership of one pending update, or return None if it's already taken.

        The status equality in the WHERE clause is what makes this a
        compare-and-swap: two dispatchers racing on the same row both issue
        the update, but only the one that gets there while the row is still
        PENDING gets a row back. Delivering an update means placing a phone
        call, so double-claiming is not a cosmetic bug.
        """
        response = (
            self.client.table(self._table)
            .update({"delivery_status": DeliveryStatus.IN_PROGRESS.value})
            .eq("id", id)
            .eq("delivery_status", DeliveryStatus.PENDING.value)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def set_delivery_state(
        self,
        id: int,
        status: DeliveryStatus,
        *,
        call_sid: str | None = None,
        error: str | None = None,
        attempts: int | None = None,
        mark_viewed: bool = False,
    ) -> Update | None:
        """
        Move an update to a delivery state, stamping whatever came with it.

        delivered_at is set only on DELIVERED so it always means "the user
        actually got this", never "we last touched the row".
        """
        payload: dict = {"delivery_status": status.value}
        if call_sid is not None:
            payload["call_sid"] = call_sid
        if attempts is not None:
            payload["delivery_attempts"] = attempts
        # Cleared on success so a row that failed and later succeeded doesn't
        # keep explaining a failure that no longer happened.
        payload["delivery_error"] = error
        if status == DeliveryStatus.DELIVERED:
            payload["delivered_at"] = datetime.now(timezone.utc).isoformat()
        if mark_viewed:
            payload["is_viewed"] = True

        response = (
            self.client.table(self._table)
            .update(payload)
            .eq("id", id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])
