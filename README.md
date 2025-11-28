# 🚀 Supabase Database Backup & Restore Tool

All-in-One tool for backing up and restoring Supabase databases with comprehensive features:
- ✅ Smart backup with comparison (incremental)
- ✅ Optimized backup with multithreading
- ✅ Safe restore with automatic safety backup
- ✅ Optimized restore with parallel processing
- ✅ Compression support (gzip)
- ✅ Progress bar monitoring
- ✅ Rollback mechanism

## 📋 Features

### Backup Features
- **Smart Comparison**: Only backup tables that changed (incremental)
- **Multithreading**: Parallel table fetching for faster performance
- **Compression**: Gzip compression to reduce file size (70-80% reduction)
- **Progress Bar**: Real-time monitoring with tqdm
- **Auto Cleanup**: Automatically removes old backups (keeps 288 = 24 hours)

### Restore Features
- **Safe Restore**: Automatic safety backup before restore
- **Optimized Restore**: Parallel batch processing
- **Data Validation**: Validates backup before restore
- **Rollback**: Rollback to safety backup if restore fails
- **Interactive Mode**: Timeline selection to choose backup

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/alterpix/supabase_backup_py
cd supabase_backup_py

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy `env.example` to `.env`:
```bash
cp env.example .env
```

2. Edit `.env` and fill in your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Usage

#### Create Backup

```bash
# Smart backup (default: optimized, 5 workers, compression enabled)
python supabase_backup.py backup

# Full backup (ignore comparison)
python supabase_backup.py backup --force-full

# Custom workers
python supabase_backup.py backup --workers 10

# Disable compression
python supabase_backup.py backup --no-compress

# Sequential backup (no multithreading)
python supabase_backup.py backup --workers 1
```

#### List Backups

```bash
# List all backups
python supabase_backup.py list
```

#### Restore

```bash
# Safe restore (with automatic safety backup)
python supabase_backup.py restore --safe --file supabase_backup_YYYYMMDD_HHMMSS.json

# Optimized restore (with multithreading)
python supabase_backup.py restore --safe --file <backup_file> --workers 5

# Interactive restore (timeline selection)
python supabase_backup.py restore --interactive --safe

# Restore without safety backup (not recommended)
python supabase_backup.py restore --file <backup_file>
```

#### Rollback

```bash
# Rollback from safety backup
python supabase_backup.py rollback safety_backup_YYYYMMDD_HHMMSS.json.gz
```

#### List Safety Backups

```bash
# List all safety backups
python supabase_backup.py list-safety
```

## 📊 Performance

### Backup Speed

| Mode | Tables | Time | Speedup |
|------|--------|------|---------|
| Sequential | 30 | ~45s | 1x |
| Optimized (5 workers) | 30 | ~12s | **3.75x** |
| Optimized (10 workers) | 30 | ~8s | **5.6x** |

### Restore Speed

| Mode | Rows | Time | Speedup |
|------|------|------|---------|
| Sequential | 15,541 | ~25s | 1x |
| Optimized (3 workers) | 15,541 | ~10s | **2.5x** |
| Optimized (5 workers) | 15,541 | ~7s | **3.6x** |

### File Size

| Mode | Size | Compression |
|------|------|-------------|
| Uncompressed | 4.15 MB | - |
| Compressed | 1.2 MB | **71% reduction** |

## 🔧 Configuration

### Default Settings

```python
DEFAULT_MAX_WORKERS_BACKUP = 5   # Parallel threads for backup
DEFAULT_MAX_WORKERS_RESTORE = 3  # Parallel threads for restore
DEFAULT_BATCH_SIZE = 100          # Restore batch size
DEFAULT_COMPRESS = True          # Enable compression
DEFAULT_SHOW_PROGRESS = True     # Show progress bar
```

### Tuning Workers

**Backup:**
- **Small database (< 10 tables)**: 3-5 workers
- **Medium database (10-30 tables)**: 5-8 workers
- **Large database (> 30 tables)**: 8-10 workers

