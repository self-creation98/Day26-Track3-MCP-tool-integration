#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export NPM_CONFIG_CACHE="$REPO_DIR/.npm-cache"

mkdir -p "$NPM_CONFIG_CACHE"
npx -y @modelcontextprotocol/inspector "$(command -v python)" "$SCRIPT_DIR/mcp_server.py"
