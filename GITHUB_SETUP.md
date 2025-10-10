# GitHub Authentication Setup

## For Local Development

### Option 1: Web-based flow (recommended for humans)

```bash
gh auth login --web
```

Follow the prompts to authenticate via browser.

### Option 2: Token-based flow (for automation)

1. Create a Personal Access Token (classic) at https://github.com/settings/tokens
2. Required permissions: `repo`, `read:org`, `gist`, `workflow`
3. Authenticate:
   ```bash
   echo "YOUR_TOKEN" | gh auth login --with-token
   ```

### Option 3: Environment variable (recommended for containers)

```bash
export GH_TOKEN=your_token_here
gh auth status  # Should show authenticated
```

## For VPS Deployment (Hunter)

### 1. Create Personal Access Tokens

For each team member:
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Name: `magenta-dev-{username}`
4. Permissions:
   - `repo` - Full control of private repositories
   - `read:org` - Read org and team membership
   - `gist` - Create gists
   - `workflow` - Update GitHub Action workflows
5. Copy the token (you won't see it again!)

### 2. Add Tokens to Ansible Vault

Create or edit `ansible/vault.yml`:

```bash
cd ansible
ansible-vault create vault.yml
# Or if it exists:
ansible-vault edit vault.yml
```

Add token variables:

```yaml
# GitHub Personal Access Tokens for gh CLI
vault_justin_github_token: "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
vault_rj_github_token: "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
vault_skyler_github_token: "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Django secret keys (generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
vault_justin_django_secret_key: "django-secret-key-here"
vault_rj_django_secret_key: "django-secret-key-here"
vault_skyler_django_secret_key: "django-secret-key-here"
```

### 3. Update Inventory

In `ansible/inventory.yml`, reference vault variables:

```yaml
users:
  - name: justin
    full_name: "Justin Holmes"
    email: "justin@cryptograss.live"
    github_username: "jMyles"
    github_token: "{{ vault_justin_github_token }}"
    django_secret_key: "{{ vault_justin_django_secret_key }}"
    # ... other fields ...
```

### 4. Deploy

The playbook will automatically:
1. Set `GH_TOKEN` environment variable in each container
2. Set `DJANGO_SECRET_KEY` for Django app
3. Configure `gh` CLI to use the token

Test authentication after deployment:
```bash
ssh sshrouter@hunter.cryptograss.live
gh auth status
```

## Verifying Authentication

```bash
# Check auth status
gh auth status

# Test with a simple command
gh repo list --limit 5

# Check token permissions
gh api user
```

## Token Security

- ✅ DO store tokens in Ansible Vault (encrypted)
- ✅ DO set appropriate permissions (least privilege)
- ✅ DO rotate tokens periodically
- ✅ DO use separate tokens per user
- ❌ DON'T commit tokens to git
- ❌ DON'T share tokens between users
- ❌ DON'T use tokens with more permissions than needed

## Troubleshooting

### "You are not logged into any GitHub hosts"

Token not set or invalid. Check:
```bash
echo $GH_TOKEN
gh auth status
```

### "Bad credentials"

Token expired or revoked. Generate new token and update vault.

### "Resource not accessible by personal access token"

Token doesn't have required permissions. Regenerate with correct scopes.

## SSH Keys for Git Operations

The `gh auth login` flow can also upload SSH keys for git operations. For VPS deployment:

1. Each user's SSH key is already mounted at `/home/magent/.ssh/`
2. Ensure the key is registered with GitHub: https://github.com/settings/keys
3. Configure git to use SSH:
   ```bash
   git config --global url."git@github.com:".insteadOf "https://github.com/"
   ```

This is already configured in the container startup script.
