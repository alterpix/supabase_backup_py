# Setup Backup App

## 1. Setup Virtual Environment

Virtual environment sudah dibuat di `backup_app/venv`. Jika perlu membuat ulang:

```bash
cd /home/alterpix/Documents/rayhar_statistic/backup_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Setup .env File

File `.env` sudah di-copy dari `release_v2.1/.env`. Pastikan kredensial sudah benar:

```bash
cd /home/alterpix/Documents/rayhar_statistic/backup_app
# Edit .env jika perlu
nano .env
```

Pastikan ada:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## 3. Test Backup Manual

```bash
cd /home/alterpix/Documents/rayhar_statistic/backup_app
source venv/bin/activate
python backup_supabase.py
```

## 4. Setup Cron untuk Backup Setiap 5 Menit

```bash
crontab -e
```

Tambahkan baris ini:
```cron
*/5 * * * * /home/alterpix/Documents/rayhar_statistic/backup_app/run_backup.sh
```

Atau gunakan path Python langsung:
```cron
*/5 * * * * cd /home/alterpix/Documents/rayhar_statistic/backup_app && /home/alterpix/Documents/rayhar_statistic/backup_app/venv/bin/python backup_supabase.py >> backup.log 2>&1
```

## 5. Restore dari Timeline

### Interactive Restore (Recommended):
```bash
cd /home/alterpix/Documents/rayhar_statistic/backup_app
source venv/bin/activate
python backup_supabase.py --restore-interactive
# atau
python restore_backup.py
```

### Restore dengan filename:
```bash
python backup_supabase.py --restore supabase_backup_20250101_120000.json
```

### List semua backup:
```bash
python backup_supabase.py --list
```

## Catatan

- **Smart Comparison**: Backup hanya tabel yang berubah, skip tabel yang tidak berubah
- Backup setiap 5 menit akan menyimpan **288 backup** (24 jam)
- Backup lama akan otomatis dihapus setelah 288 backup
- File backup disimpan di `backup_app/backups/supabase_backup_*.json`
- Summary disimpan di `backup_app/summaries/backup_summary_*.json`
- Log backup disimpan di `backup_app/logs/backup.log`
- Incremental backup lebih kecil dan lebih cepat karena hanya backup data yang berubah

