#!/usr/bin/env bash
#
# Install the Nova code agent as a background service on this Mac.
#
# Sets up three things: a venv beside the code, a launchd agent that starts it
# at login and restarts it if it dies, and a clickable app for starting and
# stopping it by hand. Safe to re-run — it reinstalls over itself.

set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$AGENT_DIR/.venv"
LABEL="com.nova.codeagent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
APP="$HOME/Applications/Nova Code Agent.app"

echo "==> agent at $AGENT_DIR"

if ! command -v claude >/dev/null 2>&1; then
  echo "!! the 'claude' CLI is not on PATH. brew install --cask claude-code" >&2
  exit 1
fi
if ! claude auth status 2>/dev/null | grep -q '"loggedIn": true'; then
  echo "!! claude is not logged in. Run: claude auth login" >&2
  exit 1
fi

echo "==> python venv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$AGENT_DIR/requirements.txt"

if [ ! -f "$AGENT_DIR/.env" ]; then
  cp "$AGENT_DIR/.env.example" "$AGENT_DIR/.env"
  chmod 600 "$AGENT_DIR/.env"
  echo "==> wrote $AGENT_DIR/.env — set NOVA_CODE_WS_URL and NOVA_CODE_TOKEN before starting"
fi

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

echo "==> launchd agent"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV/bin/python</string>
    <string>-m</string>
    <string>novacode</string>
    <string>run</string>
  </array>
  <key>WorkingDirectory</key><string>$AGENT_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOG_DIR/novacode.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/novacode.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <!-- Homebrew's bin, so the agent can find the claude CLI and git.
         launchd gives a login-shell-free PATH that would not include it. -->
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
PLIST_EOF

echo "==> clickable app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<APP_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Nova Code Agent</string>
  <key>CFBundleIdentifier</key><string>com.nova.codeagent.toggle</string>
  <key>CFBundleExecutable</key><string>toggle</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <!-- No Dock icon, no menu bar, no window: clicking it just flips the -->
  <!-- service and quits. This is the "silent shortcut". -->
  <key>LSUIElement</key><true/>
</dict>
</plist>
APP_EOF

cat > "$APP/Contents/MacOS/toggle" <<'TOGGLE_EOF'
#!/usr/bin/env bash
LABEL="com.nova.codeagent"
UID_NUM="$(id -u)"
if launchctl print "gui/$UID_NUM/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
  MSG="Nova code agent stopped."
else
  launchctl bootstrap "gui/$UID_NUM" "$HOME/Library/LaunchAgents/$LABEL.plist" 2>/dev/null || true
  MSG="Nova code agent started."
fi
osascript -e "display notification \"$MSG\" with title \"Nova\"" >/dev/null 2>&1 || true
TOGGLE_EOF
chmod +x "$APP/Contents/MacOS/toggle"

echo "==> starting service"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

cat <<DONE

Installed.

  service   $LABEL  (starts at login, restarts on crash)
  shortcut  $APP    (double-click to stop/start, no window)
  logs      $LOG_DIR/novacode.log
  config    $AGENT_DIR/.env

  status    $AGENT_DIR/scripts/novacode status
  try one   $AGENT_DIR/scripts/novacode task --repo nova-backend "say hello"
DONE
