#!/bin/bash
# Deploy magenta to hunter VPS with up-to-date database backup

set -e  # Exit on any error

# Parse command line arguments
DO_NOT_COPY_DATABASE=false
EXTRA_ANSIBLE_ARGS=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --do-not-copy-database)
      DO_NOT_COPY_DATABASE=true
      shift
      ;;
    --ask-vault-pass)
      EXTRA_ANSIBLE_ARGS="$EXTRA_ANSIBLE_ARGS --ask-vault-pass"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--do-not-copy-database] [--ask-vault-pass]"
      exit 1
      ;;
  esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="magenta_memory_${TIMESTAMP}.dump"
CONTAINER_NAME="magenta-postgres-local"
DB_NAME="magenta_memory"
DB_USER="magent"

echo "=== Magenta Hunter Deployment ==="
echo "Timestamp: $TIMESTAMP"
echo ""

if [ "$DO_NOT_COPY_DATABASE" = true ]; then
  echo "Skipping database backup (--do-not-copy-database flag set)"
  echo "Note: Ansible will skip data migration role"
  echo ""
  ANSIBLE_DB_ARG=""
else
  # Step 1: Create database backup
  echo "Step 1: Creating database backup..."
  docker exec $CONTAINER_NAME pg_dump -U $DB_USER -Fc $DB_NAME > /tmp/$BACKUP_FILE
  BACKUP_SIZE=$(du -h /tmp/$BACKUP_FILE | cut -f1)
  echo "✓ Backup created: /tmp/$BACKUP_FILE ($BACKUP_SIZE)"
  echo ""

  # Step 2: Count messages to verify backup
  echo "Step 2: Verifying backup completeness..."
  MSG_COUNT=$(docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM conversations_message;" | tr -d ' ')
  echo "✓ Database contains $MSG_COUNT messages"
  echo ""

  ANSIBLE_DB_ARG="-e db_dump_file=/tmp/$BACKUP_FILE"
fi

# Step 3: Deploy to hunter
echo "Step 3: Deploying to hunter VPS..."
echo "Running ansible playbook..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/ansible"
ansible-playbook -v -i inventory.yml playbook.yml $ANSIBLE_DB_ARG $EXTRA_ANSIBLE_ARGS

echo ""
echo "=== Deployment Complete ==="
if [ "$DO_NOT_COPY_DATABASE" = false ]; then
  echo "Database backup: /tmp/$BACKUP_FILE"
  echo "Messages deployed: $MSG_COUNT"
fi
echo ""
echo "Next steps:"
echo "  - SSH to hunter: ssh sshrouter@hunter.cryptograss.live"
echo "  - View Memory Lane: https://justin0.hunter.cryptograss.live"
if [ "$DO_NOT_COPY_DATABASE" = false ]; then
  echo "  - Clean up local backup: rm /tmp/$BACKUP_FILE"
fi