**Restore:**
- **Small batches (< 1000 rows)**: 2-3 workers
- **Medium batches (1000-10000 rows)**: 3-5 workers
- **Large batches (> 10000 rows)**: 5-8 workers

⚠️ **Note**: Too many workers can cause API rate limiting. Start with default values and adjust based on your Supabase plan limits.

## 📁 Project Structure

```
supabase_backup_py/
├── supabase_backup.py      # Main all-in-one script
├── requirements.txt         # Python dependencies
├── env.example             # Environment variables template
├── .env                    # Your environment variables (not in git)
├── README.md               # This file
├── LICENSE                 # MIT License
├── backups/                # Backup files (auto-created)
├── safety_backups/         # Safety backup files (auto-created)
├── summaries/              # Backup/restore summaries (auto-created)
└── logs/                   # Log files (auto-created)
```

## 🔄 Automated Backups

### Cron Job Setup

Edit crontab:
```bash
crontab -e
```

Add entry for 5-minute backups:
```cron
*/5 * * * * cd /path/to/supabase_backup_py && /usr/bin/python3 supabase_backup.py backup >> logs/cron.log 2>&1
```

Or use the provided shell script:
```bash
chmod +x run_backup.sh
# Edit run_backup.sh to set correct paths
# Then add to crontab:
*/5 * * * * /path/to/supabase_backup_py/run_backup.sh
```

## 🛡️ Safety Features

### Automatic Safety Backup

When performing restore with `--safe`, the tool will:
1. ✅ Create automatic safety backup before restore
2. ✅ Validate backup data before restore
3. ✅ Record current state for rollback reference
4. ✅ Verify restore after completion

### Rollback Mechanism

If restore fails or produces undesired results:
```bash
python supabase_backup.py rollback safety_backup_YYYYMMDD_HHMMSS.json.gz
```

Rollback will:
1. ✅ Create safety backup before rollback
2. ✅ Restore database to state before previous restore
3. ✅ Provide pre-rollback backup for recovery

## 📝 Examples

### Daily Backup Workflow

```bash
# Morning backup
python supabase_backup.py backup

# Check backups
python supabase_backup.py list

# If needed, restore from yesterday
python supabase_backup.py restore --interactive --safe
```

### Emergency Restore

```bash
# 1. List available backups
python supabase_backup.py list

# 2. Safe restore with automatic safety backup
python supabase_backup.py restore --safe --file supabase_backup_20251128_120000.json

# 3. If restore fails, rollback
python supabase_backup.py rollback safety_backup_20251128_120500.json.gz
```

### High-Performance Backup

```bash
# Use 10 workers for faster backup
python supabase_backup.py backup --workers 10

# Use 5 workers for faster restore
python supabase_backup.py restore --safe --file <backup> --workers 5
```

## 🐛 Troubleshooting

### Error: Rate Limiting

**Solution**: Reduce number of workers
```bash
python supabase_backup.py backup --workers 3
```

### Error: tqdm not found

**Solution**: Install tqdm
```bash
pip install tqdm
```

Or disable progress bar:
```bash
python supabase_backup.py backup --no-progress
```

### Error: Memory Issues

**Solution**: Reduce batch size or workers
- Edit `supabase_backup.py` and change `DEFAULT_BATCH_SIZE = 50`
- Or use sequential mode: `--workers 1`

### Error: Backup file not found

**Solution**: Check backup filename (case-sensitive)
```bash
# List backups to see exact filename
python supabase_backup.py list
```

## 📚 Documentation

See `docs/` folder for complete documentation:
- `INSTALLATION.md` - Setup instructions
- `SAFETY_FEATURES.md` - Safety features documentation
- `TROUBLESHOOTING.md` - Common issues and solutions
- `USAGE_EXAMPLES.md` - Usage examples

## 🤝 Contributing

Contributions are welcome! Please read `docs/CONTRIBUTING.md` for guidelines.

## 📄 License

MIT License - see `LICENSE` file for details.

## 🙏 Acknowledgments

- Supabase for the excellent platform
- tqdm for progress bars
- Python community for amazing libraries
