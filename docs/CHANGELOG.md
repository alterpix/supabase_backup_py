# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0] - 2025-11-28

### Added
- ✅ All-in-one integrated script (`supabase_backup.py`)
- ✅ Multithreading support for optimized backup/restore
- ✅ Compression support (gzip)
- ✅ Progress bar with tqdm
- ✅ Unified CLI with subcommands
- ✅ Smart comparison backup - only backup changed tables
- ✅ Incremental backup support
- ✅ Safety backup before restore operations
- ✅ Rollback mechanism for failed restores
- ✅ Data validation before restore
- ✅ Automatic verification after restore
- ✅ Comprehensive logging and restore logs
- ✅ Support for generated columns and identity columns
- ✅ Auto cleanup of old backups (keep 288 latest)
- ✅ Interactive restore with timeline selection

### Changed
- 🔄 Merged all backup/restore features into single `supabase_backup.py` file
- 🔄 Updated CLI to use subcommands (backup, restore, list, rollback)
- 🔄 Updated all documentation to English
- 🔄 Improved performance with multithreading (3-5x faster)

### Removed
- ❌ `backup_supabase.py` - Merged into `supabase_backup.py`
- ❌ `backup_supabase_safe.py` - Merged into `supabase_backup.py`
- ❌ `restore_backup.py` - Merged into `supabase_backup.py`
- ❌ Redundant documentation files

### Features
- **Smart Backup**: Compares current data with previous backup, only backs up changed tables
- **Incremental Backup**: References previous backup for unchanged tables, saves storage
- **Optimized Backup**: Multithreading support for 3-5x faster backups
- **Optimized Restore**: Parallel batch processing for 2-3x faster restores
- **Compression**: Gzip compression reduces file size by 70-80%
- **Safety Features**: Automatic safety backup before restore, easy rollback
- **Error Handling**: Handles generated columns, identity columns, and duplicate keys
- **Logging**: Detailed logs for all operations, restore verification

### Documentation
- Complete README with examples
- Installation guide
- Safety features documentation
- Troubleshooting guide
- Usage examples
- All documentation translated to English

### Files
- `supabase_backup.py` - Main all-in-one script with all features
- `restore_safe.sh` - Wrapper script for safe restore
- `run_backup.sh` - Cron job script

## [1.0.0] - 2025-11-28

### Added
- Initial release with smart backup and safety features

## Future Improvements

- [ ] Web dashboard for backup management
- [ ] Email notifications for backup failures
- [ ] Backup encryption
- [ ] Cloud storage integration (S3, Google Cloud)
- [ ] Scheduled restore operations
- [ ] Multi-database support
- [ ] Async/await for better I/O performance
- [ ] Connection pooling for Supabase client
