#!/bin/bash
# Safe Restore Wrapper Script
# Menggunakan backup_supabase_safe.py untuk restore dengan safety features

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
    echo "Available backups:"
    python backup_supabase.py --list | head -20
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "backups/$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: backups/$BACKUP_FILE"
    echo ""
    echo "Available backups:"
    python backup_supabase.py --list | head -20
    exit 1
fi

echo "🛡️  Starting Safe Restore..."
echo "   Backup file: $BACKUP_FILE"
echo ""

# Run safe restore
python backup_supabase_safe.py --restore "$BACKUP_FILE"

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

