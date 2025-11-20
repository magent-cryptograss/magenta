# MCP Server Networking Notes

## IPv4/IPv6 Resolution (November 2025)

**Problem:** Server listening on `::` (IPv6 only) while Node.js fetch defaults to IPv4 in Docker networking.

**Symptoms:**
- Claude Code in user containers getting "fetch failed" connecting to `http://mcp-server:8000`
- Server logs showing "Uvicorn running on http://[::]:8000"
- `/proc/net/tcp` showed no IPv4 listener
- `/proc/net/tcp6` showed port 8000 on IPv6 `[::]`

**Root Cause:**
- Docker DNS resolution returns IPv4 addresses for service names
- Node.js fetch was trying IPv4 connection
- Server only listening on IPv6

**Solution:**
Changed from `host="::"` to `host="0.0.0.0"` in conversations/mcp/server.py:
```python
config = uvicorn.Config(
    app,
    host="0.0.0.0",  # Listen on IPv4 (works for both in most Docker setups)
    port=8000,
    log_level="info"
)
```

**Deployment:** November 6, 2025 - commit 1646fdc, deployed to hunter VPS

## Container Networking Considerations

### Current Setup (Same Container)
- Claude Code and MCP server run in same container
- `localhost` works fine with IPv6 fix
- No Docker networking complexity

### Future Setup (Separate Containers)
When MCP server runs in its own container:

**Option 1: Docker service name**
```json
{
  "mcpServers": {
    "magenta-memory": {
      "type": "sse",
      "url": "http://mcp-server:8000/sse"
    }
  }
}
```
- Requires both containers on same Docker network
- Use service name from docker-compose

**Option 2: Container IP**
```json
{
  "url": "http://172.20.0.X:8000/sse"
}
```
- IP changes on container restart
- Not recommended

**Option 3: Host networking**
```yaml
network_mode: "host"
```
- Bypasses Docker networking
- Less isolation but simpler

## Debugging Network Issues

### Check what Node.js resolves localhost to:
```bash
node -e "const dns = require('dns'); dns.lookup('localhost', (err, addr, fam) => console.log('Address:', addr, 'Family:', fam));"
```

### Check what server is listening on:
```bash
netstat -tlnp | grep :8000
# Should show :::8000 for IPv6 wildcard
```

### Test Node.js fetch directly:
```bash
node -e "fetch('http://localhost:8000/sse').then(r => console.log('Status:', r.status)).catch(e => console.log('Error:', e.message))"
```

## GitHub Issue Template

Title: MCP server container networking for multi-container deployment

**Context:**
MCP server currently runs in same container as Claude Code. When moved to separate container for production, networking configuration will need updates.

**Requirements:**
- MCP server in dedicated container
- Accessible from Claude Code container
- IPv6 support maintained
- Docker Compose service discovery

**Considerations:**
- Container DNS resolution
- Network bridge configuration
- Health checks
- Port exposure

**Related Files:**
- `magenta/conversations/management/commands/run_mcp_server.py`
- `magenta/docker-compose.services.yml` (when created)
- `.mcp.json` configuration

Block: TBD (create when ready to deploy to separate container)
