#!/bin/bash
# Safe Restore Wrapper Script
# Uses supabase_backup.py for restore with safety features

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Check if backup file provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 supabase_backup_20251128_074723.json"
    echo ""
    echo "Or use interactive mode:"
    echo "  $0 --interactive"
    echo ""
    echo "Available backups:"
    python supabase_backup.py list | head -20
    exit 1
fi

BACKUP_FILE="$1"

# Interactive mode
if [ "$BACKUP_FILE" == "--interactive" ]; then
    echo "🛡️  Starting Interactive Safe Restore..."
    python supabase_backup.py restore --interactive --safe
    exit $?
fi

# Check if backup file exists
if [ ! -f "backups/$BACKUP_FILE" ] && [ ! -f "backups/${BACKUP_FILE}.gz" ]; then
    echo "❌ Backup file not found: backups/$BACKUP_FILE"
    echo ""
    echo "Available backups:"
    python supabase_backup.py list | head -20
    exit 1
fi

echo "🛡️  Starting Safe Restore..."
echo "   Backup file: $BACKUP_FILE"
echo ""

# Run safe restore
python supabase_backup.py restore --file "$BACKUP_FILE" --safe

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Restore completed successfully!"
    echo "💡 Check summaries/ for restore log"
else
    echo ""
    echo "❌ Restore failed!"
    echo "💡 Check safety_backups/ for rollback options"
    exit $EXIT_CODE
fi
