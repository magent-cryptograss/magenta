# Ansible Vault Setup

The vault stores sensitive passwords for PostgreSQL and code-server.

## Creating the Vault

```bash
cd ansible
ansible-vault create vault.yml
```

You'll be prompted for a vault password. **Remember this password** - you'll need it every time you run the playbook.

## Vault Contents

Add this content when creating the vault:

```yaml
---
# PostgreSQL password for shared database
vault_postgres_password: "your-secure-postgres-password-here"

# Code-server password for Justin
vault_justin_password: "your-secure-code-server-password-here"
```

Generate secure passwords with:
```bash
openssl rand -base64 32
```

## Running the Playbook with Vault

```bash
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

Or create a password file (NOT recommended for production):
```bash
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass
ansible-playbook -i inventory.yml playbook.yml --vault-password-file .vault_pass
```

## Editing the Vault

```bash
ansible-vault edit vault.yml
```

## Viewing Vault Contents

```bash
ansible-vault view vault.yml
```

## Adding More Users Later

When adding RJ or Skyler, edit the vault to add their passwords:

```bash
ansible-vault edit vault.yml
```

Add:
```yaml
vault_rj_password: "rj-secure-password"
vault_skyler_password: "skyler-secure-password"
```

Then uncomment their entries in `inventory.yml`.
