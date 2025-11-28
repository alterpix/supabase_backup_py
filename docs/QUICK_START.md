# Quick Start - Backup Supabase

## Setup Cepat

1. **Pastikan kredensial ada di `.env`**:
   ```bash
   # Di release_v2.1/.env atau root .env
   SUPABASE_URL=https://[PROJECT-REF].supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_key_here
   ```

2. **Jalankan backup manual pertama kali**:
   ```bash
   cd /home/alterpix/Documents/rayhar_statistic
   source release_v2.1/venv/bin/activate
   python backup_app/backup_supabase.py
   ```

3. **Setup cron untuk otomatisasi** (opsional):
   ```bash
   crontab -e
   # Tambahkan baris ini untuk backup harian jam 2 pagi:
   0 2 * * * cd /home/alterpix/Documents/rayhar_statistic && /home/alterpix/Documents/rayhar_statistic/release_v2.1/venv/bin/python backup_app/backup_supabase.py >> backup_app/backup.log 2>&1
   ```

## Command Cepat

```bash
# Backup manual
python backup_app/backup_supabase.py

# List backup yang ada
python backup_app/backup_supabase.py --list

# Restore (hati-hati!)
python backup_app/backup_supabase.py --restore supabase_backup_20250101_120000.json
```

## Lokasi File

- **Backup files**: `backup_app/backups/supabase_backup_*.json`
- **Summary files**: `backup_app/summaries/backup_summary_*.json`
- **Log file**: `backup_app/logs/backup.log` (jika menggunakan cron)

## Smart Comparison

Program otomatis compare data dengan backup sebelumnya:
- ✅ **Skip** tabel yang tidak berubah (menghemat waktu & storage)
- ✅ **Backup** hanya tabel yang berubah
- ✅ Backup incremental lebih kecil dan lebih cepat

### Force Full Backup (jika perlu):
```bash
python backup_supabase.py --force-full
```

## Catatan

- Backup otomatis menyimpan **10 backup terakhir**
- File backup bisa besar, pastikan ada ruang disk cukup
- Backup menggunakan format JSON untuk mudah di-compare

