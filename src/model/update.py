from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

from src.model.report_type import DeliveryStatus, ReportType


class Update(SQLModel, table=True):
    __tablename__ = "update"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    update_message: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_viewed: bool = Field(default=False)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    conversation_uuid: str | None = Field(default=None, foreign_key="conversation.uuid")

    # How the user asked to hear about this, set when the work was spawned.
    # None means badge-only: it shows up in the updates list and nowhere else.
    report_type: ReportType | None = Field(default=None)
    delivery_status: DeliveryStatus = Field(default=DeliveryStatus.NOT_REQUIRED)
    # Counts dispatch attempts, not rings. Bounds retries on an update the
    # user never picks up so Nova doesn't call forever.
    delivery_attempts: int = Field(default=0)
    delivered_at: datetime | None = Field(default=None)
    delivery_error: str | None = Field(default=None)
    # Twilio's id for the call placed to deliver this update; the status
    # callback uses it to find its way back to this row.
    call_sid: str | None = Field(default=None)

    def to_payload(self) -> dict:
        return self.model_dump(
            exclude={"id"},
            exclude_none=True,
            mode="json",
        )
