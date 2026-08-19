import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from src.model.meeting import Meeting, MeetingNotes, MeetingSegment, MeetingStatus
from src.service.meeting_service import MeetingError, MeetingService


class FakeMeetingDao:
    def __init__(self, meetings=()):
        self.meetings = {m.id: m for m in meetings}
        self.segments: list[MeetingSegment] = []
        self.titles: dict[int, str] = {}
        self.audio_paths: dict[int, str | None] = {}

    def get(self, id):
        return self.meetings.get(int(id))

    def get_by_uuid(self, uuid):
        return next(
            (m for m in self.meetings.values() if str(m.uuid) == str(uuid)), None
        )

    def get_active(self):
        return next(
            (m for m in self.meetings.values() if m.status == MeetingStatus.RECORDING),
            None,
        )

    def get_all(self, project_id=None, limit=20, since=None):
        rows = list(self.meetings.values())
        if project_id is not None:
            rows = [m for m in rows if m.project_id == project_id]
        if since is not None:
            rows = [m for m in rows if m.started_at >= since]
        return sorted(rows, key=lambda m: m.started_at, reverse=True)[:limit]

    def create(self, entity):
        entity.id = max(self.meetings, default=0) + 1
        self.meetings[entity.id] = entity
        return entity

    def set_status(self, id, status, ended_at=None):
        meeting = self.meetings.get(int(id))
        if meeting is None:
            return None
        meeting.status = status
        if ended_at is not None:
            meeting.ended_at = ended_at
        return meeting

    def set_title(self, id, title):
        self.titles[int(id)] = title

    def set_audio_path(self, id, audio_path):
        self.audio_paths[int(id)] = audio_path

    def update(self, id, changes):
        meeting = self.meetings.get(int(id))
        if meeting is None:
            return None
        for key, value in changes.items():
            setattr(meeting, key, value)
        return meeting

    def delete(self, id):
        self.meetings.pop(int(id), None)

    def close_stale_recordings(self):
        stale = [m for m in self.meetings.values() if m.status == MeetingStatus.RECORDING]
        for meeting in stale:
            meeting.status = MeetingStatus.FAILED
        return stale

    def insert_segments(self, segments):
        self.segments.extend(segments)

    def get_segments(self, meeting_id, start_ms=None, end_ms=None):
        rows = [s for s in self.segments if s.meeting_id == int(meeting_id)]
        if start_ms is not None:
            rows = [s for s in rows if s.end_ms >= start_ms]
        if end_ms is not None:
            rows = [s for s in rows if s.start_ms <= end_ms]
        return sorted(rows, key=lambda s: s.start_ms)

    def get_last_segment_end_ms(self, meeting_id):
        rows = self.get_segments(meeting_id)
        return rows[-1].end_ms if rows else 0


class FakeChunkDao:
    def __init__(self):
        self.chunks = []
        self.searches = []
        self.deleted_for = []
        self.results = []

    def insert_chunks(self, chunks):
        self.chunks.extend(chunks)

    def delete_for_meeting(self, meeting_id):
        self.deleted_for.append(int(meeting_id))

    def search(self, embedding, project_id=None, meeting_id=None, since=None, limit=5):
        self.searches.append(
            {"project_id": project_id, "meeting_id": meeting_id, "since": since, "limit": limit}
        )
        return self.results


class FakeNotesDao:
    def __init__(self):
        self.rows = []

    def create(self, entity):
        entity.id = len(self.rows) + 1
        self.rows.append(entity)
        return entity

    def get_latest(self, meeting_id):
        rows = [n for n in self.rows if n.meeting_id == int(meeting_id)]
        return rows[-1] if rows else None


class FakeProjectDao:
    def __init__(self, ids=(1,)):
        self.ids = set(ids)

    def get(self, id):
        if int(id) not in self.ids:
            return None
        return SimpleNamespace(id=int(id), name=f"Project {id}", description="desc")


class FakeConversationDao:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    def get_by_uuid(self, uuid):
        project_id = self.mapping.get(str(uuid))
        if project_id is None:
            return None
        return SimpleNamespace(uuid=uuid, project_id=project_id)


class FakeEmbeddingService:
    def embed_text(self, text):
        return [0.1] * 1536

    def embed_texts(self, texts):
        return [[0.1] * 1536 for _ in texts]


class FakeUpdateService:
    def __init__(self):
        self.created = []

    def create_update(self, update_message, project_id=None, conversation_uuid=None, report_type=None):
        record = {
            "update_message": update_message,
            "project_id": project_id,
            "report_type": report_type,
        }
        self.created.append(record)
        return record


