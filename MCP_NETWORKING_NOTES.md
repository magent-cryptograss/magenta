# MCP Server Networking Notes

## IPv6 Requirement (CRITICAL)

The MCP server MUST listen on IPv6 (`::`) not just IPv4 (`0.0.0.0`) because:

- Node.js `fetch()` (used by Claude Code) resolves `localhost` to `::1` (IPv6)
- If server only listens on IPv4, Node.js fetch fails with "fetch failed"
- `curl` works because it tries both IPv4 and IPv6, falling back gracefully

**Current Solution:**
```python
config = uvicorn.Config(
    app,
    host="::",  # Listen on both IPv4 and IPv6
    port=8000,
    log_level="info"
)
```

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
