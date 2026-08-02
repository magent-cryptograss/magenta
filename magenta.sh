#!/bin/bash
# magenta.sh — connect to a Docker container and start (or attach) a Claude Code
# session inside tmux. Supports local containers, hunter VPS, named parallel
# sessions in one container, and joining another user's shared session.
#
# Session model:
#   * The tmux session provides SSH-disconnect-survival and multiplayer support.
#   * Inside tmux, we invoke `claude` in one of four modes (see MODES below).
#   * The Claude Code supervisor (`claude agents`) tracks conversations across
#     restarts by short-ID and name. `--session foo` looks up the Claude session
#     named `foo`, attaches to it, or creates it fresh if none exists.

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

MODES (mutually exclusive; last one on the line wins):
  (no mode flag)        DEFAULT. Drop into the Claude session picker
                        (`claude agents` + auto-`/resume`). Shows all past
                        sessions including idle ones the supervisor stopped.
                        Arrow to the one you want and hit Enter to attach.
  --session <name>      Attach to the Claude session named <name>. If no such
                        session exists, create it fresh with the reawaken prompt
                        under that name. The tmux session is also named <name>.
  --force-fresh         Kill the existing tmux session (if any) and start a
                        fresh Claude conversation with the reawaken prompt.
                        If combined with --session, the new session gets that
                        name; otherwise it lives under 'magenta'.
  --continue            Old behavior — `claude --continue` in the tmux session.
                        This picks the most-recently-modified conversation in
                        the cwd, which can be wrong when multiple sessions run
                        in parallel. Kept as an escape hatch for when the
                        supervisor is misbehaving.

OTHER OPTIONS:
  --dangerously-skip-permissions
                        Pass through to `claude` — bypass permission prompts.
                        Only takes effect at process start; can't flip mid-session.
  --join <user>         Join another user's container in multiplayer/pair-programming
                        mode. Only valid with TARGET=hunter. Combine with
                        --session <name> to attach to a specific tmux session
                        in their container.
  -h, --help            Show this help and exit.

EXAMPLES:
  magenta.sh                                  # local, session picker
  magenta.sh hunter                           # hunter, session picker
  magenta.sh hunter --session pickipedia      # attach (or create) the 'pickipedia' session
  magenta.sh hunter --session ticketstubs     # ...and separately 'ticketstubs'
  magenta.sh hunter --force-fresh             # fresh Claude, generic 'magenta' name
  magenta.sh hunter --session foo --force-fresh
                                              # kill+recreate: fresh 'foo' session
  magenta.sh hunter --continue                # legacy: --continue in tmux
  magenta.sh hunter --join skyler             # pair-program with skyler
  magenta.sh hunter --join skyler --session review
                                              # join skyler's 'review' tmux session

MENTAL MODEL:
  * tmux session name = what shows in `tmux list-sessions`
  * Claude session name = what shows in `claude agents`
  * When you use --session <name>, both get that name. Kept in sync on purpose:
    one name to think about, not two.
  * `claude agents` (the default when no mode flag) lets you pick any Claude
    session regardless of tmux state. Handy after a container restart.

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
SESSION_NAME_EXPLICIT=false
CONTINUE_MODE=false
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
        --continue)
            CONTINUE_MODE=true
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
            SESSION_NAME_EXPLICIT=true
            shift 2
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Default target = local; default tmux name = magenta.
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

# ─── mode determination (local side) ──────────────────────────────────
# Precedence: --continue > --force-fresh > --session > default (picker)
if [ "$CONTINUE_MODE" = "true" ]; then
    MODE="continue"
elif [ "$FORCE_FRESH" = "true" ]; then
    MODE="fresh"
elif [ "$SESSION_NAME_EXPLICIT" = "true" ]; then
    MODE="named"
else
    MODE="picker"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Connecting to: $TARGET ($SSH_USER@$SSH_HOST:$SSH_PORT)"