class ReplyQueue:
    """
    Canned model replies, drawn in order by whichever fake asks next.

    Shared between the two fakes on purpose: notes come from a plain
    completion and the follow-up from the agent loop, and a finalize run
    consumes one of each, in that order.
    """

    def __init__(self, replies):
        self.replies = list(replies)

    def take(self):
        return self.replies.pop(0) if self.replies else ""


class FakeClaudeService:
    """Plain completion. Notes generation deliberately gets no tools."""

    def __init__(self, queue):
        self.queue = queue
        self.prompts = []

    def get_response(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return SimpleNamespace(content=[SimpleNamespace(text=self.queue.take())])


class FakeAgentLoop:
    """Stands in for the ReAct loop, used only by the follow-up assessment."""

    def __init__(self, queue):
        self.queue = queue
        self.calls = []

    def _run_agent_loop(self, prompt, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self.queue.take()


def build_service(meetings=(), replies=(), conversations=None):
    service = MeetingService.__new__(MeetingService)
    service.meeting_dao = FakeMeetingDao(meetings)
    service.chunk_dao = FakeChunkDao()
    service.notes_dao = FakeNotesDao()
    service.project_dao = FakeProjectDao()
    service.conversation_dao = FakeConversationDao(conversations)
    service.embedding_service = FakeEmbeddingService()
    service.update_service = FakeUpdateService()
    queue = ReplyQueue(replies)
    service._claude_service = FakeClaudeService(queue)
    service._agent = FakeAgentLoop(queue)
    service.finalize_threads = []
    return service


def recording_meeting(**kwargs):
    defaults = dict(
        id=1,
        uuid=uuid4(),
        title="Standup",
        status=MeetingStatus.RECORDING,
        started_at=datetime.now(timezone.utc),
        project_id=1,
    )
    defaults.update(kwargs)
    return Meeting(**defaults)


class StartMeetingTests(unittest.TestCase):
    def test_starts_and_reports_recording(self):
        service = build_service()
        result = service.start_meeting(title="Kickoff")
        self.assertEqual(result["status"], "recording")
        self.assertEqual(result["meeting"]["title"], "Kickoff")
        self.assertIsNotNone(service.meeting_dao.get_active())

    def test_refuses_a_second_concurrent_meeting(self):
        service = build_service(meetings=[recording_meeting()])
        with self.assertRaises(MeetingError) as ctx:
            service.start_meeting()
        self.assertIn("already recording", str(ctx.exception))

    def test_inherits_project_from_the_calling_conversation(self):
        conversation_uuid = str(uuid4())
        service = build_service(conversations={conversation_uuid: 1})
        result = service.start_meeting(conversation_uuid=conversation_uuid)
        self.assertEqual(result["meeting"]["project"]["id"], 1)

    def test_explicit_project_beats_the_conversation(self):
        conversation_uuid = str(uuid4())
        service = build_service(conversations={conversation_uuid: 1})
        service.project_dao = FakeProjectDao(ids=(1, 2))
        result = service.start_meeting(project_id=2, conversation_uuid=conversation_uuid)
        self.assertEqual(result["meeting"]["project"]["id"], 2)

    def test_reports_the_clash_when_the_row_came_back_as_json(self):
        # SQLModel skips validation on table=True models, so a meeting read
        # back through PostgREST has a string started_at, not a datetime.
        # Formatting that as a time used to raise and surface as a 500.
        meeting = recording_meeting()
        meeting.started_at = "2026-08-18T22:45:04.528748+00:00"
        service = build_service(meetings=[meeting])
        with self.assertRaises(MeetingError) as ctx:
            service.start_meeting()
        self.assertIn("22:45", str(ctx.exception))

    def test_rejects_an_unknown_project(self):
        service = build_service()
        with self.assertRaises(MeetingError):
            service.start_meeting(project_id=999)


class StopMeetingTests(unittest.TestCase):
    def test_stopping_moves_to_processing_without_blocking(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting])
        # Run the finalize inline instead of on a thread so the test is
        # deterministic; the threading itself is not what is under test.
        service._finalize = lambda *args, **kwargs: None
        result = service.stop_meeting()
        self.assertEqual(result["status"], "processing")
        self.assertEqual(meeting.status, MeetingStatus.PROCESSING)
        self.assertIsNotNone(meeting.ended_at)

    def test_stopping_with_no_meeting_is_an_error(self):
        service = build_service()
        with self.assertRaises(MeetingError):
            service.stop_meeting()

    def test_stopping_an_already_stopped_meeting_is_an_error(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        with self.assertRaises(MeetingError):
            service.stop_meeting(str(meeting.uuid))


class CommitSegmentsTests(unittest.TestCase):
    def test_offsets_window_times_onto_the_meeting_clock(self):
        service = build_service(meetings=[recording_meeting()])
        window = [
            SimpleNamespace(start=0.0, end=2.0, text="first"),
            SimpleNamespace(start=2.5, end=4.0, text="second"),
        ]
        committed = service.commit_segments(1, window, offset_seconds=30.0)
        self.assertEqual([c["startMs"] for c in committed], [30000, 32500])
        self.assertEqual([c["endMs"] for c in committed], [32000, 34000])

    def test_drops_empty_text(self):
        service = build_service(meetings=[recording_meeting()])
        window = [
            SimpleNamespace(start=0.0, end=1.0, text="   "),
            SimpleNamespace(start=1.0, end=2.0, text="kept"),
        ]
        committed = service.commit_segments(1, window)
        self.assertEqual([c["text"] for c in committed], ["kept"])


class ChunkingTests(unittest.TestCase):
    def test_rolls_segments_into_passages_of_about_the_window(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting])
        # 20 segments of 10s each = 200s; at 75s per passage that is 3.
        service.meeting_dao.segments = [
            MeetingSegment(
                meeting_id=1, start_ms=i * 10_000, end_ms=(i + 1) * 10_000, text=f"line {i}"
            )
            for i in range(20)
        ]
        count = service._chunk_and_embed(meeting)
        self.assertEqual(count, 3)
        self.assertEqual(len(service.chunk_dao.chunks), 3)
        self.assertEqual(service.chunk_dao.deleted_for, [1])

    def test_re_chunking_clears_the_previous_pass_first(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=1000, text="only")
        ]
        service._chunk_and_embed(meeting)
        service._chunk_and_embed(meeting)
        self.assertEqual(service.chunk_dao.deleted_for, [1, 1])

    def test_no_segments_means_no_chunks(self):
        service = build_service(meetings=[recording_meeting()])
        self.assertEqual(service._chunk_and_embed(recording_meeting()), 0)


