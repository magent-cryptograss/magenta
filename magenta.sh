#!/bin/bash
# magenta.sh — connect to a Docker container and start (or attach) a Claude Code
# session inside tmux. Supports local containers, hunter VPS, named parallel
# sessions in one container, and joining another user's shared session.

set -e  # Exit on error

# ─── help text ─────────────────────────────────────────────────────────
show_help() {
    cat <<'EOF'
Usage: magenta.sh [TARGET] [OPTIONS]

Connect to a container and drop into a tmux + Claude Code session.

TARGETS:
  local                 Local Docker container (default). SSH to localhost:2222.
  hunter                Hunter VPS. SSH via sshrouter@hunter.cryptograss.live;
                        the route-ssh script routes to your container by SSH key.

OPTIONS:
  --session <name>      Name for the tmux session (default: magenta). Use this to
                        run multiple parallel sessions in the same container —
                        e.g. one for the current task and another for a side
                        investigation you want to keep alive. Attaches to an
                        existing session with that name if one exists, otherwise
                        creates it.
  --force-fresh         Kill the existing tmux session (if any) and start a
                        fresh Claude conversation instead of --continue'ing.
                        Recommended when creating a new named session so Claude
                        doesn't attach to the wrong prior conversation.
  --dangerously-skip-permissions
                        Pass through to `claude` — bypass permission prompts.
                        Only takes effect at process start; can't flip mid-session.
  --join <user>         Join another user's container in multiplayer/pair-programming
                        mode. Only valid with TARGET=hunter. Combine with
                        --session <name> to attach to a specific tmux session
                        in their container.
  -h, --help            Show this help and exit.

EXAMPLES:
  magenta.sh                                    # Attach to local, session 'magenta'
  magenta.sh hunter                             # Attach to hunter, session 'magenta'
  magenta.sh hunter --force-fresh               # Fresh Claude on hunter
  magenta.sh hunter --session alchemy           # Named parallel session on hunter
  magenta.sh hunter --session alchemy --force-fresh
                                                # Fresh Claude in named session
                                                # (recommended for a brand-new session)
  magenta.sh hunter --join skyler               # Join skyler's default session
  magenta.sh hunter --join skyler --session review
                                                # Join skyler's 'review' session

NOTES ON PARALLEL SESSIONS:
  tmux session names are per-container. Two named sessions in the same container
  keep their tmux state separate, but `claude --continue` picks the last-modified
  conversation in the current directory. So if you plan to keep two sessions
  running for different projects, either:
    (a) start each with --force-fresh so it launches a new conversation, or
    (b) run them from different working directories inside the container.
  Otherwise both sessions may try to attach the same underlying conversation.

ENVIRONMENT:
  Reads magenta/.env if present. GH_TOKEN and POSTGRES_PASSWORD are forwarded
  to the remote session.
EOF
}

# ─── argument parsing ──────────────────────────────────────────────────
FORCE_FRESH=false
DANGEROUSLY_SKIP_PERMISSIONS=false
JOIN_USER=""
SESSION_NAME=""
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --force-fresh)
            FORCE_FRESH=true
            shift
            ;;
        --dangerously-skip-permissions)
            DANGEROUSLY_SKIP_PERMISSIONS=true
            shift
            ;;
        --join)
            JOIN_USER="$2"
            shift 2
            ;;
        --session)
            SESSION_NAME="$2"
            shift 2
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Default target = local; default session = magenta.
TARGET="${POSITIONAL_ARGS[0]:-local}"
SESSION_NAME="${SESSION_NAME:-magenta}"

# ─── mosh check (remote targets only) ──────────────────────────────────
USE_MOSH=false
if [ "$TARGET" != "local" ]; then
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
fi

# ─── target resolution ────────────────────────────────────────────────
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
        echo "Error: unknown target '$TARGET'"
        echo ""
        show_help
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Connecting to: $TARGET ($SSH_USER@$SSH_HOST:$SSH_PORT)"
echo "   tmux session:  $SESSION_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ─── host key check ────────────────────────────────────────────────────
if ssh-keygen -F "$HOST_KEY_ID" > /dev/null 2>&1; then
    TTY_FLAG=""
    if [ "$TARGET" = "hunter" ]; then
        TTY_FLAG="-t"
    fi

    if ! ssh $TTY_FLAG -o StrictHostKeyChecking=yes -o BatchMode=yes -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" exit 2>/dev/null; then
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

# ─── env forwarding ────────────────────────────────────────────────────
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# ─── remote command ────────────────────────────────────────────────────
# Runs on the remote (or local container) side. Uses SESSION_NAME for the
# tmux session so multiple parallel sessions can coexist in one container.
REMOTE_COMMAND="
    export GH_TOKEN='$GH_TOKEN'
    export POSTGRES_PASSWORD='$POSTGRES_PASSWORD'
    FORCE_FRESH='$FORCE_FRESH'
    DANGEROUSLY_SKIP_PERMISSIONS='$DANGEROUSLY_SKIP_PERMISSIONS'
    SESSION_NAME='$SESSION_NAME'

    CLAUDE_FLAGS=''
    if [ \"\$DANGEROUSLY_SKIP_PERMISSIONS\" = 'true' ]; then
        CLAUDE_FLAGS='--dangerously-skip-permissions'
    fi

    if tmux has-session -t \"\$SESSION_NAME\" 2>/dev/null; then
        if [ \"\$FORCE_FRESH\" = 'true' ]; then
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo \"⚠️  --force-fresh: Killing existing tmux session: \$SESSION_NAME\"
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            tmux kill-session -t \"\$SESSION_NAME\"
        else
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            echo \"🔄 Attaching to existing tmux session: \$SESSION_NAME\"
            echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            tmux attach-session -t \"\$SESSION_NAME\"
            exit 0
        fi
    fi

    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    echo \"✨ Creating new tmux session: \$SESSION_NAME\"
    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    if [ \"\$FORCE_FRESH\" = 'true' ]; then
        tmux new-session -s \"\$SESSION_NAME\" \"cd ~ && claude \$CLAUDE_FLAGS 'reawaken magent'\"
    else
        tmux new-session -s \"\$SESSION_NAME\" \"cd ~ && (
            if ! claude \$CLAUDE_FLAGS --continue 2>/tmp/claude_error.log; then
                if grep -iq 'no conversation found to continue' /tmp/claude_error.log; then
                    echo ''
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo 'No conversation found to continue.'
                    echo 'Starting fresh with reawaken prompt...'
                    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                    echo ''
                    claude \$CLAUDE_FLAGS 'reawaken magent'
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

# ─── --join branch (hunter multiplayer) ────────────────────────────────
if [ -n "$JOIN_USER" ]; then
    if [ "$TARGET" != "hunter" ]; then
        echo "Error: --join is only supported with the hunter target"
        exit 1
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Joining ${JOIN_USER}'s container in multiplayer mode..."
    [ "$SESSION_NAME" != "magenta" ] && echo "(session: $SESSION_NAME)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    JOIN_CMD="$JOIN_USER"
    [ "$SESSION_NAME" != "magenta" ] && JOIN_CMD="$JOIN_USER $SESSION_NAME"
    ssh -o StrictHostKeyChecking=accept-new -t -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "$JOIN_CMD"
    exit $?
fi

# ─── normal connection (mosh preferred) ────────────────────────────────
if [ "$USE_MOSH" = true ]; then
    mosh --predict=always --ssh="ssh -p $SSH_PORT" "$SSH_USER@$SSH_HOST" -- bash -c "$REMOTE_COMMAND"
else
    ssh -o StrictHostKeyChecking=accept-new -t -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "$REMOTE_COMMAND"
fi
