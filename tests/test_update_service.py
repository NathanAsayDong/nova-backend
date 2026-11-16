import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from src.model.report_type import (
    DeliveryStatus,
    ReportType,
    encode_report_types,
    normalize_report_types,
)
from src.model.update import Update
from src.service.update_service import UpdateService


class NormalizeAndEncodeReportTypesTests(unittest.TestCase):
    """
    The one place that understands both the legacy single-string shape and
    the new list shape — every model (Update, Responsibility, ScheduledTask,
    CodingSession) and service routes through these two functions instead
    of re-deriving the logic.
    """

    def test_none_normalizes_to_an_empty_list(self):
        self.assertEqual(normalize_report_types(None), [])
        self.assertIsNone(encode_report_types(None))

    def test_a_bare_string_normalizes_to_one_item(self):
        self.assertEqual(normalize_report_types("email"), [ReportType.EMAIL])

    def test_a_bare_string_is_case_and_whitespace_insensitive(self):
        self.assertEqual(normalize_report_types("  Speak  "), [ReportType.SPEAK])

    def test_a_json_encoded_list_decodes_back_out(self):
        self.assertEqual(
            normalize_report_types('["chat", "speak"]'),
            [ReportType.CHAT, ReportType.SPEAK],
        )

    def test_a_python_list_normalizes_in_order_without_duplicates(self):
        self.assertEqual(
            normalize_report_types(["sms", "speak", "sms"]),
            [ReportType.SMS, ReportType.SPEAK],
        )

    def test_an_unknown_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_report_types("carrier-pigeon")

    def test_a_list_with_one_invalid_channel_is_rejected(self):
        # Regression guard: every item in a multi-channel list must be
        # validated, not just the list shape itself — ['speak', 'sms'] is
        # valid (see test_a_python_list_normalizes_in_order_without_duplicates)
        # but a typo'd sibling must still fail loudly rather than silently
        # dropping the bad entry.
        with self.assertRaises(ValueError):
            normalize_report_types(["speak", "carrier-pigeon"])

    def test_the_rejection_message_lists_every_supported_type_including_speak(self):
        with self.assertRaises(ValueError) as ctx:
            normalize_report_types("carrier-pigeon")
        message = str(ctx.exception)
        for channel in ("email", "sms", "call", "chat", "speak"):
            self.assertIn(channel, message)

    def test_encode_single_channel_stays_a_bare_string(self):
        self.assertEqual(encode_report_types("email"), "email")
        self.assertEqual(encode_report_types(["call"]), "call")

    def test_encode_multiple_channels_as_a_json_array(self):
        encoded = encode_report_types(["chat", "speak"])
        self.assertEqual(normalize_report_types(encoded), [ReportType.CHAT, ReportType.SPEAK])
        self.assertTrue(encoded.startswith("["))

    def test_round_trip_is_stable(self):
        for value in ("email", ["sms", "speak"], ["call"], None):
            with self.subTest(value=value):
                encoded = encode_report_types(value)
                self.assertEqual(
                    normalize_report_types(encoded), normalize_report_types(value)
                )


class FakeUpdateDao:
    def __init__(self, updates=()):
        self.updates = {u.id: u for u in updates}

    def get(self, id):
        return self.updates.get(int(id))

    def get_all(self):
        return sorted(
            self.updates.values(), key=lambda u: u.created_at, reverse=True
        )

    def get_unviewed(self):
        return sorted(
            (u for u in self.updates.values() if not u.is_viewed),
            key=lambda u: u.created_at,
        )

    def create(self, entity):
        entity.id = max(self.updates, default=0) + 1
        self.updates[entity.id] = entity
        return entity

    def mark_viewed(self, id, *, consumed_by=None):
        update = self.updates.get(int(id))
        if update is None:
            return None
        update.is_viewed = True
        update.consumed_by = consumed_by
        return update

    def unmark_viewed(self, id):
        update = self.updates.get(int(id))
        if update is None or not update.is_viewed:
            return None
        update.is_viewed = False
        update.consumed_by = None
        return update

    def mark_all_viewed(self):
        flipped = [u for u in self.updates.values() if not u.is_viewed]
        for update in flipped:
            update.is_viewed = True
        return flipped


class FakeProjectDao:
    def __init__(self, project_ids=(1,)):
        self.project_ids = set(project_ids)

    def get(self, id):
        if int(id) not in self.project_ids:
            return None
        return SimpleNamespace(
            id=int(id),
            name=f"Project {id}",
            to_payload=lambda: {"name": f"Project {id}"},
        )


class FakeConversationDao:
    def __init__(self, conversations=None):
        self.conversations = conversations or {}

    def get_by_uuid(self, uuid):
        return self.conversations.get(str(uuid))


def make_update(id, message="did a thing", viewed=False, hour=12, **kwargs):
    return Update(
        id=id,
        update_message=message,
        is_viewed=viewed,
        created_at=datetime(2026, 8, 9, hour, tzinfo=timezone.utc),
        **kwargs,
    )


