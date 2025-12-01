#!/bin/bash
# Build .env.local from ansible vault for local development
#
# Note: PostgreSQL is on maybelle, not hunter. This script pulls secrets from
# maybelle-config vault and sets up connection via SSH tunnel to maybelle.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.local"

# Try to find maybelle-config vault (check common locations)
VAULT_FILE=""
for candidate in \
    "$PROJECT_ROOT/../maybelle-config/secrets/vault.yml" \
    "$HOME/workspace/maybelle-config/secrets/vault.yml" \
    "$HOME/maybelle-config/secrets/vault.yml"; do
    if [ -f "$candidate" ]; then
        VAULT_FILE="$candidate"
        break
    fi
done

if [ -z "$VAULT_FILE" ]; then
    echo "Error: Could not find maybelle-config vault.yml"
    echo "Tried:"
    echo "  - $PROJECT_ROOT/../maybelle-config/secrets/vault.yml"
    echo "  - $HOME/workspace/maybelle-config/secrets/vault.yml"
    echo "  - $HOME/maybelle-config/secrets/vault.yml"
    echo ""
    echo "Clone maybelle-config repo and try again."
    exit 1
fi

# Check if ansible-vault is available
if ! command -v ansible-vault &> /dev/null; then
    echo "Error: ansible-vault not found. Install with: pip install ansible"
    exit 1
fi

echo "Building .env.local from vault..."
echo "Using vault: $VAULT_FILE"

# Extract secrets from vault
VAULT_CONTENT=$(ansible-vault view "$VAULT_FILE" 2>/dev/null)

POSTGRES_PASSWORD=$(echo "$VAULT_CONTENT" | grep postgres_password | head -1 | sed 's/.*: *//' | tr -d '"')
GH_TOKEN=$(echo "$VAULT_CONTENT" | grep magent_github_token | head -1 | sed 's/.*: *//' | tr -d '"')

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Error: Could not extract postgres password from vault"
    exit 1
fi

if [ -z "$GH_TOKEN" ]; then
    echo "Warning: Could not extract magent_github_token from vault"
    echo "GH_TOKEN will need to be set manually"
    GH_TOKEN="your_github_token_here"
fi

# Generate .env.local
cat > "$ENV_FILE" << EOF
# Local development environment - GENERATED FILE
# Generated: $(date)
# Run: scripts/build-local-env.sh to regenerate

# Database connection (via SSH tunnel to maybelle)
# 1. Start tunnel: ssh -L 15432:localhost:5432 root@maybelle.cryptograss.live
# 2. Container connects through tunnel
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=15432
POSTGRES_DB=magenta_memory
POSTGRES_USER=magent
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# GitHub CLI Authentication (from vault: magent_github_token)
GH_TOKEN=$GH_TOKEN

# Django Settings
DJANGO_SECRET_KEY=local-dev-secret-key-change-if-needed
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Watcher Configuration (if running watcher locally)
CLAUDE_LOGS_DIR=/home/magent/.claude/projects
WATCHER_ERA_NAME=Live Conversations

# Developer Identity
DEVELOPER_NAME=justin
DEVELOPER_FULL_NAME=Justin Holmes
DEVELOPER_EMAIL=justin@cryptograss.live
DEVELOPER_GITHUB=jMyles
EOF

echo "✓ Generated $ENV_FILE"
echo ""
echo "Next steps:"
echo "1. Start SSH tunnel: ssh -L 15432:localhost:5432 root@maybelle.cryptograss.live"
echo "2. Start your local container"
