"""
Meeting mode.

Nova has two modes. In agent mode it listens for a turn, answers, and speaks
back. In meeting mode it does none of that: it transcribes, shows the text as
it arrives, and stays quiet. A meeting row with status 'recording' IS meeting
mode — there is no separate flag, so the mode survives a restart and two
clients can never disagree about which mode Nova is in.

Both modes are entered the same two ways: Nova calling start_meeting /
stop_meeting as tools, or the user pressing a button that hits the endpoints
backed by these same methods.

When a meeting stops, finishing it takes long enough (chunk, embed, summarize,
assess) that nobody should be made to wait on the call that stopped it. The
work moves to a background thread and the meeting sits in 'processing' until
it lands.
"""

import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from prompting.prompt_enums import PromptEnums
from src.dao.conversation_dao import ConversationDao
from src.dao.meeting_chunk_dao import MeetingChunkDao
from src.dao.meeting_dao import MeetingDao
from src.dao.meeting_notes_dao import MeetingNotesDao
from src.dao.project_dao import ProjectDao
from src.model.meeting import (
    Meeting,
    MeetingChunk,
    MeetingNotes,
    MeetingSegment,
    MeetingStatus,
)
from src.model.report_type import SUPPORTED_REPORT_TYPES, ReportType
from src.service.embedding_service import EmbeddingService
from src.service.update_service import UpdateService

# Passage length for retrieval. Long enough that a chunk carries an idea,
# short enough that a hit points at a place in the meeting rather than a
# quarter of it.
CHUNK_SECONDS = float(os.getenv("MEETING_CHUNK_SECONDS", "75"))

# Where captured audio is written while a meeting runs.
AUDIO_DIR = Path(os.getenv("MEETING_AUDIO_DIR", "./meeting_audio"))

# Meeting audio is other people's conversation; it is deleted once the
# transcript and notes exist unless explicitly kept.
RETAIN_AUDIO = (os.getenv("MEETING_RETAIN_AUDIO", "false").strip().lower()
                in ("1", "true", "yes"))

# Guard on the notes prompt. An hour of speech is ~10k tokens and fine; a
# forgotten recording that ran all afternoon is not.
_MAX_TRANSCRIPT_CHARS = 120_000


class MeetingError(Exception):
    """A meeting operation that failed for a reason the caller should hear."""


