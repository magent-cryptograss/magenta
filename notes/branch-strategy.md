# Branch Strategy

## arthel (cryptograss/justinholmes.com)

**Repos:**
- `cryptograss/justinholmes.com` - upstream, canonical
- `jMyles/arthel` - Justin's fork
- `magent-cryptograss/arthel` - magent's fork

**Branches:**
- `main` on cryptograss - PRs target here
- `production` on cryptograss - dead-end deployment branch

**Workflow:**
1. PRs go to cryptograss/main
2. After merge, reset production to main: `git push origin main:production --force`
3. Jenkins builds from production branch
4. Never merge FROM production - it's a dead end

## magenta (magent-cryptograss/magenta)

**Branches:**
- `multi-user-hunter-deployment` - active development
- `production` - deployed to hunter VPS

**Workflow:**
1. Develop on `multi-user-hunter-deployment`
2. Push to production: `git push origin multi-user-hunter-deployment:production --force`
3. Hunter Dockerfile clones `production` branch during image build

**Key config locations:**
- `hunter/Dockerfile:87` - `ARG MAGENTA_BRANCH=production`
- `hunter/ansible/roles/build-image/tasks/main.yml:6` - `version: production`

## maybelle-config (cryptograss/maybelle-config)

**Branches:**
- `main` - canonical
- `production` - deployed to maybelle VPS

**Workflow:**
- PRs to main
- Reset production to main for deployment
- Ansible playbook runs from `/root/maybelle-config` on the VPS

## General Notes

- The `git push origin source:dest --force` pattern is clean for dead-end deployment branches
- Always verify which branch Jenkins/ansible expects before pushing
- production branches are ephemeral - never merge out of them
