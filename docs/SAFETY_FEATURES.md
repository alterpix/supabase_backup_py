# Safety Features - Backup & Restore

## 🛡️ Safety Features

The backup program is now equipped with safety features to prevent data corruption:

### 1. **Automatic Safety Backup**
- ✅ Creates automatic backup before restore
- ✅ Saved in `safety_backups/` folder
- ✅ Can be used for rollback if restore fails

### 2. **Data Validation**
- ✅ Validates backup structure before restore
- ✅ Checks critical tables (users, packages, bookings)
- ✅ Detects corrupted or invalid data

### 3. **Rollback Mechanism**
- ✅ Automatic rollback if restore fails
- ✅ Restores database to state before restore
- ✅ Safety backup before rollback (double safety)

### 4. **Tracking & Logging**
- ✅ Records state before and after restore
- ✅ Detailed logs for each table
- ✅ Verifies row counts after restore

## 📋 Usage

### Safe Restore (Recommended)

```bash
cd /path/to/supabase_backup_py
source venv/bin/activate  # If using virtual environment

# Restore with automatic safety backup
python supabase_backup.py restore --safe --file supabase_backup_20251128_074723.json
```

**Process flow:**
1. 🛡️ Create safety backup (snapshot current state)
2. 🔍 Validate backup data
3. 📊 Record state before restore
4. 🔄 Restore data
5. ✅ Verify restore results
6. 💾 Save restore log

### Rollback from Safety Backup

If restore fails or there are issues:

```bash
# List safety backups
python supabase_backup.py list-safety

# Rollback to state before restore
python supabase_backup.py rollback safety_backup_20251128_074820.json.gz
```

### Standard Restore (Without Safety Backup)

```bash
# Not recommended for production
python supabase_backup.py restore --file <backup_file>
```

## 📁 File Structure

```
supabase_backup_py/
├── backups/              # Backup files
├── safety_backups/      # Safety backups (pre-restore snapshots)
├── summaries/           # Restore logs and summaries
├── logs/               # Log files
└── supabase_backup.py  # Main script with all features
```

## 🔄 Restore Flow with Safety

```
1. User requests restore
   ↓
2. [SAFETY] Create backup of current state → safety_backups/
   ↓
3. [VALIDATE] Validate backup data
   ↓
4. [RECORD] Record state before restore (row counts)
   ↓
5. [RESTORE] Restore data with UPSERT
   ↓
6. [VERIFY] Verify restore results
   ↓
7. [LOG] Save restore log
   ↓
8. ✅ Complete or ❌ Rollback if failed
```

## 🆘 Recovery Scenarios

### Scenario 1: Restore Failed

```bash
# Restore failed, safety backup available
python supabase_backup.py rollback safety_backup_20251128_074820.json.gz
```

### Scenario 2: Data Mismatch After Restore

```bash
# Check restore log
cat summaries/restore_log_*.json

# Rollback if needed
python supabase_backup.py rollback safety_backup_20251128_074820.json.gz
```

### Scenario 3: Partial Restore Failure

The program will:
- ✅ Restore successful tables
- ⚠️ Log failed tables
- 💾 Keep safety backup available for manual rollback

## ⚠️ Best Practices

1. **Always use safe restore for production**
   ```bash
   python supabase_backup.py restore --safe --file <backup_file>
   ```

2. **Don't skip safety backup** (except for testing)
   - Safety backup is the last safety net

3. **Verify after restore**
   - Check restore log in `summaries/`
   - Compare row counts before/after

4. **Keep safety backups**
   - Don't delete safety backups until restore is verified
   - Safety backups can be cleaned up after 7 days

## 📊 Restore Log Format

```json
{
  "started_at": "2025-11-28T07:48:20",
  "backup_file": "supabase_backup_20251128_074723.json",
  "safety_backup_file": "safety_backup_20251128_074820.json",
  "before_counts": {
    "bookings": 53,
    "users": 43
  },
  "after_counts": {
    "bookings": 53,
    "users": 43
  },
  "tables_restored": {
    "bookings": {
      "inserted": 0,
      "updated": 53,
      "errors": 0
    }
  },
  "tables_failed": [],
  "total_inserted": 3,
  "total_updated": 15538,
  "total_errors": 0
}
```

## 🔧 Advanced Usage

### Skip Safety Backup (Not Recommended)

```bash
# Only for testing, don't use in production!
python supabase_backup.py restore --file <backup>
```

### List Safety Backups

```bash
python supabase_backup.py list-safety
```

## 💡 Tips

- ✅ **Automatic safety backup** - No need to manually backup before restore
- ✅ **Easy rollback** - Single command to rollback
- ✅ **Complete logging** - All operations are logged
- ✅ **Data validation** - Detect issues before restore
- ✅ **Automatic verification** - Check results after restore
