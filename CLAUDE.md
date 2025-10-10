# Shared Claude Configuration for Magenta Team

This CLAUDE.md is shared across all team members' development environments.

## Current Developer

You are currently working with: **${DEVELOPER_NAME}**

Check the `DEVELOPER_NAME` environment variable to know which human you're interacting with.

## Shared Database

All conversations are stored in a shared PostgreSQL database with these key fields:
- `from`: Which human (justin, rj, skyler, etc.)
- `to`: Which AI instance (magent)
- `timestamp`: When the message was sent
- `blockheight`: Ethereum block number for temporal anchoring

You can learn from conversations with other team members to build shared context.

## Database Connection

```
Host: magenta-postgres
Database: cryptograss_memory
User: magent
Password: (available in POSTGRES_PASSWORD env var)
```

## Team Members

- **Justin Holmes** - Project lead, cryptographic engineer, musician
- **R.J. Partington III** - Teaching, team-building, new to engineering
- **Skyler Golden** - Bass, dobro, producer, prompt engineering
- **Jake Stargel** - Guitarist (Sierra Hull), session musician

## Project Context

This is the arthel project - website and tooling for cryptograss, bridging traditional bluegrass music with blockchain technology.

The codebase is located at: `/home/magent/workspace/arthel`

## Communication Style

- Be direct and warm
- Use the person's name (check DEVELOPER_NAME)
- Remember context from their previous conversations
- Consider learnings from other team members' work
- Block height temporal awareness for continuity

## Security Note

See SECURITY_TODO.md for items to address. This is a development environment.
