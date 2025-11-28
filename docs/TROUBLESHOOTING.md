# Troubleshooting Backup & Restore

## Error 400 Bad Request

### Penyebab Error 400

Error 400 Bad Request biasanya terjadi karena:

1. **GENERATED COLUMNS** - Kolom yang di-generate otomatis oleh database
   - Contoh: `booking_number` di tabel `booking_hajj` (GENERATED COLUMN dengan `DEFAULT booking_code`)
   - Tidak bisa di-insert manual, harus di-exclude saat restore

2. **IDENTITY COLUMNS** - Kolom ID yang di-generate otomatis
   - Contoh: `id` di tabel `room_allotments` (GENERATED ALWAYS AS IDENTITY)
   - Tidak bisa di-insert manual, harus di-exclude saat restore

### Solusi yang Sudah Diterapkan

Program backup sudah otomatis menangani kolom-kolom ini dengan:

1. **Exclude Generated Columns** saat restore:
   - `booking_hajj`: exclude `booking_number`
   - `room_allotments`: exclude `id`

2. **Auto-filter** kolom yang tidak bisa di-insert sebelum restore

### Tabel yang Terkena Dampak

| Tabel | Kolom yang Di-exclude | Alasan |
|-------|----------------------|--------|
| `booking_hajj` | `booking_number` | GENERATED COLUMN (default dari `booking_code`) |
| `room_allotments` | `id` | GENERATED ALWAYS AS IDENTITY |

### Verifikasi

Setelah restore, kolom-kolom ini akan otomatis di-generate oleh database dengan nilai yang sesuai.

## Error Lainnya

### Error: "duplicate key value violates unique constraint"

**Penyebab**: Data sudah ada di database dengan ID yang sama.

**Solusi**: Program sudah menggunakan UPSERT (update or insert) untuk menangani ini. Jika masih error, cek apakah ada constraint unique lainnya.

### Error: "foreign key constraint violation"

**Penyebab**: ID yang direferensikan tidak ada di tabel parent.

**Solusi**: Pastikan restore dilakukan dalam urutan yang benar (parent tables dulu, kemudian child tables).

### Error: "column does not exist"

**Penyebab**: Schema database berubah atau kolom dihapus.

**Solusi**: Update backup script untuk exclude kolom yang tidak ada lagi.

## Tips

1. **Selalu backup sebelum restore** - Untuk safety
2. **Cek log restore** - Untuk melihat tabel mana yang error
3. **Verifikasi data setelah restore** - Pastikan jumlah rows sesuai
4. **Test restore di development dulu** - Sebelum restore di production

