#!/usr/bin/env bash
#
# setup-opencode-sap-ai-core.sh
#
# Configures opencode to use SAP AI Core as its model backend by injecting the
# AI Core service key into the background service as an environment variable.
#
# This is the non-interactive equivalent of running `/connect` -> "SAP AI Core"
# inside the opencode TUI. You do NOT need both: setting AICORE_SERVICE_KEY as a
# service env var registers the credential automatically. (To use /connect
# instead, skip this script, run `opencode`, type `/connect`, pick SAP AI Core,
# and paste the service key JSON.)
#
# Usage:
#   1. Fill in AICORE_SERVICE_KEY below with your BTP service key JSON.
#   2. ./setup-opencode-sap-ai-core.sh
#
set -euo pipefail

# --- Configuration ----------------------------------------------------------

# Paste your SAP AI Core service key here (single line).
# Get it from BTP Cockpit > your AI Core instance > Service Keys.
# Must contain at least: clientid, clientsecret, url, serviceurls.AI_API_URL.
# IMPORTANT: keep the SINGLE quotes — the clientsecret often contains $ or !,
# which the shell would otherwise expand/mangle.
AICORE_SERVICE_KEY='{"clientid":"<CLIENT_ID>","clientsecret":"<CLIENT_SECRET>","url":"https://<your-tenant>.authentication.sap.hana.ondemand.com","serviceurls":{"AI_API_URL":"https://<ai-api-host>.ml.hana.ondemand.com"}}'

# Resource group that holds your model deployments (usually "default").
AICORE_RESOURCE_GROUP='default'

# Model to smoke-test with (any RUNNING deployment in your resource group).
TEST_MODEL='sap-ai-core/anthropic--claude-4.6-sonnet'

# --- Locate the opencode binary ---------------------------------------------

if command -v opencode >/dev/null 2>&1; then
  OC="$(command -v opencode)"
elif [ -x "$HOME/.opencode/bin/opencode" ]; then
  OC="$HOME/.opencode/bin/opencode"
else
  echo "ERROR: opencode not found on PATH or at ~/.opencode/bin/opencode" >&2
  exit 1
fi
echo "Using opencode: $OC ($("$OC" --version))"

# --- Guard against the unfilled placeholder ---------------------------------

case "$AICORE_SERVICE_KEY" in
  *"<CLIENT_ID>"*)
    echo "ERROR: AICORE_SERVICE_KEY still contains the placeholder." >&2
    echo "       Edit this script and paste your real service key JSON first." >&2
    exit 1
    ;;
esac

# --- Configure the background service ----------------------------------------

echo "1) Writing AICORE_SERVICE_KEY into the service env..."
"$OC" service set env AICORE_SERVICE_KEY "$AICORE_SERVICE_KEY"

echo "2) Setting AICORE_RESOURCE_GROUP=$AICORE_RESOURCE_GROUP ..."
"$OC" service set env AICORE_RESOURCE_GROUP "$AICORE_RESOURCE_GROUP"

echo "3) Restarting the background service so it inherits the env..."
"$OC" service restart

echo "4) Verifying registered credentials..."
"$OC" auth list | grep -i "sap ai core" || {
  echo "WARN: SAP AI Core not shown in 'auth list' — check the key." >&2
}

# --- Smoke test --------------------------------------------------------------

echo "5) Smoke test against $TEST_MODEL ..."
# Note: with opencode v2.4.x a harmless 'Schema validation failed' line may be
# printed AFTER the reply — the model output itself and multi-turn context work.
"$OC" run -m "$TEST_MODEL" "reply with exactly: PONG" || true

echo
echo "Done. opencode is wired to SAP AI Core."
echo "List all available models with:  $OC models | grep sap-ai-core"
