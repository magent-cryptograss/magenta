#!/bin/bash
# container-startup.sh

echo "Cloning repositories to /home/magent/..."
su - magent -c "
    cd /home/magent

    # Clone arthel if not already present
    if [ ! -d arthel ]; then
        echo 'Cloning arthel...'
        git clone https://github.com/jMyles/arthel.git
    else
        echo 'arthel already cloned'
    fi

    # Clone magenta if not already present
    if [ ! -d magenta ]; then
        echo 'Cloning magenta...'
        git clone https://github.com/magent-cryptograss/magenta.git
    else
        echo 'magenta already cloned'
    fi

    # Clone pickipedia if not already present
    if [ ! -d pickipedia ]; then
        echo 'Cloning pickipedia...'
        git clone https://github.com/jMyles/pickipedia.git
    else
        echo 'pickipedia already cloned'
    fi

    # Symlink CLAUDE.md from magenta to home directory
    if [ -f magenta/CLAUDE.md ] && [ ! -f CLAUDE.md ]; then
        echo 'Symlinking CLAUDE.md to home directory...'
        ln -s magenta/CLAUDE.md CLAUDE.md
    fi
"

echo "Fixing permissions..."
chown -R magent:magent /home/magent/.claude
chown magent:magent /home/magent/.claude.json 2>/dev/null || true

echo "Loading environment variables from .env..."
# Load and export all variables from .env file
ENV_FILE="/home/jmyles/projects/JustinHolmesMusic/arthel/arthel/magenta/.env"
if [ -f "$ENV_FILE" ]; then
    set -a  # automatically export all variables
    source "$ENV_FILE"
    set +a  # turn off auto-export
    echo "✓ Environment variables loaded"
else
    echo "⚠ No .env file found at $ENV_FILE"
fi

echo "Starting SSH service..."
service ssh start

echo "Starting PostgreSQL service..."
service postgresql start

# Setup GitHub CLI authentication from token if available
if [ -n "$GH_TOKEN" ]; then
    echo "Configuring GitHub CLI from GH_TOKEN..."
    echo "$GH_TOKEN" | gh auth login --with-token
    gh auth setup-git
    echo "✓ GitHub CLI authenticated"
else
    echo "No GH_TOKEN provided, GitHub CLI not authenticated"
fi

# Configure MCP memory server for Claude Code
echo "Configuring MCP memory server..."
su - magent -c "claude mcp add --scope user --transport stdio magenta-memory 'cd /home/jmyles/projects/JustinHolmesMusic/arthel/arthel/magenta && source django-venv/bin/activate && python manage.py run_mcp_server'"
echo "✓ MCP memory server configured"

# echo "Pre-pulling Puppeteer MCP Docker image..."
# docker pull mcp/puppeteer

echo "Starting code-server as magent user..."
su - magent -c "cd /home/jmyles/projects/JustinHolmesMusic/arthel && code-server --bind-addr 0.0.0.0:8080 --auth none --disable-telemetry . &"

echo "Container ready."
tail -f /dev/null
