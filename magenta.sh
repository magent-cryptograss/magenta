#!/bin/bash
# Script to SSH into Docker container and start Claude Code session
# Usage: ./magenta.sh

set -e  # Exit on error

# Check if SSH key has changed
if ssh-keygen -F "[localhost]:2222" > /dev/null 2>&1; then
    # Key exists, try to connect to check if it's valid
    if ! ssh -o StrictHostKeyChecking=yes -o BatchMode=yes -p 2222 magent@localhost exit 2>/dev/null; then
        # Connection failed, likely due to changed host key
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⚠️  SSH HOST KEY HAS CHANGED"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "This usually happens when the Docker container has been rebuilt."
        echo ""
        read -p "Has the container been rebuilt? (y/n): " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Removing old host key and adding new one..."
            ssh-keygen -R "[localhost]:2222" 2>/dev/null
            echo "Connecting to accept new host key..."
            ssh -o StrictHostKeyChecking=accept-new -p 2222 magent@localhost exit
            echo "✓ Host key updated successfully!"
            echo ""
        else
            echo "⚠️  Proceeding anyway with StrictHostKeyChecking=no"
            echo "   (Security warning: This bypasses host verification!)"
            echo ""
        fi
    fi
fi

# Source environment variables from magenta/.env if it exists
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# SSH into the container and start/attach to tmux session with Claude Code
# Pass through GH_TOKEN and other environment variables
ssh -o StrictHostKeyChecking=accept-new -t magent@localhost -p 2222 "
    # Load environment variables
    export GH_TOKEN='$GH_TOKEN'
    export POSTGRES_PASSWORD='$POSTGRES_PASSWORD'

    # Check if tmux session 'magenta' exists
    if tmux has-session -t magenta 2>/dev/null; then
        echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        echo '🔄 Attaching to existing tmux session: magenta'
        echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        tmux attach-session -t magenta
    else
        echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        echo '✨ Creating new tmux session: magenta'
        echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        # Create new session and start Claude Code
        # Projects live in ~/workspace/ and logs go to ~/.claude/projects/
        tmux new-session -s magenta \"cd ~ && claude --continue\"
    fi
"
