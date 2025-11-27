# DNS/Subdomain Setup for Hunter

Each user gets 10 subdomains that map to their port range.

## DNS Records Needed

Add these A records to your `cryptograss.live` DNS:

```
justin1.cryptograss.live  → 5.78.83.4:14000
justin2.cryptograss.live  → 5.78.83.4:14001
...
justin10.cryptograss.live → 5.78.83.4:14009

rj1.cryptograss.live      → 5.78.83.4:14010
rj2.cryptograss.live      → 5.78.83.4:14011
...
rj10.cryptograss.live     → 5.78.83.4:14019

skyler1.cryptograss.live  → 5.78.83.4:14020
skyler2.cryptograss.live  → 5.78.83.4:14021
...
skyler10.cryptograss.live → 5.78.83.4:14029
```

## Wildcard Approach (Easier)

Instead of individual records, use wildcard DNS:

```
*.cryptograss.live → 5.78.83.4
```

Then configure nginx/caddy as reverse proxy to route:
- `justin1.cryptograss.live` → `localhost:14000`
- `justin2.cryptograss.live` → `localhost:14001`
- etc.

## Current Status

**Without DNS/reverse proxy:**
- Access directly via IP and port: `http://5.78.83.4:14000`
- SSH: `ssh -p 2222 magent@5.78.83.4`

**With DNS setup:**
- Access via subdomain: `http://justin1.cryptograss.live`
- Cleaner URLs, SSL/TLS possible

## Next Steps

1. Add wildcard DNS record or individual A records
2. Install nginx/caddy on hunter for reverse proxying
3. Set up Let's Encrypt for SSL certificates
4. Update inventory with SSL configuration