class MeetingService:
    def __init__(self) -> None:
        self.meeting_dao = MeetingDao()
        self.chunk_dao = MeetingChunkDao()
        self.notes_dao = MeetingNotesDao()
        self.project_dao = ProjectDao()
        self.conversation_dao = ConversationDao()
        self.embedding_service = EmbeddingService()
        self.update_service = UpdateService()
        # Imported lazily in _agent_loop(): AgentLoop pulls in ToolService and
        # the whole tool surface, and most calls into this service never need
        # a model at all.
        self._agent = None
        self.finalize_threads: list[threading.Thread] = []

    # ---------- mode ----------

    def get_active_meeting(self) -> dict | None:
        """The meeting currently recording, or None when Nova is in agent mode."""
        meeting = self.meeting_dao.get_active()
        return self._to_dict(meeting) if meeting else None

    def get_state(self) -> dict:
        """
        Which mode Nova is in, for the client's toggle and for the tools.

        Derived from the table rather than held in memory on purpose: a crash
        mid-meeting would otherwise leave the flag and the data disagreeing.
        """
        active = self.get_active_meeting()
        return {
            "mode": "meeting" if active else "agent",
            "meeting": active,
        }

    def start_meeting(
        self,
        title: str | None = None,
        project_id: int | None = None,
        conversation_uuid: str | None = None,
    ) -> dict:
        """
        Put Nova into meeting mode and open a meeting to record into.

        conversation_uuid is injected by the tool harness, never chosen by the
        model; it is what lets a meeting started by voice inherit the project
        the user was already working in.
        """
        existing = self.meeting_dao.get_active()
        if existing is not None:
            raise MeetingError(
                f"A meeting is already recording (started "
                f"{self._clock(existing.started_at)}, "
                f"{'untitled' if not existing.title else existing.title!r}). "
                "Stop it before starting another."
            )

        resolved_project_id = self._resolve_project_id(project_id, conversation_uuid)

        meeting = self.meeting_dao.create(
            Meeting(
                title=(title or "").strip() or None,
                status=MeetingStatus.RECORDING,
                started_at=datetime.now(timezone.utc),
                project_id=resolved_project_id,
            )
        )
        return {
            "status": "recording",
            "meeting": self._to_dict(meeting),
            "note": (
                "Nova is in meeting mode: transcribing only, not answering. "
                "Call stop_meeting when the meeting is over."
            ),
        }

    def stop_meeting(
        self,
        meeting_uuid: str | None = None,
        generate_notes: bool = True,
    ) -> dict:
        """
        Leave meeting mode and finish the meeting off in the background.

        Returns as soon as recording has stopped. Chunking, embedding, notes,
        and the follow-up assessment run on a daemon thread, because the caller
        here is either a person who pressed a button or a model mid-sentence,
        and neither should wait a minute for a summary.
        """
        meeting = (
            self._require_meeting(meeting_uuid)
            if meeting_uuid
            else self.meeting_dao.get_active()
        )
        if meeting is None:
            raise MeetingError("No meeting is currently recording.")
        if meeting.status != MeetingStatus.RECORDING:
            raise MeetingError(
                f"That meeting is already {meeting.status}, not recording."
            )

        self.meeting_dao.set_status(
            meeting.id, MeetingStatus.PROCESSING, ended_at=datetime.now(timezone.utc)
        )

        thread = threading.Thread(
            target=self._finalize,
            args=(meeting.id, bool(generate_notes)),
            name=f"nova-meeting-finalize-{meeting.id}",
            daemon=True,
        )
        self.finalize_threads = [t for t in self.finalize_threads if t.is_alive()]
        self.finalize_threads.append(thread)
        thread.start()

        return {
            "status": "processing",
            "meeting_uuid": str(meeting.uuid),
            "note": (
                "Recording stopped and Nova is back in agent mode. The write-up "
                "is being prepared and will appear on the meeting shortly."
                if generate_notes
                else "Recording stopped and Nova is back in agent mode."
            ),
        }

    # ---------- capture ----------

    def commit_segments(
        self,
        meeting_id: int,
        segments: list,
        offset_seconds: float = 0.0,
    ) -> list[dict]:
        """
        Persist a window of transcript, timed from the start of the recording.

        `segments` are ASRService TranscriptSegments whose times are relative to
        the slice they were transcribed from, so offset_seconds carries them
        back onto the meeting's own clock.
        """
        rows: list[MeetingSegment] = []
        for segment in segments:
            text = (segment.text or "").strip()
            if not text:
                continue
            rows.append(
                MeetingSegment(
                    meeting_id=int(meeting_id),
                    start_ms=max(0, int((segment.start + offset_seconds) * 1000)),
                    end_ms=max(0, int((segment.end + offset_seconds) * 1000)),
                    text=text,
                )
            )
        if not rows:
            return []
        self.meeting_dao.insert_segments(rows)
        return [
            {"startMs": row.start_ms, "endMs": row.end_ms, "text": row.text}
            for row in rows
        ]

    def audio_path_for(self, meeting_id: int) -> Path:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        return AUDIO_DIR / f"meeting_{int(meeting_id)}.webm"

    def recover_stale_meetings(self) -> int:
        """
        Fail any meeting left recording by a crash, at startup.

        Only one meeting may record at a time, so a single abandoned row would
        otherwise block every future meeting with a confusing error.
        """
        stale = self.meeting_dao.close_stale_recordings()
        if stale:
            print(
                f"Recovered {len(stale)} meeting(s) left recording by a previous run: "
                f"{[str(m.uuid) for m in stale]}"
            )
        return len(stale)

    # ---------- retrieval ----------

    def list_meetings(
        self,
        project_id: int | None = None,
        limit: int = 20,
        since_days: int | None = None,
    ) -> list[dict]:
        """Meetings, newest first. Cheap: no transcript, no notes body."""
        since = (
            datetime.now(timezone.utc) - timedelta(days=int(since_days))
            if since_days
            else None
        )
        meetings = self.meeting_dao.get_all(
            project_id=project_id, limit=max(1, min(int(limit), 100)), since=since
        )
        return [self._to_dict(meeting) for meeting in meetings]

    def get_meeting_notes(self, meeting_uuid: str) -> dict:
        """
        The write-up for one meeting.

        This is the right first call for "what happened in that meeting" — the
        summary was already written, and searching for it would be slower and
        worse than reading it.
        """
        meeting = self._require_meeting(meeting_uuid)
        notes = self.notes_dao.get_latest(meeting.id)
        if notes is None:
            return {
                "meeting": self._to_dict(meeting),
                "notes": None,
                "note": (
                    "This meeting is still being written up."
                    if meeting.status == MeetingStatus.PROCESSING
                    else "No notes have been generated for this meeting yet."
                ),
            }
        return {"meeting": self._to_dict(meeting), "notes": self._notes_to_dict(notes)}

    def get_meeting_segments(
        self,
        meeting_uuid: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> dict:
        """
        Verbatim transcript for a bounded window of one meeting.

        The escape hatch for when a search hit is not enough. Capped server-side
        so a careless end_ms cannot pull an entire meeting into context.
        """
        meeting = self._require_meeting(meeting_uuid)
        segments = self.meeting_dao.get_segments(meeting.id, start_ms, end_ms)

        total = len(segments)
        kept, chars = [], 0
        for segment in segments:
            chars += len(segment.text)
            if chars > _MAX_SEGMENT_WINDOW_CHARS:
                break
            kept.append(segment)

        result = {
            "meeting": self._to_dict(meeting),
            "segments": [
                {"startMs": s.start_ms, "endMs": s.end_ms, "text": s.text} for s in kept
            ],
        }
        if len(kept) < total:
            result["truncated"] = (
                f"Showing {len(kept)} of {total} segments. Narrow the window with "
                "start_ms and end_ms to see the rest."
            )
        return result

    def search_meetings(
        self,
        query: str,
        project_id: int | None = None,
        meeting_uuid: str | None = None,
        since_days: int | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Semantic search across meeting transcripts.

        Returns passages, not transcripts: each hit carries the meeting it came
        from and where in it, so an answer can cite a place and drill in with
        get_meeting_segments if it needs the verbatim words around it.
        """
        query = (query or "").strip()
        if not query:
            raise MeetingError("A search query is required.")

        meeting_id = None
        if meeting_uuid:
            meeting_id = self._require_meeting(meeting_uuid).id

        since = (
            datetime.now(timezone.utc) - timedelta(days=int(since_days))
            if since_days
            else None
        )
        embedding = self.embedding_service.embed_text(query)
        rows = self.chunk_dao.search(
            embedding=embedding,
            project_id=project_id,
            meeting_id=meeting_id,
            since=since,
            limit=max(1, min(int(limit), 20)),
        )
        return [
            {
                "meeting_uuid": row.get("meeting_uuid"),
                "meeting_title": row.get("meeting_title"),
                "started_at": row.get("started_at"),
                "start_ms": row.get("start_ms"),
                "end_ms": row.get("end_ms"),
                "content": row.get("content"),
                "similarity": row.get("similarity"),
            }
            for row in rows
        ]

    # ---------- notes ----------

    def generate_notes(self, meeting_uuid: str, instructions: str | None = None) -> dict:
        """
        Write (or re-write) the notes for a meeting.

        Additive: every call appends a new notes row, so asking for a different
        cut of the same meeting never destroys the first one.
        """
        meeting = self._require_meeting(meeting_uuid)
        notes = self._write_notes(meeting, instructions)
        if notes is None:
            raise MeetingError(
                "That meeting has no transcript to write up — nothing was "
                "captured, or it is all silence."
            )
        return {"meeting": self._to_dict(meeting), "notes": self._notes_to_dict(notes)}

    # ---------- finalize ----------

    def _finalize(self, meeting_id: int, generate_notes: bool) -> None:
        """
        Body of a stopped meeting, on a daemon thread with nobody awaiting it.

        Every path must end with the meeting out of 'processing': one left
        stuck there reads as a hang, and because only one meeting may record at
        a time, a wedged meeting is not just cosmetic.
        """
        try:
            meeting = self.meeting_dao.get(meeting_id)
            if meeting is None:
                return

            self._chunk_and_embed(meeting)

            notes = self._write_notes(meeting) if generate_notes else None
            if notes is not None:
                self._run_followup(meeting, notes)

            self.meeting_dao.set_status(meeting_id, MeetingStatus.COMPLETE)
            self._cleanup_audio(meeting_id)
        except Exception as exc:
            print(f"Meeting {meeting_id} failed to finalize: {exc}")
            try:
                self.meeting_dao.set_status(meeting_id, MeetingStatus.FAILED)
            except Exception as inner:
                print(f"Meeting {meeting_id} could not be marked failed: {inner}")

    def _chunk_and_embed(self, meeting: Meeting) -> int:
        """
        Roll segments into passages and embed them for search.

        Segments are single utterances and retrieve badly alone; a passage is
        the smallest unit that carries an idea. Re-chunking replaces whatever
        was there so a re-run cannot double the corpus.
        """
        segments = self.meeting_dao.get_segments(meeting.id)
        if not segments:
            return 0

        passages: list[tuple[int, int, str]] = []
        buffer: list[str] = []
        start_ms = segments[0].start_ms
        end_ms = segments[0].end_ms
        for segment in segments:
            if buffer and (segment.end_ms - start_ms) > CHUNK_SECONDS * 1000:
                passages.append((start_ms, end_ms, " ".join(buffer)))
                buffer, start_ms = [], segment.start_ms
            buffer.append(segment.text)
            end_ms = segment.end_ms
        if buffer:
            passages.append((start_ms, end_ms, " ".join(buffer)))

        embeddings = self.embedding_service.embed_texts([text for _, _, text in passages])
        self.chunk_dao.delete_for_meeting(meeting.id)
        self.chunk_dao.insert_chunks(
            [
                MeetingChunk(
                    meeting_id=meeting.id,
                    content=text,
                    embedding=embedding,
                    start_ms=start,
                    end_ms=end,
                )
                for (start, end, text), embedding in zip(passages, embeddings)
            ]
        )
        return len(passages)

    def _write_notes(
        self, meeting: Meeting, instructions: str | None = None
    ) -> MeetingNotes | None:
        transcript = self._build_transcript(meeting.id)
        if not transcript:
            return None

        prompt = PromptEnums.MEETING_NOTES_PROMPT.load().replace(
            "{transcript}", transcript
        )
        if instructions and instructions.strip():
            prompt = (
                f"{prompt}\n\nThe user asked for this specific cut of the "
                f"meeting, which takes precedence over the general shape above "
                f"where they conflict:\n{instructions.strip()}"
            )

        reply = self._agent_loop()._run_agent_loop(prompt)
        parsed = self._extract_json_object(reply) or {}

        summary = str(parsed.get("summary_md") or "").strip()
        if not summary:
            # The model answered but not in the shape asked for. Its prose is
            # still a write-up, and losing the meeting over a formatting miss
            # would be the worse failure.
            summary = reply.strip() or "No summary could be generated."

        notes = self.notes_dao.create(
            MeetingNotes(
                meeting_id=meeting.id,
                summary_md=summary,
                decisions=[str(d) for d in (parsed.get("decisions") or []) if d],
                action_items=[a for a in (parsed.get("action_items") or []) if isinstance(a, dict)],
                model=os.getenv("ANTHROPIC_MODEL") or None,
            )
        )

        title = str(parsed.get("title") or "").strip()
        if title and not meeting.title:
            self.meeting_dao.set_title(meeting.id, title[:120])
        return notes

    def _run_followup(self, meeting: Meeting, notes: MeetingNotes) -> dict | None:
        """
        Decide whether this meeting needs to reach the user proactively.

        Deliberately a full agent loop rather than one completion: deciding
        whether something is urgent often needs context the notes do not carry,
        and the agent has the tools to go look. It decides only; delivery stays
        system-side through the update dispatcher, the same as every other
        piece of background work.
        """
        if not notes.action_items and not notes.decisions:
            return None

        project = (
            self.project_dao.get(meeting.project_id) if meeting.project_id else None
        )
        prompt = json.dumps(
            {
                "meeting": {
                    "title": meeting.title,
                    "started_at": str(meeting.started_at),
                    "project": (
                        {"name": project.name, "description": project.description}
                        if project
                        else None
                    ),
                },
                "summary": notes.summary_md,
                "decisions": notes.decisions,
                "action_items": notes.action_items,
                "now": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )

        try:
            reply = self._agent_loop()._run_agent_loop(
                prompt, system=PromptEnums.MEETING_FOLLOWUP_PROMPT.load()
            )
        except Exception as exc:
            print(f"Meeting {meeting.id} follow-up assessment failed: {exc}")
            return None

        decision = self._extract_json_object(reply) or {}
        if not decision.get("notify"):
            print(
                f"Meeting {meeting.id}: no follow-up needed "
                f"({decision.get('reason') or 'no reason given'})"
            )
            return None

        message = str(decision.get("message") or "").strip()
        if not message:
            print(f"Meeting {meeting.id}: follow-up wanted but no message written.")
            return None

        report_type = self._validated_report_type(decision.get("report_type"))
        created = self.update_service.create_update(
            update_message=message,
            project_id=meeting.project_id,
            report_type=str(report_type) if report_type else None,
        )
        print(
            f"Meeting {meeting.id}: follow-up queued by {report_type or 'badge'} "
            f"({decision.get('reason') or 'no reason given'})"
        )
        return created

    # ---------- helpers ----------

    def _agent_loop(self):
        if self._agent is None:
            from src.harness.agent_loop import AgentLoop

            self._agent = AgentLoop()
        return self._agent

    def _build_transcript(self, meeting_id: int) -> str:
        segments = self.meeting_dao.get_segments(meeting_id)
        transcript = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()
        if len(transcript) > _MAX_TRANSCRIPT_CHARS:
            # Keep the end: a meeting's decisions and next steps land last.
            transcript = (
                "[earlier transcript truncated]\n"
                + transcript[-_MAX_TRANSCRIPT_CHARS:]
            )
        return transcript

    @staticmethod
    def _clock(value) -> str:
        """
        HH:MM from a timestamp that may be a datetime or an ISO string.

        SQLModel skips validation on table=True models, so a row read back
        through PostgREST keeps its timestamps as JSON strings rather than
        datetimes. Anything that formats one has to cope with both.
        """
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        try:
            return datetime.fromisoformat(str(value)).strftime("%H:%M")
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _validated_report_type(value) -> ReportType | None:
        if not value:
            return None
        try:
            report_type = ReportType(str(value).strip().lower())
        except ValueError:
            return None
        # An unsupported-but-known type would land as a badge-only update the
        # user is never told about; drop to no type so at least it is honest.
        return report_type if report_type in SUPPORTED_REPORT_TYPES else None

    @staticmethod
    def _extract_json_object(text: str) -> dict | None:
        """
        Pull the last balanced JSON object out of a model reply.

        The last one rather than the first: an agent that reasoned in prose
        before answering may well have shown an example along the way, and the
        answer is what it finished with.
        """
        if not text:
            return None
        cleaned = re.sub(r"```(?:json)?", "", text)
        depth = 0
        end = -1
        for index in range(len(cleaned) - 1, -1, -1):
            char = cleaned[index]
            if char == "}":
                if depth == 0:
                    end = index
                depth += 1
            elif char == "{":
                depth -= 1
                if depth == 0 and end != -1:
                    try:
                        parsed = json.loads(cleaned[index : end + 1])
                    except json.JSONDecodeError:
                        end = -1
                        continue
                    return parsed if isinstance(parsed, dict) else None
        return None

    def _resolve_project_id(
        self, project_id: int | None, conversation_uuid: str | None
    ) -> int | None:
        if project_id is not None:
            if self.project_dao.get(int(project_id)) is None:
                raise MeetingError(f"Project {project_id} does not exist.")
            return int(project_id)
        if conversation_uuid:
            try:
                conversation = self.conversation_dao.get_by_uuid(UUID(str(conversation_uuid)))
            except (ValueError, AttributeError):
                return None
            if conversation is not None:
                return conversation.project_id
        return None

    def _require_meeting(self, meeting_uuid: str) -> Meeting:
        try:
            uuid = UUID(str(meeting_uuid))
        except (ValueError, AttributeError):
            raise MeetingError(f"'{meeting_uuid}' is not a valid meeting id.")
        meeting = self.meeting_dao.get_by_uuid(uuid)
        if meeting is None:
            raise MeetingError(f"No meeting found with id {meeting_uuid}.")
        return meeting

    def _cleanup_audio(self, meeting_id: int) -> None:
        if RETAIN_AUDIO:
            return
        path = self.audio_path_for(meeting_id)
        try:
            if path.exists():
                path.unlink()
            self.meeting_dao.set_audio_path(meeting_id, None)
        except Exception as exc:
            print(f"Could not delete audio for meeting {meeting_id}: {exc}")

    def _to_dict(self, meeting: Meeting) -> dict:
        project = None
        if meeting.project_id is not None:
            found = self.project_dao.get(meeting.project_id)
            if found is not None:
                project = {"id": found.id, "name": found.name}
        return {
            "uuid": str(meeting.uuid),
            "title": meeting.title,
            "status": str(meeting.status),
            "started_at": (
                meeting.started_at.isoformat()
                if hasattr(meeting.started_at, "isoformat")
                else meeting.started_at
            ),
            "ended_at": (
                meeting.ended_at.isoformat()
                if hasattr(meeting.ended_at, "isoformat")
                else meeting.ended_at
            ),
            "project": project,
        }

    @staticmethod
    def _notes_to_dict(notes: MeetingNotes) -> dict:
        return {
            "summary_md": notes.summary_md,
            "decisions": notes.decisions or [],
            "action_items": notes.action_items or [],
            "created_at": (
                notes.created_at.isoformat()
                if hasattr(notes.created_at, "isoformat")
                else notes.created_at
            ),
        }


# Ceiling on one get_meeting_segments call, so drilling into a window can
# never turn into loading the whole meeting.
_MAX_SEGMENT_WINDOW_CHARS = 12_000