echo "   tmux session:  $SESSION_NAME"
echo "   claude mode:   $MODE"
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
# Runs on the container side. The MODE dispatch happens here because the
# Claude session lookup (agents --json) has to run where claude lives.
REMOTE_COMMAND="
    export GH_TOKEN='$GH_TOKEN'
    export POSTGRES_PASSWORD='$POSTGRES_PASSWORD'
    FORCE_FRESH='$FORCE_FRESH'
    DANGEROUSLY_SKIP_PERMISSIONS='$DANGEROUSLY_SKIP_PERMISSIONS'
    SESSION_NAME='$SESSION_NAME'
    MODE='$MODE'

    CLAUDE_FLAGS=''
    if [ \"\$DANGEROUSLY_SKIP_PERMISSIONS\" = 'true' ]; then
        CLAUDE_FLAGS='--dangerously-skip-permissions'
    fi

    # ─── tmux session: attach if exists (unless force-fresh) ──────────
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

    # ─── mode-specific inner command ──────────────────────────────────
    # Build INNER (the command that will run inside the new tmux session)
    # based on MODE. Uses python3 (always present on the container) for
    # JSON parsing rather than jq (not guaranteed).
    lookup_claude_session_id() {
        local target_name=\"\$1\"
        claude agents --json --all 2>/dev/null | python3 -c \"
import sys, json
try:
    for s in json.load(sys.stdin):
        if s.get('name') == '\$target_name':
            print(s.get('id', ''))
            break
except Exception:
    pass
\" 2>/dev/null
    }

    case \"\$MODE\" in
        picker)
            INNER=\"cd ~ && claude agents\"
            ;;
        fresh)
            INNER=\"cd ~ && claude \$CLAUDE_FLAGS 'reawaken magent'\"
            ;;
        named)
            SESS_ID=\$(lookup_claude_session_id \"\$SESSION_NAME\")
            if [ -n \"\$SESS_ID\" ]; then
                echo \"→ Found Claude session '\$SESSION_NAME' (id \$SESS_ID). Attaching.\"
                INNER=\"cd ~ && claude attach \$SESS_ID\"
            else
                echo \"→ No Claude session named '\$SESSION_NAME' — creating one\"
                # --bg registers a new session under the supervisor. We then
                # look it up by name to get its short id.
                claude \$CLAUDE_FLAGS --bg --name \"\$SESSION_NAME\" 'reawaken magent' >/dev/null 2>&1
                sleep 2
                SESS_ID=\$(lookup_claude_session_id \"\$SESSION_NAME\")
                if [ -n \"\$SESS_ID\" ]; then
                    echo \"→ Created and attaching (id \$SESS_ID)\"
                    INNER=\"cd ~ && claude attach \$SESS_ID\"
                else
                    echo \"⚠️  Failed to find or create Claude session '\$SESSION_NAME'\"
                    echo \"    Falling back to the agents picker\"
                    INNER=\"cd ~ && claude agents\"
                fi
            fi
            ;;
        continue)
            # Legacy: --continue with reawaken fallback if no conversation
            # to continue. Kept as escape hatch when supervisor misbehaves.
            INNER=\"cd ~ && (
                if ! claude \$CLAUDE_FLAGS --continue 2>/tmp/claude_error.log; then
                    if grep -iq 'no conversation found to continue' /tmp/claude_error.log; then
                        echo 'No conversation found; starting fresh.'
                        claude \$CLAUDE_FLAGS 'reawaken magent'
                    else
                        echo 'Claude Code failed. See /tmp/claude_error.log'
                        read -p 'Press Enter to close...'
                    fi
                    rm -f /tmp/claude_error.log
                fi
            )\"
            ;;
    esac

    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    echo \"✨ Creating new tmux session: \$SESSION_NAME\"
    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    if [ \"\$MODE\" = 'picker' ]; then
        # \`claude agents\` opens with only currently-active sessions in the
        # visible list — idle sessions (supervisor-stopped after ~1hr) are
        # hidden. Typing \`/resume\` in the dispatch input opens the full
        # picker including idle. Start tmux detached, wait for claude's TUI
        # to be ready, send-keys the /resume, then attach.
        tmux new-session -d -s \"\$SESSION_NAME\" \"\$INNER\"
        sleep 2
        tmux send-keys -t \"\$SESSION_NAME\" '/resume' Enter
        tmux attach-session -t \"\$SESSION_NAME\"
    else
        tmux new-session -s \"\$SESSION_NAME\" \"\$INNER\"
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
