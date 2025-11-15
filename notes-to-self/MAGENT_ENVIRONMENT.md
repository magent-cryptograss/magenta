# Magent's Environment Context

## Where am I running?
You (magent) are running **on hunter** in a Docker container named `justin-arthel` or `rj-arthel`.

You are **NOT** running on:
- Justin's laptop
- A local development machine
- Maybelle

## Git/GitHub Access

### Pushing to GitHub
You use **HTTPS with GitHub CLI token** for authentication, NOT SSH.

The credential helper is configured in container startup, but for manual pushes use:

```bash
git push https://magent-cryptograss:$(gh auth token)@github.com/magent-cryptograss/maybelle-config.git hunter-deploy
```

### Your GitHub Account
- Account: `magent-cryptograss`
- You have a fork of `cryptograss/maybelle-config`
- All your work goes to the `hunter-deploy` branch on your fork
- There's an open PR from your fork to the main repo

### SSH Access Issues
The container filesystem is mostly read-only, so:
- You CANNOT write to `~/.ssh/known_hosts`
- You CANNOT use SSH for git operations
- Always use HTTPS with token authentication

## Docker Socket Access
You have access to the Docker socket at `/var/run/docker.sock`, which means you can:
- Run `docker ps` to see all containers on hunter
- Run `docker exec` to execute commands in other containers
- Inspect and manage containers

Common containers on hunter:
- `justin-arthel` / `rj-arthel` - User development containers (you're in one of these)
- `magenta-postgres` - PostgreSQL database
- `mcp-server` - MCP memory server (port 8000)
- `memory-lane` - Django web interface (port 3000)
- `watcher` - Conversation monitor

## Network Access
- You're on the `magenta-net` Docker network
- You can access other containers by their service names
- You can SSH to maybelle: `ssh root@maybelle.cryptograss.live`
- Maybelle is at `maybelle.cryptograss.live` (5.78.110.78)
- Hunter is at `hunter.cryptograss.live` (5.78.83.4)

## Vault Access
The ansible vault password is available via:
- `ANSIBLE_VAULT_PASSWORD_FILE` environment variable (points to a file)
- Or `ANSIBLE_VAULT_PASSWORD` environment variable (direct password)

You cannot edit the vault directly - it's encrypted. Justin edits it and pushes changes.

## Important Repositories

### On Hunter (in workspace)
- `/home/magent/workspace/maybelle-config` - Deployment configurations
- `/home/magent/workspace/magenta` - Main magenta repo with CLAUDE.md
- `/home/magent/workspace/arthel` - Website build logic

### Remote Repositories
- `cryptograss/maybelle-config` - Main deployment repo (you don't have write access)
- `magent-cryptograss/maybelle-config` - Your fork (you have write access)
- All your commits go to your fork's `hunter-deploy` branch

## GitHub CLI
You're authenticated with `gh` using a token stored in the environment.

Check status: `gh auth status`

The CLI is configured to use HTTPS for git operations.

## Deployment Workflow
1. Make changes in `/home/magent/workspace/maybelle-config`
2. Commit to your local branch
3. Push to your fork: `git push https://magent-cryptograss:$(gh auth token)@github.com/magent-cryptograss/maybelle-config.git hunter-deploy`
4. Justin reviews the PR and merges to production
5. Deployments run from production branch on the main repo

## Common Mistakes to Avoid After Compacting
- ❌ Trying to SSH push (you can't, use HTTPS with token)
- ❌ Trying to write to known_hosts (filesystem is read-only)
- ❌ Forgetting you're on hunter, not on a laptop
- ❌ Trying to push to cryptograss/* repos (you don't have access, use your fork)
- ❌ Using `origin` remote without checking where it points
- ❌ Trying to `git config` globally (filesystem restrictions)

## When in Doubt
- Check where you are: `pwd`, `hostname`, `echo $DEVELOPER_NAME`
- Check git status: `git remote -v`, `git branch`
- Check GitHub auth: `gh auth status`
- Remember: **HTTPS with token, not SSH!**
- The full push command is in this file - just copy it!
