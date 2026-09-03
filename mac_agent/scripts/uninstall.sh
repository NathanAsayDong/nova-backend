#!/usr/bin/env bash
# Remove the service and the shortcut. Leaves the venv, .env, and any
# worktrees alone — those hold work and configuration, not installation.
set -euo pipefail
LABEL="com.nova.codeagent"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Applications/Nova Code Agent.app"
echo "Removed the service and shortcut. Worktrees under ~/.nova/worktrees are untouched."
