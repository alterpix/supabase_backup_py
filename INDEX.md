# 📚 Documentation Index

Quick navigation to all documentation:

## 🚀 Getting Started

1. **[README.md](README.md)** - Main documentation, overview, and quick start
2. **[INSTALLATION.md](INSTALLATION.md)** - Step-by-step installation guide
3. **[QUICK_START.md](QUICK_START.md)** - Quick start guide for basic usage
4. **[QUICK_START_SAFE.md](QUICK_START_SAFE.md)** - Quick start for safe restore

## 📖 Usage Guides

1. **[USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)** - Common use cases and examples
2. **[SETUP.md](SETUP.md)** - Detailed setup instructions
3. **[SAFETY_FEATURES.md](SAFETY_FEATURES.md)** - Safety features documentation

## 🔧 Troubleshooting

1. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
2. **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

## 🤝 Contributing

1. **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to this project

## 📋 Quick Reference

### Backup
```bash
python backup_supabase.py              # Smart backup
python backup_supabase.py --force-full # Full backup
python backup_supabase.py --list       # List backups
```

### Restore
```bash
python backup_supabase_safe.py --restore <backup_file>  # Safe restore
python backup_supabase_safe.py --rollback <safety_backup> # Rollback
python backup_supabase_safe.py --list-safety            # List safety backups
```

### Automation
```bash
# Add to crontab (backup every 5 minutes)
*/5 * * * * /path/to/backup_release/run_backup.sh
```

## 📁 File Structure

- `backup_supabase.py` - Main backup script
- `backup_supabase_safe.py` - Safe restore script
- `restore_safe.sh` - Wrapper script
- `run_backup.sh` - Cron job script
- `requirements.txt` - Python dependencies
- `env.example` - Environment variables template

## 🆘 Need Help?

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)
3. Read restore logs in `summaries/`

