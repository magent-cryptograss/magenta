# Security Issues to Address Before Production

## Secrets Management
- [ ] **Django SECRET_KEY** - Currently using insecure default key in settings.py
  - Solution: Use environment variable
  - File: `memory_viewer/settings.py`
  - Example: `SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-...')`

- [ ] **PostgreSQL password** - Currently hardcoded as "cryptograss" in inventory.yml
  - Solution: Use Ansible Vault
  - File: `ansible/inventory.yml`

- [ ] **Code-server passwords** - Currently using default passwords in inventory
  - Solution: Create ansible-vault file with secure passwords
  - Command: `ansible-vault create ansible/vault.yml`
  - Add: `vault_justin_password`, `vault_rj_password`, `vault_skyler_password`

- [ ] **SSH public keys** - Currently placeholder keys in inventory
  - Action: Replace with actual team member public keys
  - File: `ansible/inventory.yml` lines 24, 33, 42

- [ ] **GitHub Personal Access Tokens** - Required for gh CLI authentication
  - Solution: Create PATs for each user, store in Ansible Vault
  - Permissions needed: `repo`, `read:org`, `gist`, `workflow`
  - Add to vault: `vault_justin_github_token`, `vault_rj_github_token`, etc.
  - Set as `GH_TOKEN` environment variable in containers

## Access Control
- [ ] **Docker socket mounting** - Gives containers root-equivalent access to host
  - Current: Mounting `/var/run/docker.sock` for Puppeteer MCP
  - Risk: Container escape = full host access
  - Mitigation options:
    1. Accept risk (isolated VPS)
    2. Use rootless Docker
    3. Implement socket proxy with access controls

## Network Security
- [ ] **Port exposure** - Many ports exposed per user
  - Review which ports need to be public vs internal only
  - Consider firewall rules / security groups

## Database Security
- [ ] **Shared database access** - All user containers access same DB
  - Need to ensure proper row-level security with `from`/`to` columns
  - Consider PostgreSQL row-level security policies

## Future Considerations
- [ ] Secrets rotation strategy
- [ ] Audit logging for database access
- [ ] Rate limiting on exposed ports
- [ ] SSL/TLS for web endpoints
- [ ] Backup encryption

---
**Note**: This is a development environment, not production. Security requirements may vary based on sensitivity of data and use case.
