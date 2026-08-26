import json
import os
import re
from uuid import UUID

from src.dao.memory_chunk_dao import MemoryChunkDao
from src.model.conversation import Conversation
from src.model.memory_chunk import MemoryChunk
from src.model.message import MessageRole
from src.service.claude_service import ClaudeService
from src.service.conversation_service import ConversationService
from src.service.embedding_service import EmbeddingService

_MAX_CHUNKS_PER_CONVERSATION = 12
_MAX_TOOL_CONTENT_CHARS = 400
_FETCH_LIMIT = 5

# --- automatic retrieval (memory injected into the prompt, unasked) ---------

# How many chunks a turn may carry. Five is what the tool returns, and it is
# the point where the block is still shorter than the reply it informs.
_RETRIEVAL_LIMIT = 5

# Cosine-similarity floor for injecting a chunk nobody asked for.
#
# A nearest-neighbour search always returns its k nearest rows, so without a
# floor every turn gets five memories whether or not any of them are about the
# question — which is worse than none, because irrelevant context misleads.
# 0.40 is the empirical query-to-document balance point for
# text-embedding-3-small, whose relevant matches land around 0.30-0.55 (much
# lower than query-to-query similarity, so thresholds quoted for semantic
# caching do not transfer here).
_MIN_SIMILARITY = float(os.getenv("NOVA_MEMORY_MIN_SIMILARITY", "0.40"))

# Chunks are summaries, but a runaway one should not crowd out the reply.
_MAX_INJECTED_CHARS = 320

_WORD_RE = re.compile(r"[A-Za-z0-9']+")

# Turns with nothing to look up. Retrieval on "yes" or "thanks" embeds the
# acknowledgment and returns whatever happens to sit nearest it in vector
# space, which is noise by construction.
_NON_RETRIEVABLE_WORDS = frozenset(
    {
        "yes", "yeah", "yep", "yup", "no", "nope", "nah", "ok", "okay",
        "sure", "thanks", "thank", "you", "please", "stop", "cancel",
        "nevermind", "never", "mind", "done", "correct", "right", "wrong",
        "exactly", "perfect", "great", "cool", "nice", "hello", "hi", "hey",
        "nova", "goodbye", "bye", "go", "on", "it", "do", "that", "this",
        "again", "continue", "repeat", "louder", "quieter", "and", "the",
        "a", "an", "i", "we", "sounds", "good", "got",
    }
)

_MEMORY_HEADER = (
    "Recalled from your long-term memory because it looks relevant to what the "
    "user just said. This is background you already know: use it where it "
    "helps, ignore it where it does not, and never announce that you looked it "
    "up. Call fetch_memory when you need something these lines do not cover."
)

_SUMMARIZE_PROMPT = """You are distilling a finished conversation into long-term memory chunks for an AI assistant named Nova.

Each chunk must be a standalone statement that will still make sense months from now, with no pronouns that depend on the conversation ("the user prefers X", not "he said he prefers it"). Capture durable facts, decisions, preferences, plans, and outcomes — including results of tool calls. Skip greetings, chit-chat, and anything with no lasting value.

Return ONLY a JSON array of strings (no markdown fences, no commentary). Return [] if nothing is worth remembering.

Conversation transcript:
{transcript}"""