class NotesTests(unittest.TestCase):
    def test_parses_the_models_json_into_a_notes_row(self):
        meeting = recording_meeting(title=None)
        reply = json.dumps(
            {
                "title": "Sensor rollout",
                "summary_md": "We agreed the reporting interval.",
                "decisions": ["Report every fifteen minutes."],
                "action_items": [{"task": "Send the quote", "owner": "Kaden", "due": "Friday"}],
            }
        )
        service = build_service(meetings=[meeting], replies=[reply])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=5000, text="some talking")
        ]
        notes = service._write_notes(meeting)
        self.assertEqual(notes.summary_md, "We agreed the reporting interval.")
        self.assertEqual(notes.decisions, ["Report every fifteen minutes."])
        self.assertEqual(notes.action_items[0]["owner"], "Kaden")
        # An untitled meeting takes the title the write-up came up with.
        self.assertEqual(service.meeting_dao.titles[1], "Sensor rollout")

    def test_keeps_the_reply_as_the_summary_when_json_is_missing(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting], replies=["Just prose, no JSON."])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=5000, text="talking")
        ]
        notes = service._write_notes(meeting)
        self.assertEqual(notes.summary_md, "Just prose, no JSON.")

    def test_no_transcript_means_no_notes(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting], replies=["{}"])
        self.assertIsNone(service._write_notes(meeting))

    def test_does_not_overwrite_a_title_the_user_gave(self):
        meeting = recording_meeting(title="Nathan's title")
        reply = json.dumps({"title": "Model's title", "summary_md": "x"})
        service = build_service(meetings=[meeting], replies=[reply])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=1000, text="talking")
        ]
        service._write_notes(meeting)
        self.assertNotIn(1, service.meeting_dao.titles)


