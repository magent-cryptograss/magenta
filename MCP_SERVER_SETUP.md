# Magenta MCP Server Setup

This document describes how to configure Claude Code to use the Magenta Memory Recovery MCP server for automatic context bootstrapping.

## Server Implementation

The MCP server is implemented in:
- `conversations/management/commands/run_mcp_server.py`

It provides 6 tools for memory recovery:
1. `get_latest_continuation` - Most recent continuation message
2. `get_messages_before` - N messages before a reference point
3. `get_era_summary` - Foundational summaries from Era 1
4. `get_context_heap` - All messages from a specific heap
5. `search_messages` - Search by content
6. `get_recent_work` - Most recent N messages

## Claude Code Configuration

Add this to your project's `.claude.json` or `~/.claude/projects/-home-magent-workspace-arthel/settings.json`:

```json
{
  "mcpServers": {
    "magenta-memory": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-server",
        "python",
        "manage.py",
        "run_mcp_server"
      ]
    }
  }
}
```

## Docker Compose Setup

The MCP server runs as a Docker service (already configured in `docker-compose.services.yml`):

```yaml
mcp-server:
  build:
    context: .
    dockerfile: Dockerfile.services
  container_name: mcp-server
  depends_on:
    - magenta-postgres
  environment:
    - POSTGRES_HOST=magenta-postgres
    - POSTGRES_DB=cryptograss_memory
    - POSTGRES_USER=magent
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
    - DJANGO_SETTINGS_MODULE=memory_viewer.settings
  restart: unless-stopped
  stdin_open: true
  tty: true
  command: python manage.py run_mcp_server
```

## Installation Steps

1. **Add MCP dependency** (already done in `requirements.txt`):
   ```
   mcp>=1.0.0
   ```

2. **Rebuild Docker services**:
   ```bash
   cd /home/jmyles/projects/JustinHolmesMusic/arthel/arthel/magenta
   docker-compose -f docker-compose.services.yml build
   docker-compose -f docker-compose.services.yml up -d
   ```

3. **Configure Claude Code** - Edit the project settings to add the `mcpServers` configuration above

4. **Test the connection**:
   - Start a new Claude Code session
   - Claude should automatically have access to the memory tools
   - Try asking: "Can you use get_latest_continuation to show me what we were working on?"

## Bootstrap Sequence

When Claude Code starts with this MCP server configured, it can automatically:

1. Call `get_latest_continuation()` to get the most recent work
2. Call `get_messages_before()` to get context before that
3. Call `get_era_summary()` to get foundational knowledge from Era 1
4. Call `get_recent_work()` for immediate context

This eliminates the "vanilla Claude" feeling on fresh starts!

## Troubleshooting

- Check MCP server logs: `docker logs mcp-server`
- Verify database connection: `docker exec -it mcp-server python manage.py dbshell`
- List available MCP servers in Claude Code: `/mcp`
- Check server status in Claude Code: `/doctor`