class MemoryChunkService:
    def __init__(self):
        self.memory_chunk_dao = MemoryChunkDao()
        self.conversation_service = ConversationService()
        self.embedding_service = EmbeddingService()
        self.claude_service = ClaudeService()

    def process_conversations(self) -> dict:
        """
        Distill every closed-but-unprocessed conversation into memory chunks.

        For each conversation: summarize its messages into standalone chunks,
        embed them, insert into memory_chunk (carrying the conversation's
        project fk when it has one), then mark the conversation processed.
        Failures on one conversation are logged and skipped so the batch
        keeps moving; the conversation stays unprocessed and is retried on
        the next scheduler run. Not exposed as a tool — the worker runs this.
        """
        conversations = self.conversation_service.get_unprocessed_closed_conversations()
        processed = 0
        chunks_created = 0
        failed = 0

        for conversation in conversations:
            try:
                chunks_created += self._process_conversation(conversation)
                self.conversation_service.mark_processed(conversation.uuid)
                processed += 1
            except Exception as exc:
                failed += 1
                print(f"Failed to process conversation {conversation.uuid}: {exc}")

        summary = {
            "conversations_processed": processed,
            "memory_chunks_created": chunks_created,
            "failures": failed,
        }
        print(f"process_conversations: {summary}")
        return summary

    def _process_conversation(self, conversation: Conversation) -> int:
        transcript = self._build_transcript(conversation)
        if not transcript:
            return 0

        chunk_texts = self._summarize_to_chunks(transcript)
        if not chunk_texts:
            return 0

        embeddings = self.embedding_service.embed_texts(chunk_texts)
        chunks = [
            MemoryChunk(
                content=text,
                embedding=embedding,
                project_id=conversation.project_id,
            )
            for text, embedding in zip(chunk_texts, embeddings)
        ]
        self.memory_chunk_dao.insert_memory_chunks(chunks)
        return len(chunks)

    def _build_transcript(self, conversation: Conversation) -> str:
        """Flatten a conversation's messages into labelled lines for summarization."""
        lines: list[str] = []
        for message in self.conversation_service.get_messages(conversation.uuid):
            content = (message.content or "").strip()
            if not content:
                continue
            if message.role == MessageRole.TOOL:
                content = content[:_MAX_TOOL_CONTENT_CHARS]
            lines.append(f"[{message.role}] {content}")
        return "\n".join(lines)

    def _summarize_to_chunks(self, transcript: str) -> list[str]:
        response = self.claude_service.get_response(
            _SUMMARIZE_PROMPT.format(transcript=transcript)
        )
        text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        ).strip()
        return self._parse_chunks(text)

    @staticmethod
    def _parse_chunks(text: str) -> list[str]:
        if not text:
            return []

        # Tolerate markdown fences despite the prompt forbidding them.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[len("json"):]
            text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Not JSON — treat the whole summary as a single memory chunk
            # rather than losing the conversation entirely.
            return [text][:_MAX_CHUNKS_PER_CONVERSATION]

        if not isinstance(parsed, list):
            return []
        chunks = [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
        return chunks[:_MAX_CHUNKS_PER_CONVERSATION]

    def fetch_memory(self, prompt: str, project_id: int | None = None) -> str:
        """
        Vector nearest-neighbor lookup over memory chunks.

        With a project_id, searches that project's memory plus general
        (project-less) memory; without one, searches everything.
        """
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("A non-empty prompt is required to search memory.")

        embedding = self.embedding_service.embed_text(prompt)
        chunks = self.memory_chunk_dao.get_memory_chunks(
            embedding, project_id=project_id, limit=_FETCH_LIMIT
        )
        if not chunks:
            return "No relevant memories found."

        lines = [f"{index}. {chunk.content}" for index, chunk in enumerate(chunks, start=1)]
        return "Relevant memories (most similar first):\n" + "\n".join(lines)

    @staticmethod
    def is_retrievable_query(text: str) -> bool:
        """
        Whether a turn is worth a memory lookup at all.

        Acknowledgments, confirmations, and one-word commands carry no subject
        to search for. Embedding them costs a round trip and returns whatever
        sits nearest a content-free phrase, so they are skipped outright.
        """
        words = _WORD_RE.findall((text or "").lower())
        if not words:
            return False
        return any(word not in _NON_RETRIEVABLE_WORDS for word in words)

    def retrieve_context(
        self,
        query: str,
        project_id: int | None = None,
        limit: int = _RETRIEVAL_LIMIT,
        min_similarity: float = _MIN_SIMILARITY,
    ) -> str | None:
        """
        Relevance-gated memory for injecting into a prompt, or None.

        The difference from fetch_memory is the gate and the return contract.
        fetch_memory answers a question the model chose to ask, so returning
        the five nearest rows is right even when they are a poor match — the
        model asked. This runs on every turn whether or not memory is wanted,
        so it returns nothing at all unless the rows actually clear
        `min_similarity`, and None (rather than prose) so the caller can tell
        "nothing relevant" from "here is something".
        """
        query = (query or "").strip()
        if not query or not self.is_retrievable_query(query):
            return None

        embedding = self.embedding_service.embed_text(query)
        matches = self.memory_chunk_dao.match_memory_chunks(
            embedding, project_id=project_id, limit=limit
        )

        lines: list[str] = []
        for match in matches:
            if match.similarity < min_similarity:
                # Ordered by distance, so the first miss ends the useful run.
                break
            content = (match.chunk.content or "").strip()
            if not content:
                continue
            if len(content) > _MAX_INJECTED_CHARS:
                content = content[: _MAX_INJECTED_CHARS - 1].rstrip() + "…"
            lines.append(f"- {content}")

        if not lines:
            return None
        return _MEMORY_HEADER + "\n" + "\n".join(lines)

    def retrieve_context_for_conversation(
        self, query: str, conversation_uuid: UUID | str | None
    ) -> str | None:
        """
        retrieve_context scoped by the conversation's project, like the tool.

        Falls back to searching all memory when the conversation has no
        project or cannot be read — a scoping lookup failing is not a reason
        to answer the turn with no memory at all.
        """
        project_id = None
        if conversation_uuid is not None:
            try:
                conversation = self.conversation_service.get_conversation(
                    UUID(str(conversation_uuid))
                )
                project_id = conversation.project_id if conversation else None
            except Exception as exc:
                print(f"Memory scoping lookup failed (searching all memory): {exc}")
        return self.retrieve_context(query, project_id=project_id)

    def fetch_memory_for_conversation(self, prompt: str, conversation_uuid: str) -> str:
        """
        Tool-facing wrapper around fetch_memory: scopes the search by the
        active conversation's project (or all memory when it has none).
        conversation_uuid is injected by the harness, not the model.
        """
        conversation = self.conversation_service.get_conversation(
            UUID(str(conversation_uuid))
        )
        project_id = conversation.project_id if conversation is not None else None
        return self.fetch_memory(prompt, project_id=project_id)
