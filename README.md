# 🛡️ Supabase Database Backup & Restore Tool

Automated backup and restore tool for Supabase PostgreSQL database with **Smart Comparison** and **Safety Features**.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ Features

- ✅ **Smart Comparison**: Only backup tables that changed, skip unchanged tables
- ✅ **Incremental Backup**: Reference previous backup for unchanged tables
- ✅ **Safety Backup**: Automatic backup before restore operations
- ✅ **Rollback Mechanism**: Easy rollback if restore fails
- ✅ **Data Validation**: Validate backup data before restore
- ✅ **Auto Cleanup**: Keep only latest 288 backups (24 hours with 5-min intervals)
- ✅ **Error Handling**: Handle generated columns and identity columns
- ✅ **Comprehensive Logging**: Detailed logs for all operations

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Safety Features](#safety-features)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Supabase account with database access
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`

### Setup

1. **Clone or download this repository**

```bash
cd backup_release
```

2. **Create virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create `.env` file:

```bash
cp env.example .env
nano .env
```

Fill in your Supabase credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## 🎯 Quick Start

### Create Backup

```bash
# Activate virtual environment
source venv/bin/activate

# Create backup (smart mode - only changed tables)
python backup_supabase.py

# Force full backup (all tables)
python backup_supabase.py --force-full
```

### Restore from Backup

```bash
# List available backups
python backup_supabase.py --list

# Safe restore (recommended - with auto safety backup)
python backup_supabase_safe.py --restore supabase_backup_YYYYMMDD_HHMMSS.json

# Or use wrapper script
./restore_safe.sh supabase_backup_YYYYMMDD_HHMMSS.json
```

### Rollback if Restore Fails

```bash
# List safety backups
python backup_supabase_safe.py --list-safety

# Rollback to state before restore
python backup_supabase_safe.py --rollback safety_backup_YYYYMMDD_HHMMSS.json
```

## 📖 Usage

### Backup Operations

#### Smart Backup (Default)

```bash
python backup_supabase.py
```

- Compares current data with previous backup
- Only backs up tables that changed
- Skips unchanged tables (saves time and storage)

#### Force Full Backup

```bash
python backup_supabase.py --force-full
```

- Backs up all tables regardless of changes
- Useful for initial backup or when you want complete snapshot

#### List Backups

```bash
python backup_supabase.py --list
```

Shows all available backups with:
- Date/Time
- Backup type (FULL/INCREMENTAL)
- Size
- Number of changed tables
- Total rows

### Restore Operations

#### Safe Restore (Recommended)

```bash
python backup_supabase_safe.py --restore <backup_file>
```

**Features:**
- 🛡️ Automatic safety backup before restore
- 🔍 Data validation before restore
- 📊 State recording (before/after)
- ✅ Automatic verification after restore
- 💾 Comprehensive restore log

#### Standard Restore

```bash
python backup_supabase.py --restore-interactive
```

Interactive restore with timeline selection (no safety backup).

### Automation

#### Cron Job Setup (Backup Every 5 Minutes)

```bash
# Edit crontab
crontab -e

# Add this line (backup every 5 minutes)
*/5 * * * * /path/to/backup_release/run_backup.sh
```

See `cron_example.txt` for more examples.

## 🛡️ Safety Features

### Automatic Safety Backup

Before every restore operation, the tool automatically creates a safety backup:

```
safety_backups/
└── safety_backup_20251128_074820.json
```

This backup can be used to rollback if restore fails.

### Rollback Mechanism

If restore fails or produces unexpected results:

```bash
# List safety backups
python backup_supabase_safe.py --list-safety

# Rollback
python backup_supabase_safe.py --rollback safety_backup_YYYYMMDD_HHMMSS.json
```

### Data Validation

The tool validates backup data before restore:
- ✅ Checks metadata structure
- ✅ Verifies critical tables exist
- ✅ Detects corrupted or invalid data
- ✅ Warns about potential issues

### Restore Verification

After restore, the tool automatically:
- ✅ Compares row counts before/after
- ✅ Verifies data integrity
- ✅ Logs all operations
- ✅ Reports any discrepancies

## ⚙️ Configuration

### Environment Variables

Create `.env` file with:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Optional: Direct PostgreSQL connection
# SUPABASE_CONNECTION_STRING=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### Backup Settings

Default settings in `backup_supabase.py`:
- **Backup interval**: Every 5 minutes (when using cron)
- **Retention**: 288 backups (24 hours)
- **Batch size**: 100 rows per batch
- **Page size**: 1000 rows per API call

## 📁 Project Structure

```
backup_release/
├── backups/                  # Backup JSON files
├── safety_backups/          # Safety backups (pre-restore snapshots)
├── summaries/              # Backup summaries & restore logs
├── logs/                   # Application logs
├── backup_supabase.py      # Main backup script
├── backup_supabase_safe.py # Safe restore script
├── restore_backup.py       # Interactive restore (legacy)
├── restore_safe.sh         # Wrapper script for safe restore
├── run_backup.sh          # Cron job script
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from env.example)
├── env.example            # Environment variables template
├── README.md              # This file
├── SAFETY_FEATURES.md     # Safety features documentation
├── TROUBLESHOOTING.md     # Troubleshooting guide
├── SETUP.md               # Detailed setup instructions
└── QUICK_START.md         # Quick start guide
```

## 📚 Documentation

All detailed documentation is available in the [`docs/`](docs/) folder:

- **[Installation Guide](docs/INSTALLATION.md)** - Step-by-step installation instructions
- **[Quick Start](docs/QUICK_START.md)** - Get started quickly
- **[Safe Restore Guide](docs/QUICK_START_SAFE.md)** - Safe restore quick start
- **[Usage Examples](docs/USAGE_EXAMPLES.md)** - Common use cases and examples
- **[Safety Features](docs/SAFETY_FEATURES.md)** - Safety features documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Setup Guide](docs/SETUP.md)** - Detailed setup instructions
- **[Changelog](docs/CHANGELOG.md)** - Version history
- **[Contributing](docs/CONTRIBUTING.md)** - How to contribute
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Project structure overview
- **[Documentation Index](docs/INDEX.md)** - Complete documentation index

## 🔧 Troubleshooting

### Common Issues

#### Error 400: Generated Column

**Problem**: `cannot insert a non-DEFAULT value into column "booking_number"`

**Solution**: Already handled automatically. The tool excludes generated columns during restore.

#### Error: Duplicate Key

**Problem**: `duplicate key value violates unique constraint`

**Solution**: The tool uses UPSERT (update or insert) to handle duplicates automatically.

#### Error: Connection Failed

**Problem**: Cannot connect to Supabase

**Solution**: 
1. Check `.env` file has correct credentials
2. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
3. Check network connectivity

See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for more details.

## 📊 Backup Format

### Full Backup

```json
{
  "metadata": {
    "backup_date": "2025-11-28T07:22:53",
    "backup_type": "full",
    "total_tables": 30,
    "total_rows": 15541
  },
  "data": {
    "bookings": [...],
    "users": [...]
  }
}
```

### Incremental Backup

```json
{
  "metadata": {
    "backup_date": "2025-11-28T07:39:32",
    "backup_type": "incremental",
    "previous_backup": "20251128_072253",
    "changed_tables": ["booking_participants"],
    "unchanged_tables": ["bookings", "users", ...]
  },
  "data": {
    "booking_participants": [...],  // Only changed tables
    "bookings": {
      "_unchanged": true,
      "_reference_backup": "20251128_072253"
    }
  }
}
```

## 🎓 Examples

### Example 1: Daily Backup Workflow

```bash
# Morning: Create full backup
python backup_supabase.py --force-full

