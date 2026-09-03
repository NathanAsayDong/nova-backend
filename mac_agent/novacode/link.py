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
        raise ValueError(f"Unknown command: {kind}")
