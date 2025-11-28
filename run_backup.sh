#!/bin/bash
# Script untuk menjalankan backup via cron job
# Usage: Add to crontab for automated backups

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: Virtual environment not found!" >> logs/backup.log 2>&1
    exit 1
fi

# Run backup
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting backup..." >> logs/backup.log
python supabase_backup.py backup >> logs/backup.log 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed successfully" >> logs/backup.log
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup failed with exit code $EXIT_CODE" >> logs/backup.log
fi

exit $EXIT_CODE
