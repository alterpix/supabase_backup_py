# 🛡️ Quick Start - Safe Restore

## Restore dengan Safety Features

### 1. Safe Restore (Recommended)

```bash
cd /home/alterpix/Documents/rayhar_statistic/backup_app
source venv/bin/activate

# Pilih backup yang ingin di-restore
python backup_supabase.py --list

# Safe restore (dengan auto-backup)
python backup_supabase_safe.py --restore supabase_backup_YYYYMMDD_HHMMSS.json
```

**Apa yang terjadi:**
1. 🛡️ Safety backup otomatis dibuat (snapshot current state)
2. 🔍 Validasi backup data
3. 📊 Recording state sebelum restore
4. 🔄 Restore data
5. ✅ Verifikasi hasil restore
6. 💾 Log disimpan

### 2. Jika Restore Gagal - Rollback

```bash
# List safety backups
python backup_supabase_safe.py --list-safety

# Rollback ke state sebelum restore
python backup_supabase_safe.py --rollback safety_backup_YYYYMMDD_HHMMSS.json
```

### 3. Verifikasi Restore

Setelah restore, cek:
- ✅ Restore log di `summaries/restore_log_*.json`
- ✅ Row counts sebelum/sesudah restore
- ✅ Tabel yang berhasil/gagal di-restore

## Keuntungan Safe Restore

✅ **Auto-backup** - Tidak perlu manual backup sebelum restore  
✅ **Rollback mudah** - Satu command untuk rollback  
✅ **Validasi data** - Deteksi masalah sebelum restore  
✅ **Log lengkap** - Semua operasi tercatat  
✅ **Verifikasi otomatis** - Cek hasil setelah restore  

## Contoh Workflow

```bash
# 1. List backups
python backup_supabase.py --list

# 2. Safe restore
python backup_supabase_safe.py --restore supabase_backup_20251128_074723.json

# 3. Jika ada masalah, rollback
python backup_supabase_safe.py --rollback safety_backup_20251128_074820.json

# 4. Cek restore log
cat summaries/restore_log_*.json | jq .
```

