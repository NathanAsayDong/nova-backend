from src.dao.base_dao import BaseDao
from src.model.scheduled_task import ScheduledTask, TaskStatus


class ScheduledTaskDao(BaseDao):
    """
    DAO for ScheduledTask model.
    """
    _table = "scheduled_task"
    _model_class = ScheduledTask

    def get(self, id: int) -> ScheduledTask | None:
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

    def list_by_status(self, status: str | None = None) -> list[ScheduledTask]:
        query = self.client.table(self._table).select("*")
        if status is not None:
            query = query.eq("status", status)
        response = query.order("run_at").execute()
        return [self._to_model(self._model_class, row) for row in response.data]

    def get_due(self, now_utc: str) -> list[ScheduledTask]:
        """Pending tasks whose run_at has arrived, oldest first."""
        response = (
            self.client.table(self._table)
            .select("*")
            .eq("status", TaskStatus.PENDING.value)
            .lte("run_at", now_utc)
            .order("run_at")
            .execute()
        )
        return [self._to_model(self._model_class, row) for row in response.data]

    def create(self, entity: ScheduledTask) -> ScheduledTask:
        response = (
            self.client.table(self._table)
            .insert(entity.to_payload())
            .execute()
        )
        return self._to_model(self._model_class, response.data[0])

    def claim(self, id: int, started_at_utc: str) -> ScheduledTask | None:
        """
        Move a task pending -> running, or return None if it wasn't pending.

        One guarded UPDATE, so if two passes ever race for the same task only
        one gets a row back and the other must leave it alone.
        """
        response = (
            self.client.table(self._table)
            .update({"status": TaskStatus.RUNNING.value, "started_at": started_at_utc})
            .eq("id", id)
            .eq("status", TaskStatus.PENDING.value)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def finish(
        self, id: int, status: TaskStatus, completed_at_utc: str, result: str | None
    ) -> ScheduledTask | None:
        response = (
            self.client.table(self._table)
            .update(
                {
                    "status": status.value,
                    "completed_at": completed_at_utc,
                    "result": result,
                }
            )
            .eq("id", id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])

    def cancel(self, id: int) -> ScheduledTask | None:
        """Cancel a task only if it is still pending; None means it wasn't."""
        response = (
            self.client.table(self._table)
            .update({"status": TaskStatus.CANCELLED.value})
            .eq("id", id)
            .eq("status", TaskStatus.PENDING.value)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(self._model_class, response.data[0])