def build_service(updates=(), conversations=None) -> UpdateService:
    service = UpdateService.__new__(UpdateService)
    service.update_dao = FakeUpdateDao(updates)
    service.project_dao = FakeProjectDao()
    service.conversation_dao = FakeConversationDao(conversations)
    return service


class CreateUpdateTests(unittest.TestCase):
    def test_creates_and_returns_dict(self):
        service = build_service()
        result = service.create_update("Deploy finished.", project_id=1)
        self.assertEqual(result["update_message"], "Deploy finished.")
        self.assertFalse(result["is_viewed"])
        self.assertEqual(result["project"], {"id": 1, "name": "Project 1"})

    def test_blank_message_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("   ")

    def test_unknown_project_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("hello", project_id=99)

    def test_unknown_conversation_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("hello", conversation_uuid=str(uuid4()))

    def test_invalid_conversation_uuid_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("hello", conversation_uuid="not-a-uuid")

    def test_links_conversation_uuid(self):
        uuid = uuid4()
        service = build_service(
            conversations={str(uuid): SimpleNamespace(id=42, uuid=uuid)}
        )
        result = service.create_update("hello", conversation_uuid=str(uuid))
        self.assertEqual(result["conversation_uuid"], str(uuid))


class NotificationQueueFieldsTests(unittest.TestCase):
    """
    kind/status/link: the notification-queue tags a finished background
    agent/coding task/scheduled task run stamps onto its Update row (see
    migration 010 and AgentLoop._conversation_turn).
    """

    def test_kind_status_and_link_round_trip(self):
        service = build_service()
        result = service.create_update(
            "PR #42 opened.",
            kind="coding_task",
            status="success",
            link="https://example.com/pr/42",
        )
        self.assertEqual(result["kind"], "coding_task")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["link"], "https://example.com/pr/42")

    def test_defaults_to_no_notification_tags(self):
        service = build_service()
        result = service.create_update("Deploy finished.")
        self.assertIsNone(result["kind"])
        self.assertIsNone(result["status"])
        self.assertIsNone(result["link"])

    def test_unknown_kind_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("hello", kind="carrier_pigeon", status="success")

    def test_unknown_status_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("hello", kind="coding_task", status="pending")

    def test_every_valid_kind_and_status_is_accepted(self):
        for kind in ("background_agent", "coding_task", "scheduled_task"):
            for status in ("success", "failed"):
                with self.subTest(kind=kind, status=status):
                    service = build_service()
                    result = service.create_update("x", kind=kind, status=status)
                    self.assertEqual(result["kind"], kind)
                    self.assertEqual(result["status"], status)


