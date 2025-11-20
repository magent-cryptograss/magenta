#!/bin/bash
# Build .env.local from ansible vault for local development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_FILE="$PROJECT_ROOT/hunter/ansible/vault.yml"
ENV_FILE="$PROJECT_ROOT/.env.local"

# Check if ansible-vault is available
if ! command -v ansible-vault &> /dev/null; then
    echo "Error: ansible-vault not found. Install with: pip install ansible"
    exit 1
fi

# Check if vault file exists
if [ ! -f "$VAULT_FILE" ]; then
    echo "Error: Vault file not found at $VAULT_FILE"
    exit 1
fi

echo "Building .env.local from vault..."

# Extract secrets from vault
POSTGRES_PASSWORD=$(ansible-vault view "$VAULT_FILE" 2>/dev/null | grep vault_postgres_password | cut -d'"' -f2)

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Error: Could not extract postgres password from vault"
    exit 1
fi

# Generate .env.local
cat > "$ENV_FILE" << EOF
# Local development environment - GENERATED FILE
# Generated: $(date)
# Run: scripts/build-local-env.sh to regenerate

# Database connection (via SSH tunnel to hunter)
# 1. Start tunnel: ssh -L 15432:magenta-postgres:5432 root@hunter.cryptograss.live
# 2. Container connects through tunnel
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=15432
POSTGRES_DB=magenta_memory
POSTGRES_USER=magent
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# GitHub CLI Authentication
# Add your personal GitHub token here
# Generate at: https://github.com/settings/tokens
# Required scopes: repo, read:org, workflow
GH_TOKEN=your_github_token_here

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
echo "1. Edit .env.local and add your GH_TOKEN"
echo "2. Start SSH tunnel: ssh -L 15432:magenta-postgres:5432 root@hunter.cryptograss.live"
echo "3. Start your local container"
