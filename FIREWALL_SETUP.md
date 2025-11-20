# Firewall and Network Security Setup for Hunter

## Required Ports

### PostgreSQL Database (5432)
**Purpose**: Allow ai-sandbox and user containers to connect to shared database

**Hetzner Cloud Firewall Rule**:
```
Type: TCP
Port: 5432
Source: Your laptop IP (for ai-sandbox) + hunter's internal network
```

**Using Hetzner CLI**:
```bash
# Create firewall rule for postgres
hcloud firewall create --name magenta-services

# Allow postgres from specific IP (your laptop for ai-sandbox)
hcloud firewall add-rule magenta-services \
  --direction in \
  --protocol tcp \
  --port 5432 \
  --source-ips YOUR_LAPTOP_IP/32

# Allow postgres from internal docker network
hcloud firewall add-rule magenta-services \
  --direction in \
  --protocol tcp \
  --port 5432 \
  --source-ips 172.17.0.0/16

# Apply to hunter server
hcloud firewall apply-to-resource magenta-services \
  --type server \
  --server hunter
```

**Using Hetzner Web Console**:
1. Go to Cloud Console → Firewalls
2. Create new firewall "magenta-services"
3. Add inbound rule:
   - Protocol: TCP
   - Port: 5432
   - Source: Your laptop IP (check with `curl ifconfig.me`)
4. Attach to hunter server

### Memory Lane Web UI (3000)
**Purpose**: Access Memory Lane viewer from browser

**Rule**:
```
Type: TCP
Port: 3000
Source: 0.0.0.0/0 (public) OR specific IPs (more secure)
```

### SSH (22)
**Purpose**: SSH access to user containers via router

**Rule** (should already exist):
```
Type: TCP
Port: 22
Source: 0.0.0.0/0 (or your specific IPs)
```

### HTTP/HTTPS (80/443)
**Purpose**: Caddy reverse proxy for subdomains

**Rules** (should already exist):
```
Type: TCP
Port: 80, 443
Source: 0.0.0.0/0
```

## Security Considerations

### PostgreSQL Access
**Current setup**: Database exposed on port 5432 with password auth

**Recommendations**:
- [ ] Use strong password in `.env` file
- [ ] Restrict to known IPs only (laptop, trusted networks)
- [ ] Consider VPN for database access instead of public internet
- [ ] Enable SSL for postgres connections
- [ ] Set up `pg_hba.conf` with IP-based auth rules

### Memory Lane UI Access
**Current setup**: Public web server on port 3000

**Recommendations**:
- [ ] Add HTTP Basic Auth via Caddy
- [ ] Use Caddy's automatic HTTPS
- [ ] Set `ALLOWED_HOSTS` in Django settings
- [ ] Consider VPN or IP whitelist

## Testing Connectivity

### From ai-sandbox to hunter postgres:
```bash
# Test connection
psql -h hunter.cryptograss.live -U magent -d cryptograss_memory

# Or with IP
psql -h 5.78.83.4 -U magent -d cryptograss_memory
```

### Check if port is accessible:
```bash
# From your laptop
nc -zv hunter.cryptograss.live 5432

# From ai-sandbox container
nc -zv 5.78.83.4 5432
```

## Current Hunter IP
- **Hostname**: hunter.cryptograss.live
- **IP**: 5.78.83.4 (verify with `dig hunter.cryptograss.live`)

## Docker Network
Containers on hunter use bridge network (typically 172.17.0.0/16). Services can reach each other via container names when in same docker-compose.