class ReportTypeTests(unittest.TestCase):
    def test_no_report_type_is_badge_only(self):
        service = build_service()
        result = service.create_update("Deploy finished.")

        self.assertIsNone(result["report_type"])
        self.assertEqual(result["delivery_status"], DeliveryStatus.NOT_REQUIRED)
        self.assertNotIn("warning", result)

    def test_deliverable_types_are_queued(self):
        for report_type in ("email", "call", "sms"):
            with self.subTest(report_type=report_type):
                service = build_service()
                result = service.create_update("Deploy finished.", report_type=report_type)

                self.assertEqual(result["report_type"], report_type)
                self.assertEqual(result["delivery_status"], DeliveryStatus.PENDING)
                self.assertNotIn("warning", result)

    def test_known_but_undeliverable_types_are_recorded_not_rejected(self):
        # Losing the update because its channel isn't built yet would be worse
        # than not delivering it, so these are kept and flagged.
        service = build_service()
        result = service.create_update("Deploy finished.", report_type="chat")

        self.assertEqual(result["report_type"], "chat")
        self.assertEqual(result["delivery_status"], DeliveryStatus.NOT_REQUIRED)
        self.assertIn("not deliverable yet", result["warning"])

    def test_unknown_report_type_rejected(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.create_update("hello", report_type="carrier-pigeon")

    def test_blank_report_type_treated_as_unset(self):
        service = build_service()
        result = service.create_update("hello", report_type="  ")
        self.assertIsNone(result["report_type"])

    def test_report_type_is_case_insensitive(self):
        service = build_service()
        result = service.create_update("hello", report_type="Call")
        self.assertEqual(result["report_type"], "call")


class MultiChannelReportTypeTests(unittest.TestCase):
    """
    report_type can now carry several channels at once, including the new
    'speak' channel — see src.model.report_type.normalize_report_types /
    encode_report_types, which this (and every other) create_update caller
    routes through.
    """

    def test_single_string_still_works(self):
        """A bare string is still exactly what it was before multi-channel."""
        service = build_service()
        result = service.create_update("Deploy finished.", report_type="email")

        self.assertEqual(result["report_type"], "email")
        self.assertEqual(result["channels"], ["email"])
        self.assertEqual(result["delivery_status"], DeliveryStatus.PENDING)

    def test_a_list_of_channels_is_stored_and_normalized(self):
        service = build_service()
        result = service.create_update(
            "Deploy finished.", report_type=["chat", "speak"]
        )

        self.assertEqual(result["channels"], ["chat", "speak"])
        # Two or more channels are stored as a JSON array on the raw column.
        self.assertTrue(result["report_type"].startswith("["))
        # 'speak' is deliverable, so the row is still queued even though
        # 'chat' alone would not be.
        self.assertEqual(result["delivery_status"], DeliveryStatus.PENDING)

    def test_speak_is_a_deliverable_channel(self):
        service = build_service()
        result = service.create_update("Deploy finished.", report_type="speak")

        self.assertEqual(result["channels"], ["speak"])
        self.assertEqual(result["delivery_status"], DeliveryStatus.PENDING)
        self.assertNotIn("warning", result)

    def test_a_list_with_one_undeliverable_channel_warns_for_that_channel_only(self):
        service = build_service()
        result = service.create_update(
            "Deploy finished.", report_type=["speak", "chat"]
        )

        self.assertEqual(result["channels"], ["speak", "chat"])
        # speak alone is enough to queue the update for delivery...
        self.assertEqual(result["delivery_status"], DeliveryStatus.PENDING)
        # ...but the warning still calls out the channel with no delivery path.
        self.assertIn("Reporting by chat", result["warning"])

    def test_duplicate_channels_collapse_to_one(self):
        service = build_service()
        result = service.create_update(
            "Deploy finished.", report_type=["email", "email"]
        )
        self.assertEqual(result["channels"], ["email"])
        self.assertEqual(result["report_type"], "email")

    def test_an_update_read_back_decodes_json_encoded_channels(self):
        """
        A row written with several channels round-trips through
        get_unviewed_updates exactly as it was stored — this is what the
        sidekick poller and the next-turn injection both read.
        """
        service = build_service()
        created = service.create_update(
            "Deploy finished.", report_type=["sms", "speak"], kind="coding_task",
            status="success",
        )
        [unviewed] = service.get_unviewed_updates()
        self.assertEqual(unviewed["id"], created["id"])
        self.assertEqual(sorted(unviewed["channels"]), ["sms", "speak"])


class ViewingTests(unittest.TestCase):
    def test_unviewed_only_and_oldest_first(self):
        service = build_service(
            updates=(
                make_update(1, "newest unviewed", hour=15),
                make_update(2, "already seen", viewed=True, hour=10),
                make_update(3, "oldest unviewed", hour=9),
            )
        )
        messages = [u["update_message"] for u in service.get_unviewed_updates()]
        self.assertEqual(messages, ["oldest unviewed", "newest unviewed"])
        self.assertEqual(service.get_unviewed_count(), 2)

    def test_mark_all_viewed_reports_count_and_clears(self):
        service = build_service(
            updates=(make_update(1), make_update(2), make_update(3, viewed=True))
        )
        result = service.mark_all_updates_viewed()
        self.assertEqual(result, {"status": "viewed", "count": 2})
        self.assertEqual(service.get_unviewed_updates(), [])

    def test_mark_one_viewed(self):
        service = build_service(updates=(make_update(1),))
        result = service.mark_update_viewed(1)
        self.assertTrue(result["is_viewed"])

    def test_mark_missing_update_raises(self):
        service = build_service()
        with self.assertRaises(ValueError):
            service.mark_update_viewed(7)

    def test_mark_one_viewed_records_who_consumed_it(self):
        service = build_service(updates=(make_update(1),))
        result = service.mark_update_viewed(1, consumed_by="chat_prompt:abc-123")
        self.assertTrue(result["is_viewed"])
        self.assertEqual(service.update_dao.updates[1].consumed_by, "chat_prompt:abc-123")

    def test_unmark_restores_an_update_to_unviewed(self):
        """
        Regression coverage for the sidekick-pass bug: a notification can be
        marked viewed the moment it's folded into a turn's prompt, then need
        undoing because that turn never actually said or persisted anything
        -- see AgentLoop._conversation_turn's is_sidekick_pass branch.
        """
        service = build_service(updates=(make_update(1),))
        service.mark_update_viewed(1, consumed_by="sidekick_prompt:abc-123")

        result = service.unmark_update_viewed(1)

        self.assertIsNotNone(result)
        self.assertFalse(result["is_viewed"])
        self.assertEqual(service.update_dao.updates[1].consumed_by, None)
        self.assertEqual(service.get_unviewed_count(), 1)

    def test_unmark_an_already_unviewed_update_is_a_quiet_no_op(self):
        # Someone else may have legitimately settled it in between (the
        # delivery dispatcher, the notify loop, another turn) -- that
        # outcome must win, not get clobbered.
        service = build_service(updates=(make_update(1),))
        self.assertIsNone(service.unmark_update_viewed(1))


if __name__ == "__main__":
    unittest.main()
