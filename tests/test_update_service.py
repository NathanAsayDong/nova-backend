import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from src.model.report_type import DeliveryStatus
from src.model.update import Update
from src.service.update_service import UpdateService


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

    def mark_viewed(self, id):
        update = self.updates.get(int(id))
        if update is None:
            return None
        update.is_viewed = True
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


if __name__ == "__main__":
    unittest.main()