class FollowUpTests(unittest.TestCase):
    def _notes(self, **kwargs):
        defaults = dict(
            meeting_id=1,
            summary_md="Summary",
            decisions=["Something was decided"],
            action_items=[{"task": "Do the thing", "owner": "Nathan", "due": "tomorrow"}],
        )
        defaults.update(kwargs)
        return MeetingNotes(**defaults)

    def test_does_nothing_when_the_agent_says_no(self):
        meeting = recording_meeting()
        reply = json.dumps({"notify": False, "reason": "nothing time-sensitive"})
        service = build_service(meetings=[meeting], replies=[reply])
        self.assertIsNone(service._run_followup(meeting, self._notes()))
        self.assertEqual(service.update_service.created, [])

    def test_queues_an_update_when_the_agent_says_yes(self):
        meeting = recording_meeting()
        reply = json.dumps(
            {
                "notify": True,
                "report_type": "email",
                "message": "You owe the city a quote by Friday.",
                "reason": "deadline inside a week",
            }
        )
        service = build_service(meetings=[meeting], replies=[reply])
        service._run_followup(meeting, self._notes())
        self.assertEqual(len(service.update_service.created), 1)
        created = service.update_service.created[0]
        self.assertEqual(created["report_type"], "email")
        self.assertEqual(created["project_id"], 1)
        self.assertIn("Friday", created["update_message"])

    def test_skips_entirely_when_there_is_nothing_actionable(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting], replies=["never reached"])
        result = service._run_followup(
            meeting, self._notes(decisions=[], action_items=[])
        )
        self.assertIsNone(result)
        self.assertEqual(service._agent.calls, [])

    def test_notify_without_a_message_is_not_delivered(self):
        meeting = recording_meeting()
        reply = json.dumps({"notify": True, "report_type": "email", "message": ""})
        service = build_service(meetings=[meeting], replies=[reply])
        service._run_followup(meeting, self._notes())
        self.assertEqual(service.update_service.created, [])

    def test_undeliverable_report_type_falls_back_to_a_badge(self):
        meeting = recording_meeting()
        # 'chat' is a known type with no channel behind it; queuing it as-is
        # would silently never reach anyone.
        reply = json.dumps({"notify": True, "report_type": "chat", "message": "Heads up"})
        service = build_service(meetings=[meeting], replies=[reply])
        service._run_followup(meeting, self._notes())
        self.assertEqual(service.update_service.created[0]["report_type"], None)

    def test_an_agent_failure_does_not_take_the_meeting_down(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting])

        def explode(prompt, system=None):
            raise RuntimeError("model unavailable")

        service._agent = SimpleNamespace(_run_agent_loop=explode)
        self.assertIsNone(service._run_followup(meeting, self._notes()))


class FinalizeTests(unittest.TestCase):
    def test_completes_the_meeting_end_to_end(self):
        meeting = recording_meeting(status=MeetingStatus.PROCESSING)
        notes_reply = json.dumps({"summary_md": "It happened.", "action_items": []})
        followup_reply = json.dumps({"notify": False, "reason": "routine"})
        service = build_service(meetings=[meeting], replies=[notes_reply, followup_reply])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=9000, text="talking")
        ]
        service._cleanup_audio = lambda meeting_id: None

        service._finalize(1, generate_notes=True)

        self.assertEqual(meeting.status, MeetingStatus.COMPLETE)
        self.assertEqual(len(service.chunk_dao.chunks), 1)
        self.assertEqual(service.notes_dao.get_latest(1).summary_md, "It happened.")

    def test_a_failure_marks_the_meeting_failed_rather_than_leaving_it_stuck(self):
        meeting = recording_meeting(status=MeetingStatus.PROCESSING)
        service = build_service(meetings=[meeting])

        def explode(_meeting):
            raise RuntimeError("embedding backend down")

        service._chunk_and_embed = explode
        service._finalize(1, generate_notes=True)
        self.assertEqual(meeting.status, MeetingStatus.FAILED)

    def test_skips_notes_when_asked_to(self):
        meeting = recording_meeting(status=MeetingStatus.PROCESSING)
        service = build_service(meetings=[meeting])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=1000, text="talking")
        ]
        service._cleanup_audio = lambda meeting_id: None
        service._finalize(1, generate_notes=False)
        self.assertEqual(meeting.status, MeetingStatus.COMPLETE)
        self.assertIsNone(service.notes_dao.get_latest(1))