# Throughout day: Incremental backups (via cron)
# Every 5 minutes automatically

# Evening: Verify backups
python backup_supabase.py --list
```

### Example 2: Restore After Data Loss

```bash
# 1. List backups
python backup_supabase.py --list

# 2. Safe restore (creates safety backup automatically)
python backup_supabase_safe.py --restore supabase_backup_20251128_074723.json

# 3. Verify restore
cat summaries/restore_log_*.json

# 4. If needed, rollback
python backup_supabase_safe.py --rollback safety_backup_20251128_074820.json
```

### Example 3: Compare Data Changes

```bash
# Create backup before changes
python backup_supabase.py

# Make changes to database...

# Create backup after changes
python backup_supabase.py

# Compare (see summaries/comparison_*.json)
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📚 Documentation

All documentation is available in the [`docs/`](docs/) folder. See [Documentation Index](docs/INDEX.md) for complete list.

## ⚠️ Important Notes

1. **Always use safe restore for production** - It creates automatic safety backups
2. **Keep safety backups** - Don't delete until you're sure restore was successful
3. **Test in development first** - Always test restore in dev environment
4. **Monitor disk space** - Backups can take significant space
5. **Verify after restore** - Always check restore logs and verify data

## 🆘 Support

For issues and questions:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review restore logs in `summaries/`
3. Check application logs in `logs/`

---

**Made with ❤️ for safe database backups**
