# Safety Features - Backup & Restore

## 🛡️ Fitur Keamanan

Program backup sekarang dilengkapi dengan fitur keamanan untuk mencegah kerusakan data:

### 1. **Safety Backup Otomatis**
- ✅ Membuat backup otomatis sebelum restore
- ✅ Disimpan di folder `safety_backups/`
- ✅ Dapat digunakan untuk rollback jika restore gagal

### 2. **Validasi Data**
- ✅ Validasi struktur backup sebelum restore
- ✅ Cek tabel critical (users, packages, bookings)
- ✅ Deteksi data yang corrupt atau tidak valid

### 3. **Rollback Mechanism**
- ✅ Rollback otomatis jika restore gagal
- ✅ Mengembalikan database ke state sebelum restore
- ✅ Safety backup sebelum rollback (double safety)

### 4. **Tracking & Logging**
- ✅ Mencatat state sebelum dan sesudah restore
- ✅ Log detail untuk setiap tabel
- ✅ Verifikasi jumlah rows setelah restore

## 📋 Cara Penggunaan

### Safe Restore (Recommended)

```bash
cd /home/alterpix/Documents/rayhar_statistic/backup_app
source venv/bin/activate

# Restore dengan safety backup otomatis
python backup_supabase_safe.py --restore supabase_backup_20251128_074723.json
```

**Proses yang terjadi:**
1. 🛡️ Membuat safety backup (snapshot current state)
2. 🔍 Validasi backup data
3. 📊 Mencatat state sebelum restore
4. 🔄 Restore data
5. ✅ Verifikasi hasil restore
6. 💾 Menyimpan restore log

### Rollback dari Safety Backup

Jika restore gagal atau ada masalah:

```bash
# List safety backups
python backup_supabase_safe.py --list-safety

# Rollback ke state sebelum restore
python backup_supabase_safe.py --rollback safety_backup_20251128_074820.json
```

### Standard Restore (Tanpa Safety Backup)

```bash
# Menggunakan script original (tidak recommended untuk production)
python backup_supabase.py --restore-interactive
```

## 📁 Struktur File

```
backup_app/
├── backups/              # Backup files
├── safety_backups/      # Safety backups (pre-restore snapshots)
├── summaries/           # Restore logs dan summaries
├── logs/               # Log files
├── backup_supabase.py  # Script original
└── backup_supabase_safe.py  # Script dengan safety features
```

## 🔄 Alur Restore dengan Safety

```
1. User meminta restore
   ↓
2. [SAFETY] Buat backup current state → safety_backups/
   ↓
3. [VALIDATE] Validasi backup data
   ↓
4. [RECORD] Catat state sebelum restore (row counts)
   ↓
5. [RESTORE] Restore data dengan UPSERT
   ↓
6. [VERIFY] Verifikasi hasil restore
   ↓
7. [LOG] Simpan restore log
   ↓
8. ✅ Selesai atau ❌ Rollback jika gagal
```

## 🆘 Recovery Scenarios

### Scenario 1: Restore Gagal

```bash
# Restore gagal, safety backup tersedia
python backup_supabase_safe.py --rollback safety_backup_20251128_074820.json
```

### Scenario 2: Data Tidak Sesuai Setelah Restore

```bash
# Cek restore log
cat summaries/restore_log_*.json

# Rollback jika perlu
python backup_supabase_safe.py --rollback safety_backup_20251128_074820.json
```

### Scenario 3: Restore Sebagian Gagal

Program akan:
- ✅ Restore tabel yang berhasil
- ⚠️ Log tabel yang gagal
- 💾 Safety backup tetap tersedia untuk rollback manual

## ⚠️ Best Practices

1. **Selalu gunakan safe restore untuk production**
   ```bash
   python backup_supabase_safe.py --restore <backup_file>
   ```

2. **Jangan skip safety backup** (kecuali testing)
   - Safety backup adalah jaring pengaman terakhir

3. **Verifikasi setelah restore**
   - Cek restore log di `summaries/`
   - Bandingkan row counts sebelum/sesudah

4. **Simpan safety backups**
   - Jangan hapus safety backups sampai yakin restore berhasil
   - Safety backups bisa di-cleanup setelah 7 hari

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
# Hanya untuk testing, jangan gunakan di production!
python backup_supabase_safe.py --restore <backup> --skip-safety
```

### List Safety Backups

```bash
python backup_supabase_safe.py --list-safety
```

## 💡 Tips

- ✅ **Safety backup otomatis** - Tidak perlu manual backup sebelum restore
- ✅ **Rollback mudah** - Satu command untuk rollback
- ✅ **Log lengkap** - Semua operasi tercatat
- ✅ **Validasi data** - Deteksi masalah sebelum restore
- ✅ **Verifikasi otomatis** - Cek hasil setelah restore

