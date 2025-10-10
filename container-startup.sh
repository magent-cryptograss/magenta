#!/bin/bash
# container-startup.sh - Multi-user version

echo "Starting SSH service..."
service ssh start

# Pull Puppeteer MCP Docker image (optional, speeds up first MCP use)
if [ -S /var/run/docker.sock ]; then
    echo "Pre-pulling Puppeteer MCP Docker image..."
    docker pull mcp/puppeteer || echo "Warning: Could not pull Puppeteer image"
fi

echo "Starting code-server as magent user..."
if [ -n "$CODE_SERVER_PASSWORD" ]; then
    echo "Code-server will require password authentication"
    su - magent -c "cd /home/magent/workspace/arthel && PASSWORD='$CODE_SERVER_PASSWORD' code-server --bind-addr 0.0.0.0:8080 --disable-telemetry . &"
else
    echo "Warning: No CODE_SERVER_PASSWORD set, using auth none"
    su - magent -c "cd /home/magent/workspace/arthel && code-server --bind-addr 0.0.0.0:8080 --auth none --disable-telemetry . &"
fi

echo "Container ready for user: ${DEVELOPER_NAME:-unknown} (${DEVELOPER_FULL_NAME:-unknown})"
echo "Email: ${DEVELOPER_EMAIL:-not-configured}"
echo "GitHub: ${DEVELOPER_GITHUB:-not-configured}"
echo "PostgreSQL host: ${POSTGRES_HOST:-not-configured}"
echo "Port range: Check USER_CONTEXT.md in .claude directory"

tail -f /dev/null
