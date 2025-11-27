# Build-Once Architecture

## Overview

Instead of building a separate Docker image for each user, we build **one shared base image** that all user containers run from. This dramatically speeds up deployment and ensures consistency.

## How It Works

### 1. Build Phase (Once)
```bash
docker-compose -f docker-compose-build.yml build
```

This creates `magenta-arthel:latest` with:
- All system packages installed
- Node.js dependencies for arthel pre-installed
- Arthel repository cloned into `/home/magent/workspace/arthel`
- All tools (Docker CLI, gh CLI, code-server, etc.) ready to go

### 2. Run Phase (Per User)

Each user gets a container from the same image, with:
- **Different ports** mapped to host
- **Different volumes** for .claude and .ssh
- **Environment variables** to identify the user (`DEVELOPER_NAME`)
- **Same codebase** (arthel repo is baked into the image)

## Benefits

✅ **Fast deployment**: Build takes ~5 minutes once, not 5 minutes × N users
✅ **Consistency**: Everyone runs identical environments
✅ **Easy updates**: Rebuild image once, restart all containers
✅ **No host dependencies**: No `/home/jmyles/` paths or local mounts needed

## File Structure on VPS

```
/opt/magenta/
├── magenta-source/          # Source files for building image
│   ├── Dockerfile
│   ├── container-startup.sh
│   ├── packages.txt
│   └── docker-compose-build.yml
├── postgres-data/           # Shared PostgreSQL data
├── justin/
│   ├── .claude/            # Justin's Claude config
│   ├── .ssh/               # Justin's SSH keys
│   └── docker-compose.yml  # References magenta-arthel:latest
├── rj/
│   ├── .claude/
│   ├── .ssh/
│   └── docker-compose.yml
└── skyler/
    ├── .claude/
    ├── .ssh/
    └── docker-compose.yml
```

## Updating the Environment

### Update arthel code (in image):
```bash
cd /opt/magenta/magenta-source
# Edit Dockerfile to point to new commit/branch
docker-compose -f docker-compose-build.yml build
# Restart all user containers to pick up new image
docker restart justin-arthel rj-arthel skyler-arthel
```

### Update user-specific config:
```bash
cd /opt/magenta/justin
# Edit .claude/CLAUDE.md or other configs
docker restart justin-arthel
```

## Ansible Workflow

The playbook handles this automatically:

1. **build-image role**: Copies source files, builds `magenta-arthel:latest`
2. **postgres role**: Creates shared database
3. **user-instance role**: For each user, creates directories and starts container from pre-built image

No per-user building needed!
