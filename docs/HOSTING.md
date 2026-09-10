# Hosting Nova off the home network

The frontend is a static React build on Firebase Hosting. The API stays on the
tower and is reached through a Cloudflare Tunnel, so nothing on the home router
is opened and the tower's only public surface is port 8000 behind Cloudflare's
TLS. One username and password, set in the API's environment, gate everything.

```
browser ── https ──► Firebase Hosting (nova-voice-nd.web.app)
   │
   └── https / wss ─► api.nova-api.us  ──► Cloudflare edge ──► cloudflared on the tower ──► uvicorn :8000
```

## One-time setup

### 1. Cloudflare: domain and tunnel (on the tower)

1. Cloudflare dashboard → **Domain Registration → Register Domains**. Buy a
   domain; it lands in the account with DNS already on Cloudflare.
2. Dashboard → **Zero Trust**. Pick a team name and the Free plan.
3. Zero Trust → **Networks → Tunnels → Create a tunnel** → type *Cloudflared*,
   name it `nova-tower`, pick **Windows 64-bit**, copy the install command.
4. On the tower, in an **Administrator PowerShell**, paste that command. It
   installs `cloudflared` as a Windows service that starts at boot and
   reconnects on its own. The tunnel shows *Healthy* in the dashboard.
5. Back in the wizard, **Public Hostname**: subdomain `api`, your domain,
   type `HTTP`, URL `localhost:8000`. Save. Cloudflare creates the DNS record.
6. With uvicorn running on the tower, from a phone off the Wi-Fi:
   `https://api.nova-api.us/health` should return `{"status":"ok"}`.

Cloudflare supports WebSockets by default and only drops an HTTP response that
has sent nothing for 100 seconds; the chat stream and the sockets start
sending immediately, so neither is affected.

### 2. Backend environment (on the tower)

Add to the tower's `.env`, then restart the API:

```
NOVA_AUTH_USERNAME=<you>
NOVA_AUTH_PASSWORD=<a long password>
NOVA_ALLOWED_ORIGINS=https://nova-voice-nd.web.app,https://nova-voice-nd.firebaseapp.com
PUBLIC_BASE_URL=https://api.nova-api.us
MCP_OAUTH_REDIRECT_BASE=https://api.nova-api.us
```

- Without the username and password, every gated route refuses (503) and
  nothing can log in. There is deliberately no bypass flag.
- `PUBLIC_BASE_URL` is where Twilio calls back; `MCP_OAUTH_REDIRECT_BASE` is
  where MCP OAuth providers redirect to. Both used to assume ngrok/localhost.
- Optional: `NOVA_SESSION_DAYS` (default 30, sliding).

Then create the sessions table:

```
uv run python scripts/run_migrations.py 006
```

### 3. Mac coding agent

In `mac_agent/.env`, point at the tunnel:

```
NOVA_CODE_WS_URL=wss://api.nova-api.us/ws/coding
```

Its own shared token still applies; the login gate leaves `/ws/coding` alone.

### 4. Frontend build and deploy (on the Mac)

In `nova-frontend/.env.production`:

```
VITE_API_URL=https://api.nova-api.us
```

then

```
npm run deploy
```

which type-checks, builds, and pushes `dist/` to Firebase Hosting. The build
refuses to run while `.env.production` still holds the placeholder. The app is
at `https://nova-voice-nd.web.app`, the face at `/face`.

## How login works

- `POST /auth/login` with `{username, password}` returns a bearer token. The
  browser keeps it in `localStorage` and sends it as `Authorization: Bearer`
  on every fetch and as `?token=` on every WebSocket.
- The server stores only the token's SHA-256 in `nova_sessions`, with
  `expires_at`, `last_seen_at`, `user_agent`, `ip`, `revoked_at`.
- Sessions slide: use inside the window extends it. Settings → *Signed-in
  devices* lists live sessions; *Sign out* revokes this one, *Sign out
  everywhere* revokes all.
- Five failed logins from one address, or twenty from anywhere, lock the
  endpoint for fifteen minutes.
- A 401 anywhere in the app drops the token and shows the login screen.

### What is not behind the gate

| path | why |
|---|---|
| `/`, `/health` | liveness |
| `/auth/login` | how you get in |
| `/calls/*`, `/sms/*` | Twilio webhooks, gated on Twilio's request signature |
| `/ws/coding` | the Mac agent, gated on `NOVA_CODE_TOKEN` |
| `/ws/face` | the face display, deliberately open |
| `/mcp-servers/oauth/callback` | the OAuth provider's redirect; carries a one-time state nonce |

`/docs` and `/openapi.json` are gated too; pass a bearer token to read them.

## Day to day

- **Change the password**: edit `.env` on the tower, restart the API, then
  *Sign out everywhere* (old sessions stay valid until revoked or expired).
- **Frontend change**: `npm run deploy`.
- **Local development**: `npm run dev:local` (backend on this machine) or
  `npm run dev:tower` (backend on the LAN). You log in the same way; the
  Vite origin is always allowed by CORS.
- **Streamlit interface** (`interface/nova_chat_interface.py`) does not send a
  token and will get 401s against a gated API. It still works against a local
  backend with no credentials set only for the open routes; treat it as
  unsupported for now.
