# Local Development Setup

This guide covers running the magenta development environment on your laptop, connecting to the hunter postgres database.

## Prerequisites

- Docker and docker-compose installed
- SSH access to hunter.cryptograss.live
- Ansible vault password (for extracting secrets)

## Initial Setup

### 1. Create the Docker network

```bash
docker network create magenta-net
```

### 2. Generate .env.local from vault

```bash
cd /path/to/magenta
./scripts/build-local-env.sh
```

This extracts secrets from the encrypted ansible vault and creates `.env.local` in the magenta directory.

### 3. Fix network configuration (one-time)

Make sure `hunter/docker-compose.local.yml` uses the external network:

```yaml
networks:
  magenta-net:
    external: true
```

## Running the Environment

### 1. Start the SSH tunnel to hunter postgres

In a dedicated terminal, keep this running:

```bash
ssh -L 0.0.0.0:15432:localhost:5432 root@hunter.cryptograss.live
```

This tunnels your local port 15432 (listening on all interfaces) to hunter's postgres on port 5432.

Note: Postgres on hunter is bound to localhost only (127.0.0.1:5432), so it's not exposed to the internet.

### 2. Start the dev workspace

In terminal 1:

```bash
cd magenta/hunter
docker compose -f docker-compose.local.yml up dev-workspace
```

### 3. Start the shared services (MCP server, Memory Lane)

In terminal 2:

```bash
cd magenta
docker compose -f docker-compose.services.yml -f docker-compose.local-override.yml --env-file .env.local up
```

**Important:** Must specify `--env-file .env.local` or the services will use default values and fail to connect to postgres.

## What's Running

After startup, you should have:

- **magenta-dev** (dev-workspace): Your development container with Claude Code
  - SSH: localhost:2222
  - code-server: localhost:8080

- **mcp-server-local**: MCP server connecting to hunter postgres
  - HTTP: localhost:8000

- **memory-lane-local**: Django web UI for viewing conversations
  - Web UI: localhost:3000

## Verifying Connectivity

### Check containers are on the network

```bash
docker network inspect magenta-net --format '{{range .Containers}}{{.Name}} {{end}}'
```

Should show: `magenta-dev mcp-server-local memory-lane-local`

### Check MCP server environment

```bash
docker exec mcp-server-local env | grep POSTGRES
```

Should show:
- POSTGRES_HOST=host.docker.internal
- POSTGRES_PORT=15432
- POSTGRES_DB=magenta_memory
- POSTGRES_USER=magent
- POSTGRES_PASSWORD=(your password)

### Test MCP server from inside dev container

```bash
docker exec -it magenta-dev curl http://mcp-server:8000
```

Should return some HTTP response (not "Could not resolve host").

### Check Claude Code MCP logs

From inside the dev container:

```bash
cat ~/.local/state/claude/logs/mcp-*.log | tail -50
```

Look for successful connections, not "fetch failed" errors.

## Architecture Notes

### Why two separate compose files?

- `hunter/docker-compose.local.yml`: Defines the dev workspace (magenta-dev container)
- `docker-compose.services.yml`: Defines shared services (MCP, Memory Lane, Watcher)
- `docker-compose.local-override.yml`: Minimal local-specific overrides

This keeps the shared services configuration identical between hunter and local, reducing maintenance burden.

### How does the MCP server reach hunter's postgres?

1. SSH tunnel on laptop: `localhost:15432` → `hunter:magenta-postgres:5432`
2. `.env.local` sets `POSTGRES_HOST=host.docker.internal` and `POSTGRES_PORT=15432`
3. `docker-compose.local-override.yml` adds `extra_hosts` mapping for `host.docker.internal` (Linux only)
4. MCP server container connects to `host.docker.internal:15432` which resolves to laptop's localhost
5. Laptop's SSH tunnel forwards to hunter

## Troubleshooting

### "Network magenta-net declared as external, but could not be found"

Run: `docker network create magenta-net`

### "Could not resolve host: mcp-server"

The dev-workspace container isn't on the magenta-net network. Make sure `hunter/docker-compose.local.yml` has `external: true` for the network definition, then restart the container.

### MCP server connecting to wrong postgres port

The `.env.local` file isn't being read. Make sure you're using `--env-file .env.local` in the docker compose command.

### "connection to server at localhost port 5432 failed"

The `host.docker.internal` mapping isn't working. Make sure `docker-compose.local-override.yml` has the `extra_hosts` entry for the mcp-server service.

### SSH tunnel dies / connection drops

The tunnel will drop if your laptop sleeps or network changes. Just restart it:

```bash
ssh -L 0.0.0.0:15432:localhost:5432 root@hunter.cryptograss.live
```

### "Temporary failure in name resolution" in SSH tunnel

This means postgres isn't exposed on hunter's localhost. Make sure you've deployed the updated postgres configuration that includes the port mapping (127.0.0.1:5432:5432).

## Stopping Everything

```bash
# Stop services
cd magenta
docker compose -f docker-compose.services.yml -f docker-compose.local-override.yml down

# Stop dev workspace
cd magenta/hunter
docker compose -f docker-compose.local.yml down

# Kill SSH tunnel (Ctrl+C in that terminal)
```

## When to Use Local vs Hunter

**Use local dev when:**
- Hunter is down or having issues
- Testing changes to MCP server, Memory Lane, or Watcher before deploying
- Working offline (with cached data)

**Use hunter directly when:**
- Normal development work
- Want to see real-time watcher updates
- Multiple team members collaborating

Both environments connect to the same postgres database on hunter, so conversations and data are shared.
