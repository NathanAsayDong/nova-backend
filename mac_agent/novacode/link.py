"""
The channel to Nova, dialled from this side.

The Mac connects out to the tower rather than the other way round, for the
same reason the browser does it for /ws/face: no port forwarding, no sshd, no
static address, and it survives sleeping, waking, and changing networks. The
tower never needs to know where this laptop is.

The link is a supervisor channel, not a lifeline. Sessions keep running while
it is down; events buffer; on reconnect the agent says what it has and Nova
asks for whatever it missed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

from . import protocol
from .config import Config
from .sessions import SessionManager

log = logging.getLogger("novacode.link")

_BACKOFF_START = 1.0
_BACKOFF_MAX = 30.0


class Link:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.socket: Any = None
        self.manager = SessionManager(config, self._send)

    async def _send(self, event: dict[str, Any]) -> None:
        socket = self.socket
        if socket is None:
            return
        await socket.send(json.dumps(event))

    async def run_forever(self) -> None:
        backoff = _BACKOFF_START
        while True:
            try:
                # Re-read .env on every attempt. Editing it and wondering why
                # nothing changed is otherwise a guaranteed ten minutes: the
                # daemon runs for weeks, and a value read once at startup is
                # stale for almost all of that.
                self.config = Config.from_env(reload=True)
                if not self.config.token:
                    log.error(
                        "NOVA_CODE_TOKEN is empty in mac_agent/.env — the tower "
                        "will reject the connection. Check the line is "
                        "NOVA_CODE_TOKEN=<value> with an equals sign."
                    )

                headers = (
                    {"Authorization": f"Bearer {self.config.token}"}
                    if self.config.token
                    else None
                )
                async with websockets.connect(
                    self.config.ws_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=8 * 1024 * 1024,
                ) as socket:
                    self.socket = socket
                    backoff = _BACKOFF_START
                    log.info("connected to %s", self.config.ws_url)
                    # Announce what is already running, so a Nova that
                    # restarted (or never knew) can re-sync rather than
                    # assume an idle Mac.
                    await self._send(
                        {
                            "type": protocol.EVT_HELLO,
                            "sessions": self.manager.list(),
                        }
                    )
                    await self._serve(socket)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # A rejected handshake surfaces as a bare "HTTP 403", which
                # reads like a server fault rather than what it is. The tower
                # closes the socket before accepting when the bearer token does
                # not match, and that is the only reason it does so.
                if "403" in str(exc):
                    log.error(
                        "Tower rejected the connection (403): the token does not "
                        "match NOVA_CODE_TOKEN on the server, or the server has "
                        "none set. Retrying in %.0fs",
                        backoff,
                    )
                else:
                    log.warning("link down (%s); retrying in %.0fs", exc, backoff)
            finally:
                self.socket = None

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _serve(self, socket: Any) -> None:
        async for raw in socket:
            try:
                command = json.loads(raw)
            except json.JSONDecodeError:
                await self._send({"type": protocol.EVT_ERROR, "reason": "bad_json"})
                continue
            # Each command is handled on its own task: `start` blocks on a
            # worktree checkout and the CLI booting, and a slow start must not
            # hold up a `feedback` for a session already running.
            asyncio.create_task(self._dispatch(command))

    async def _dispatch(self, command: dict[str, Any]) -> None:
        kind = command.get("command")
        request_id = command.get("request_id")
        try:
            result = await self._handle(kind, command)
            await self._send({"type": "ack", "request_id": request_id, "result": result})
        except Exception as exc:
            log.exception("command %s failed", kind)
            await self._send(
                {
                    "type": protocol.EVT_ERROR,
                    "request_id": request_id,
                    "reason": kind or "unknown",
                    "detail": str(exc),
                }
            )

    async def _handle(self, kind: str | None, command: dict[str, Any]) -> Any:
        manager = self.manager
        if kind == protocol.CMD_START:
            return await manager.start(
                session_id=command["session_id"],
                repo=command["repo"],
                instructions=command["instructions"],
                title=command.get("title"),
                base=command.get("base"),
                isolate=bool(command.get("isolate")),
            )
        if kind == protocol.CMD_FEEDBACK:
            return await manager.feedback(
                command["session_id"], command["text"], steer=bool(command.get("steer"))
            )
        if kind == protocol.CMD_INTERRUPT:
            return await manager.interrupt(command["session_id"])
        if kind == protocol.CMD_STOP:
            return await manager.stop(command["session_id"])
        if kind == protocol.CMD_REPLAY:
            return manager.replay(command["session_id"], int(command.get("after_seq", 0)))
        if kind == protocol.CMD_LIST:
            return manager.list()
        if kind == protocol.CMD_CLAUDE_SESSIONS:
            # Synchronous: both SDK history calls read local .jsonl files and
            # return in milliseconds, so there is nothing to await.
            return manager.claude_sessions(
                command["repo"], limit=int(command.get("limit", 25))
            )
        if kind == protocol.CMD_TRANSCRIPT:
            return manager.transcript(
                command["session_id"],
                command["repo"],
                limit=int(command.get("limit", 20)),
                offset=command.get("offset"),
                prose_only=command.get("prose_only", True),
            )
        if kind == protocol.CMD_ATTACH:
            return await manager.attach(
                command["session_id"],
                repo=command.get("repo"),
                cwd=command.get("cwd"),
                title=command.get("title"),
            )
        raise ValueError(f"Unknown command: {kind}")
