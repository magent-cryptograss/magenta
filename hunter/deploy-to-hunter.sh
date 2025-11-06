#!/bin/bash
# Deploy magenta to hunter VPS with up-to-date database backup

set -e  # Exit on any error

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="magenta_memory_${TIMESTAMP}.dump"
CONTAINER_NAME="magenta-postgres-local"
DB_NAME="magenta_memory"
DB_USER="magent"

echo "=== Magenta Hunter Deployment ==="
echo "Timestamp: $TIMESTAMP"
echo ""

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

# Step 3: Deploy to hunter
echo "Step 3: Deploying to hunter VPS..."
echo "Running ansible playbook..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/ansible"
ansible-playbook -v -i inventory.yml playbook.yml -e "db_dump_file=/tmp/$BACKUP_FILE"

echo ""
echo "=== Deployment Complete ==="
echo "Database backup: /tmp/$BACKUP_FILE"
echo "Messages deployed: $MSG_COUNT"
echo ""
echo "Next steps:"
echo "  - SSH to hunter: ssh sshrouter@hunter.cryptograss.live"
echo "  - View Memory Lane: https://justin0.hunter.cryptograss.live"
echo "  - Clean up local backup: rm /tmp/$BACKUP_FILE"
