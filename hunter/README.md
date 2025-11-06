# Hunter Deployment

Infrastructure for deploying the magenta memory system to hunter VPS.

## Architecture

### Shared Services (run on hunter host or dedicated container)

**PostgreSQL Database** (`ai-sandbox` or `postgres` container):
- Database: `magenta_memory`
- Accessible from all user containers
- Stores all conversation history with `from`/`to` columns

**Conversation Watcher** (`watcher` container or systemd service):
- Monitors `/opt/magenta/*/` claude logs directories
- Auto-imports new messages in real-time
- Runs as single shared service
- Configuration:
  - `CLAUDE_LOGS_DIR`: Colon-separated paths to watch (e.g., `/opt/magenta/justin/.claude/project-logs:/opt/magenta/rj/.claude/project-logs`)
  - `WATCHER_ERA_NAME`: Era to import into (default: "Current Working Era (Era N)")

### Per-User Containers

Each team member gets isolated container with:
- Dedicated ports (e.g., justin: 14000-14009, rj: 14010-14019)
- Own `.claude` directory mounted from `/opt/magenta/{username}/`
- Shared access to PostgreSQL database
- SSH access via key-based routing

## Files

- `Dockerfile` - Main user container image
- `Dockerfile.services` - Services container (watcher, postgres)
- `docker-compose.services.yml` - Shared services stack
- `docker-compose.local.yml` - Local development setup
- `ansible/` - Ansible playbooks for hunter deployment

## Deployment

### Local Development

```bash
# Start services (postgres, watcher)
cd hunter
docker-compose -f docker-compose.services.yml up -d

# Start dev container
docker-compose -f docker-compose.local.yml up -d
```

### Hunter VPS

```bash
# Deploy everything
cd hunter/ansible
ansible-playbook -i inventory.yml playbook.yml
```

This will:
1. Build shared base image
2. Deploy postgres container
3. Deploy watcher container
4. Create per-user containers for justin, rj, skyler
5. Configure SSH routing and Caddy reverse proxy

## Watcher Service

The watcher runs as a **shared service** (not per-user) because:
- Single process can watch multiple user directories
- Deduplication works across all users
- Simpler resource usage
- Consistent era management

It watches all user log directories and imports to shared database with proper `from`/`to` attribution.

## Database Access

All containers access the shared database:
- Host: `postgres` (container name) or `ai-sandbox` (if using existing postgres)
- Database: `magenta_memory`
- User: `magent`
- Password: (from ansible vault or environment)

## Logs

- Watcher: `/opt/magenta/logs/watcher.log` (rotated, 10MB max, 5 backups)
- Import counts displayed in real-time
- Deduplication stats tracked

## Ready for Hunter

✅ Import count tracking (created vs skipped)
✅ Line accounting with verification
✅ Perfect deduplication (tested on 365 files, 131K+ lines)
✅ Watcher running and importing in real-time
✅ All infrastructure organized in `/hunter`
