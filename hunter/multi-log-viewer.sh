#!/bin/bash
# Multi-pane log viewer for hunter deployment
# Shows all important logs in tmux panes

SESSION="hunter-logs"

# Check if session already exists
tmux has-session -t $SESSION 2>/dev/null

if [ $? != 0 ]; then
    # Create new session with first pane for MCP server logs
    tmux new-session -d -s $SESSION -n logs

    # Split into 4 panes
    tmux split-window -h -t $SESSION
    tmux split-window -v -t $SESSION:0.0
    tmux split-window -v -t $SESSION:0.2

    # Pane 0 (top-left): MCP server logs
    tmux send-keys -t $SESSION:0.0 'ssh root@hunter.cryptograss.live "docker logs -f mcp-server"' C-m

    # Pane 1 (top-right): Memory Lane (Django web) logs
    tmux send-keys -t $SESSION:0.1 'ssh root@hunter.cryptograss.live "docker logs -f memory-lane"' C-m

    # Pane 2 (bottom-left): Watcher logs
    tmux send-keys -t $SESSION:0.2 'ssh root@hunter.cryptograss.live "docker logs -f watcher"' C-m

    # Pane 3 (bottom-right): Postgres logs
    tmux send-keys -t $SESSION:0.3 'ssh root@hunter.cryptograss.live "docker logs -f magenta-postgres"' C-m

    # Set pane titles
    tmux select-pane -t $SESSION:0.0 -T "MCP Server"
    tmux select-pane -t $SESSION:0.1 -T "Memory Lane"
    tmux select-pane -t $SESSION:0.2 -T "Watcher"
    tmux select-pane -t $SESSION:0.3 -T "PostgreSQL"
fi

# Attach to session
tmux attach-session -t $SESSION
