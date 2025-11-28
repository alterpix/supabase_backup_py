# Usage Examples

## 📚 Common Use Cases

### Example 1: Initial Setup and First Backup

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure .env
cp env.example .env
nano .env  # Add your Supabase credentials

# 3. Create first backup (full backup)
python backup_supabase.py --force-full

# 4. Verify backup
python backup_supabase.py --list
```

### Example 2: Automated Daily Backups

```bash
# Setup cron job for backup every 5 minutes
crontab -e

# Add this line:
*/5 * * * * /path/to/backup_release/run_backup.sh
```

### Example 3: Restore After Accidental Deletion

```bash
# 1. List available backups
python backup_supabase.py --list

# 2. Safe restore (creates safety backup automatically)
python backup_supabase_safe.py --restore supabase_backup_20251128_074723.json

# 3. Verify restore was successful
cat summaries/restore_log_*.json | grep -A 5 "tables_restored"

# 4. If something went wrong, rollback
python backup_supabase_safe.py --rollback safety_backup_20251128_074820.json
```

### Example 4: Compare Data Changes

```bash
# Before making changes
python backup_supabase.py

# Make changes to database...

# After changes
python backup_supabase.py

# Check comparison (if changes detected)
cat summaries/comparison_*.json
```

### Example 5: Restore Specific Table Only

Currently, restore restores all tables. For table-specific restore, you can:

1. Extract specific table from backup JSON
2. Use Supabase dashboard to import manually
3. Or modify restore script to accept table filter (future feature)

### Example 6: Backup Before Migration

```bash
# Before running database migration
python backup_supabase.py --force-full

# Run migration...

# If migration fails, restore
python backup_supabase_safe.py --restore supabase_backup_YYYYMMDD_HHMMSS.json
```

## 🔄 Workflow Examples

### Daily Backup Workflow

```bash
# Morning: Full backup
python backup_supabase.py --force-full

# Throughout day: Incremental backups (via cron)
# Every 5 minutes automatically

# Evening: Verify backups
python backup_supabase.py --list
```

### Disaster Recovery Workflow

```bash
# 1. Identify the issue
# 2. List available backups
python backup_supabase.py --list

# 3. Choose backup from before the issue
# 4. Safe restore
python backup_supabase_safe.py --restore supabase_backup_YYYYMMDD_HHMMSS.json

# 5. Verify data
# 6. Test application
# 7. If OK, keep. If not, rollback and try different backup
```

### Testing Restore Process

```bash
# 1. Create test backup
python backup_supabase.py

# 2. Make test changes (delete a row)
# 3. Create another backup
python backup_supabase.py

# 4. Restore from first backup
python backup_supabase_safe.py --restore supabase_backup_YYYYMMDD_HHMMSS.json

# 5. Verify deleted row is back
```

## 💡 Tips

1. **Always use safe restore for production**
   ```bash
   python backup_supabase_safe.py --restore <backup>
   ```

2. **Keep safety backups until verified**
   - Don't delete safety backups immediately
   - Verify restore was successful first

3. **Regular full backups**
   - Do full backup daily or weekly
   - Incremental backups are fine for frequent intervals

4. **Monitor disk space**
   - Backups can take significant space
   - Cleanup old backups if needed (default: keeps 288)

5. **Test restore process**
   - Test restore in development first
   - Verify you can rollback if needed

