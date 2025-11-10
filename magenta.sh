#!/bin/bash
# Script to SSH into Docker container and start Claude Code session
# Usage: ./magenta.sh [local|hunter]
#   local  - Connect to local Docker container (default)
#   hunter - Connect to hunter VPS

set -e  # Exit on error

# Check if mosh is installed (optional but recommended)
USE_MOSH=false
if command -v mosh &> /dev/null; then
    USE_MOSH=true
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Mosh not found (optional)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Mosh provides persistent SSH connections that survive network changes."
    echo "Install it for better connection reliability:"
    echo ""
    echo "  macOS:   brew install mosh"
    echo "  Ubuntu:  sudo apt install mosh"
    echo "  Arch:    sudo pacman -S mosh"
    echo ""
    echo "Continuing with regular SSH..."
    echo ""
fi

# Parse target argument (default to local)
TARGET="${1:-local}"

# Set connection parameters based on target
case "$TARGET" in
    local)
        SSH_HOST="localhost"
        SSH_PORT="2222"
        SSH_USER="magent"
        HOST_KEY_ID="[localhost]:2222"
        ;;
    hunter)
        SSH_HOST="hunter.cryptograss.live"
        SSH_PORT="22"
        SSH_USER="sshrouter"
        HOST_KEY_ID="hunter.cryptograss.live"
        ;;
    *)
        echo "Usage: $0 [local|hunter]"
        echo "  local  - Connect to local Docker container (default)"
        echo "  hunter - Connect to hunter VPS"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Connecting to: $TARGET ($SSH_USER@$SSH_HOST:$SSH_PORT)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if SSH key has changed
if ssh-keygen -F "$HOST_KEY_ID" > /dev/null 2>&1; then
    # Key exists, try to connect to check if it's valid
    # For hunter, we need -t flag because route-ssh uses docker exec -it
    TTY_FLAG=""
    if [ "$TARGET" = "hunter" ]; then
        TTY_FLAG="-t"
    fi

    if ! ssh $TTY_FLAG -o StrictHostKeyChecking=yes -o BatchMode=yes -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" exit 2>/dev/null; then
        # Connection failed, likely due to changed host key
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⚠️  SSH HOST KEY HAS CHANGED"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "This usually happens when the container/server has been rebuilt."
        echo ""
        read -p "Has the $TARGET been rebuilt? (y/n): " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Removing old host key and adding new one..."
            ssh-keygen -R "$HOST_KEY_ID" 2>/dev/null
            echo "Connecting to accept new host key..."
            ssh $TTY_FLAG -o StrictHostKeyChecking=accept-new -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" exit
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

# Connect using mosh if available, otherwise SSH
# Pass through GH_TOKEN and other environment variables
REMOTE_COMMAND="
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
        # Try to continue, if that fails offer to start fresh
        tmux new-session -s magenta \"cd ~ && (
            # Try to continue - if it fails, check for specific error
            if ! claude --continue 2>/tmp/claude_error.log; then
                if grep -iq 'no conversation found to continue' /tmp/claude_error.log; then
                    echo ''
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo 'No conversation found to continue.'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo ''
                    read -p 'Start a fresh conversation? (y/n): ' -n 1 -r
                    echo ''

                    if [[ \\\$REPLY =~ ^[Yy]\\\$ ]]; then
                        echo 'Starting fresh conversation...'
                        claude
                    else
                        echo 'Exiting...'
                    fi
                else
                    echo ''
                    echo 'Claude Code failed with an error. Check /tmp/claude_error.log for details.'
                    echo ''
                    echo 'Press Enter to close...'
                    read
                fi
                rm -f /tmp/claude_error.log
            fi
        )\"
    fi
"

if [ "$USE_MOSH" = true ]; then
    mosh --ssh="ssh -p $SSH_PORT" "$SSH_USER@$SSH_HOST" -- bash -c "$REMOTE_COMMAND"
else
    ssh -o StrictHostKeyChecking=accept-new -t -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "$REMOTE_COMMAND"
fi