class RetrievalTests(unittest.TestCase):
    def test_state_reports_the_mode(self):
        self.assertEqual(build_service().get_state()["mode"], "agent")
        self.assertEqual(
            build_service(meetings=[recording_meeting()]).get_state()["mode"], "meeting"
        )

    def test_segments_are_capped_so_a_drill_in_cannot_load_a_whole_meeting(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        service.meeting_dao.segments = [
            MeetingSegment(
                meeting_id=1, start_ms=i * 1000, end_ms=(i + 1) * 1000, text="x" * 500
            )
            for i in range(100)
        ]
        result = service.get_meeting_segments(str(meeting.uuid))
        self.assertIn("truncated", result)
        self.assertLess(len(result["segments"]), 100)

    def test_search_passes_its_filters_through(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        service.search_meetings("the pilot", project_id=1, since_days=7, limit=3)
        call = service.chunk_dao.searches[0]
        self.assertEqual(call["project_id"], 1)
        self.assertEqual(call["limit"], 3)
        self.assertIsNotNone(call["since"])

    def test_search_needs_a_query(self):
        with self.assertRaises(MeetingError):
            build_service().search_meetings("   ")

    def test_notes_for_a_processing_meeting_say_so(self):
        meeting = recording_meeting(status=MeetingStatus.PROCESSING)
        service = build_service(meetings=[meeting])
        result = service.get_meeting_notes(str(meeting.uuid))
        self.assertIsNone(result["notes"])
        self.assertIn("still being written up", result["note"])

    def test_unknown_meeting_id_is_an_error(self):
        with self.assertRaises(MeetingError):
            build_service().get_meeting_notes(str(uuid4()))

    def test_malformed_meeting_id_is_an_error(self):
        with self.assertRaises(MeetingError):
            build_service().get_meeting_notes("not-a-uuid")


class NotesUseNoToolsTests(unittest.TestCase):
    def test_notes_come_from_a_plain_completion_not_the_agent_loop(self):
        # The transcript is untrusted text. Anyone in the room can say
        # "email the city" and the agent loop would hand that to an agent
        # holding send_email, run_terminal_command and run_sql.
        meeting = recording_meeting()
        service = build_service(meetings=[meeting], replies=['{"summary_md": "x"}'])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=1000, text="talking")
        ]
        service._write_notes(meeting)
        self.assertEqual(len(service._claude_service.prompts), 1)
        self.assertEqual(service._agent.calls, [])


class UpdateMeetingTests(unittest.TestCase):
    def test_renames(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        result = service.update_meeting(str(meeting.uuid), title="  Sensor kickoff  ")
        self.assertEqual(result["meeting"]["title"], "Sensor kickoff")

    def test_rejects_an_empty_title(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        with self.assertRaises(MeetingError):
            service.update_meeting(str(meeting.uuid), title="   ")

    def test_moves_to_another_project(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        service.project_dao = FakeProjectDao(ids=(1, 2))
        result = service.update_meeting(str(meeting.uuid), project_id=2)
        self.assertEqual(result["meeting"]["project"]["id"], 2)

    def test_rejects_an_unknown_project(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        with self.assertRaises(MeetingError):
            service.update_meeting(str(meeting.uuid), project_id=999)

    def test_clear_project_detaches_it(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        result = service.update_meeting(str(meeting.uuid), clear_project=True)
        self.assertIsNone(result["meeting"]["project"])

    def test_no_changes_is_a_no_op_not_an_error(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        result = service.update_meeting(str(meeting.uuid))
        self.assertEqual(result["meeting"]["uuid"], str(meeting.uuid))


class DeleteMeetingTests(unittest.TestCase):
    def test_deletes_a_finished_meeting(self):
        meeting = recording_meeting(status=MeetingStatus.COMPLETE)
        service = build_service(meetings=[meeting])
        service._cleanup_audio = lambda meeting_id: None
        result = service.delete_meeting(str(meeting.uuid))
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(service.meeting_dao.meetings, {})

    def test_refuses_to_delete_one_that_is_still_recording(self):
        meeting = recording_meeting()
        service = build_service(meetings=[meeting])
        with self.assertRaises(MeetingError) as ctx:
            service.delete_meeting(str(meeting.uuid))
        self.assertIn("still recording", str(ctx.exception))
        self.assertIn(1, service.meeting_dao.meetings)


class RecoveryTests(unittest.TestCase):
    def test_stale_recordings_are_failed_so_a_new_meeting_can_start(self):
        service = build_service(meetings=[recording_meeting()])
        self.assertEqual(service.recover_stale_meetings(), 1)
        self.assertIsNone(service.meeting_dao.get_active())
        self.assertEqual(service.start_meeting()["status"], "recording")


class TranscriptTests(unittest.TestCase):
    def test_long_transcripts_are_truncated_from_the_front(self):
        service = build_service(meetings=[recording_meeting()])
        service.meeting_dao.segments = [
            MeetingSegment(meeting_id=1, start_ms=0, end_ms=1000, text="A" * 200_000),
            MeetingSegment(meeting_id=1, start_ms=1000, end_ms=2000, text="ENDING"),
        ]
        transcript = service._build_transcript(1)
        self.assertTrue(transcript.startswith("[earlier transcript truncated]"))
        # The end is what carries the decisions, so it must survive.
        self.assertTrue(transcript.endswith("ENDING"))


if __name__ == "__main__":
    unittest.main()
