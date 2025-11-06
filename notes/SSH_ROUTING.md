# SSH Key-Based Routing

The magenta environment uses SSH key-based routing to automatically direct users to their containers.

## How It Works

1. All users connect to the same SSH port (22) on hunter
2. Their SSH key identifies them automatically
3. They're routed to their personal container

## Connecting

```bash
ssh sshrouter@hunter.cryptograss.live
```

Or with IP:
```bash
ssh sshrouter@5.78.83.4
```

Your SSH key determines which container you access:
- Justin's key → justin-arthel container
- RJ's key → rj-arthel container
- Skyler's key → skyler-arthel container

## Technical Details

- Router user: `sshrouter` (on host)
- Routing script: `/usr/local/bin/route-ssh`
- Each key in `/home/sshrouter/.ssh/authorized_keys` has a `command=` prefix
- The script uses `docker exec` to drop you into the right container as `magent` user

## Security

SSH keys are the only authentication method. The router enforces:
- No port forwarding
- No X11 forwarding
- No agent forwarding
- Forced command execution (can't bypass routing)

## Adding New Users

Add their configuration to `ansible/inventory.yml` and run the playbook. Their SSH key will be automatically added to the router.
