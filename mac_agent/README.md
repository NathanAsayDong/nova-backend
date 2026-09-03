# Nova code agent (Mac)

Runs Claude Code on this Mac, on Nova's behalf, against the repos you actually
work in.

Nova's API and worker live on the tower; your code lives here. So Nova cannot
run Claude Code itself — it has to ask this machine to. That is all this is: a
small daemon that dials the tower, holds coding sessions open, and streams
what they do back up.

## Why it is shaped this way

**The Mac dials out.** Same reason the browser does it for `/ws/face`: no port
forwarding, no sshd, no static address, and it survives sleep, wake, and
changing networks. The tower never needs to know where this laptop is.

**Sessions are threads, not jobs.** A `ClaudeSDKClient` stays open between
requests, so Nova can ask what a task is doing, send a correction into it, and
pick it up again tomorrow. That is why there is an event loop here rather than
a subprocess call.

**The link is a supervisor, not a lifeline.** Sessions keep running while it is
down, events buffer, and Claude Code persists its own transcript — so even a
full agent restart re-attaches by session id instead of losing the work.

**Every session gets a git worktree.** Same repo, same history, same remote,
different checkout. The agent never edits the files you have open, and the
result arrives as a branch you review like anyone else's.

## Install

```bash
brew install --cask claude-code   # if you haven't
claude auth login                 # subscription, not --console
mac_agent/scripts/install.sh
```

That creates a venv, installs a launchd service that starts at login and
restarts on crash, and puts a **Nova Code Agent** app in `~/Applications` that
toggles the service on and off with no window (it is `LSUIElement`, so no Dock
icon, no Terminal — just a notification).

Then fill in `mac_agent/.env` (copied from `.env.example`, chmod 600):

| variable | meaning |
|---|---|
| `NOVA_CODE_WS_URL` | the tower's `/ws/coding` endpoint |
| `NOVA_CODE_TOKEN` | shared secret with the tower — **treat like an SSH key** |
| `NOVA_CODE_REPOS_ROOT` | where bare repo names resolve from |
| `NOVA_CODE_WORKTREE_ROOT` | where session checkouts go |
| `NOVA_CODE_MAX_BUDGET_USD` | optional per-session ceiling |

## Use it without Nova

The interesting half works before the tower half exists:

```bash
scripts/novacode task --repo nova-backend "add a /health endpoint"
scripts/novacode status
scripts/novacode logs
```

## Wire protocol

Commands down, events up, both plain JSON.

| command | |
|---|---|
| `start` | `session_id`, `repo`, `instructions`, `title?`, `base?` |
| `feedback` | `session_id`, `text`, `steer?` — queues if the agent is mid-turn, sends now if idle, cuts the turn short if `steer` |
| `interrupt` | `session_id` |
| `stop` | `session_id` |
| `replay` | `session_id`, `after_seq` — what the link missed |
| `list` | live sessions |

Events are `hello`, `started`, `text`, `thinking`, `tool`, `rate_limit`,
`result`, `error`, `closed`. A `tool` event carries an `artifact` whose kind is
one of `diff` / `file` / `terminal` — the three the Nova chat UI already draws,
so nothing new was needed on the display side.

## Safety

Three layers, weakest last:

1. **Claude Code's OS sandbox** (`NOVA_CODE_SANDBOX=1`) — the only one that
   actually contains a process.
2. **Path containment** (`permissions.py`) — a session cannot read or write
   outside its worktree. A fence for a cooperative agent making a mistake,
   which is the realistic risk.
3. **A command denylist** — `rm -rf /`, `sudo`, `mkfs` and friends. A speed
   bump, nothing more.

Two things worth knowing:

- The `NOVA_CODE_TOKEN` grants the ability to edit your repos. Anyone who can
  reach Nova with it can run coding agents here.
- `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` are **stripped** from every
  CLI subprocess (`config.child_env`). Either one would make Claude Code skip
  subscription auth and bill the API instead, silently — and `main.py` and
  `worker.py` both push nova-backend's `.env` into the process environment, so
  it is one line away from happening by accident. Subscription auth is a
  property of this code, not of the environment it inherits.

## Known limits

- **The Mac must be awake.** Asleep laptop, no coding. The tower should queue
  and say so rather than fail.
- **Replay is bounded** to the last 400 events per session. The authoritative
  record is Claude Code's own `.jsonl` under `~/.claude/projects/`.
- **A fresh session costs ~43k cache-creation tokens** before your instructions
  are counted — system prompt plus tool definitions. Resuming reuses that
  cache, so one long thread is materially cheaper than many short tasks. It is
  also why this is built around threads.
