"""
Streamlit chat interface for the Nova backend.

A thin text-only client over the same agent loop the voice websocket uses, so
Nova can be driven from a keyboard instead of a microphone.

Run with:
    uv run streamlit run interface/nova_chat_interface.py
"""

import json
import os
from collections.abc import Iterator

import requests
import streamlit as st

DEFAULT_BACKEND_URL = os.getenv("NOVA_BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = (5, 300)  # (connect, read) — agent turns can run long.


def backend_url() -> str:
    return st.session_state.backend_url.rstrip("/")


def fetch_health() -> tuple[bool, str]:
    try:
        response = requests.get(f"{backend_url()}/health", timeout=(3, 5))
        response.raise_for_status()
        return True, response.json().get("status", "ok")
    except requests.RequestException as exc:
        return False, str(exc)


def fetch_tools() -> list[dict]:
    response = requests.get(f"{backend_url()}/tools", timeout=(3, 15))
    response.raise_for_status()
    return response.json()


def fetch_projects() -> list[dict]:
    response = requests.get(f"{backend_url()}/projects", timeout=(3, 15))
    response.raise_for_status()
    return response.json()


def fetch_conversation_info() -> dict | None:
    """Current conversation state (project attachment etc.), or None if unavailable."""
    conversation_id = st.session_state.conversation_id
    if not conversation_id:
        return None
    try:
        response = requests.get(
            f"{backend_url()}/conversations/{conversation_id}",
            timeout=(3, 15),
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def close_current_conversation() -> None:
    """Closed conversations are terminal — the backend will refuse further turns."""
    conversation_id = st.session_state.conversation_id
    if not conversation_id:
        return
    try:
        requests.post(
            f"{backend_url()}/conversations/{conversation_id}/close",
            timeout=(3, 15),
        )
    except requests.RequestException:
        pass  # Closing is best-effort from the UI; the id is discarded either way.


def stream_reply(message: str) -> Iterator[str]:
    """
    POST a turn to /chat/stream and yield sentence chunks as they arrive.

    The conversation id is stored back into session state so the backend keeps
    threading history for this browser session.
    """
    payload = {"message": message}
    if st.session_state.conversation_id:
        payload["conversationId"] = st.session_state.conversation_id

    try:
        response = requests.post(
            f"{backend_url()}/chat/stream",
            json=payload,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "text/event-stream"},
        )
    except requests.RequestException as exc:
        yield f"⚠️ Could not reach the Nova backend at {backend_url()} ({exc})."
        return

    with response:
        if response.status_code != 200:
            yield f"⚠️ Backend returned {response.status_code}: {response.text[:500]}"
            return

        emitted_any = False
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue

            try:
                event = json.loads(line[len("data:"):].strip())
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")

            if event_type == "start":
                st.session_state.conversation_id = event.get("conversationId")
            elif event_type == "conversation_switched":
                # switch_project closed the old conversation; adopt its successor.
                st.session_state.conversation_id = event.get("conversationId")
                st.toast("Switched projects — continuing in a new conversation.")
            elif event_type == "delta":
                emitted_any = True
                yield event.get("text", "") + " "
            elif event_type == "error":
                yield f"\n\n⚠️ {event.get('message', 'Unknown backend error.')}"
                return
            elif event_type == "done":
                if event.get("conversationId"):
                    st.session_state.conversation_id = event["conversationId"]
                if not emitted_any:
                    yield "_(Nova returned an empty response.)_"
                return


st.set_page_config(page_title="Nova Chat", page_icon="🛰️", layout="centered")

st.session_state.setdefault("backend_url", DEFAULT_BACKEND_URL)
st.session_state.setdefault("conversation_id", None)
st.session_state.setdefault("messages", [])

with st.sidebar:
    st.header("Nova")

    st.text_input("Backend URL", key="backend_url")

    healthy, health_detail = fetch_health()
    if healthy:
        st.success(f"Backend online ({health_detail})")
    else:
        st.error("Backend unreachable")
        st.caption(health_detail)

    st.divider()

    st.caption("Conversation")
    st.code(st.session_state.conversation_id or "not started yet", language=None)

    conversation_info = fetch_conversation_info()
    project = (conversation_info or {}).get("project")
    if project:
        st.success(f"📁 Project: {project.get('name', 'unnamed')} (id {project.get('id')})")
        if project.get("description"):
            st.caption(project["description"])
    elif st.session_state.conversation_id:
        st.caption("No project attached. Ask Nova to assign one.")

    if st.button("New conversation", use_container_width=True):
        close_current_conversation()
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()

    with st.expander("Projects"):
        try:
            projects = fetch_projects()
        except requests.RequestException as exc:
            st.caption(f"Could not load projects: {exc}")
        else:
            if not projects:
                st.caption("No projects yet.")
            for project in projects:
                st.markdown(f"**{project.get('name', 'unnamed')}** (id {project.get('id')})")
                if project.get("description"):
                    st.caption(project["description"])

    with st.expander("Registered tools"):
        try:
            tools = fetch_tools()
        except requests.RequestException as exc:
            st.caption(f"Could not load tools: {exc}")
        else:
            if not tools:
                st.caption("No tools registered.")
            for tool in tools:
                st.markdown(f"**{tool.get('name', 'unnamed')}**")
                description = tool.get("description")
                if description:
                    st.caption(description)

st.title("🛰️ Nova")
st.caption("Text interface to the same agent loop the voice pipeline uses.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Message Nova"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        reply = st.write_stream(stream_reply(prompt))

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # The sidebar rendered before this turn ran, so its conversation id and
    # project attachment may be stale (Nova can assign a project mid-turn).
    # Redraw now that the turn is committed; messages live in session state.
    st.rerun()
