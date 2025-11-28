#!/usr/bin/env python3
"""
Script Otomatisasi Backup Database Supabase dengan Smart Comparison
Mengekspor hanya tabel yang berubah dari Supabase dan menyimpan sebagai JSON backup
"""
import os
import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base directory - standalone, no parent dependency
BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR
BACKUPS_DIR = BACKUP_DIR / 'backups'
SUMMARIES_DIR = BACKUP_DIR / 'summaries'
LOGS_DIR = BACKUP_DIR / 'logs'

# Create subdirectories
BACKUPS_DIR.mkdir(exist_ok=True)
SUMMARIES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Load environment variables
def load_env():
    """Load environment variables from .env files"""
    script_dir = Path(__file__).resolve().parent
    env_paths = [
        script_dir / '.env',  # Prioritas pertama: .env di current directory
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded .env from {env_path}")
            return True
    
    logger.error("No .env file found!")
    return False

def get_supabase_client():
    """Initialize Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/ANON_KEY must be set in .env")
    
    return create_client(url, key)

def get_all_tables():
    """Get list of all tables from query.sql schema or use default list"""
    # Try to find query.sql in current directory or parent
    query_sql_path = BASE_DIR / 'query.sql'
    if not query_sql_path.exists():
        # Try parent directory
        query_sql_path = BASE_DIR.parent / 'query.sql'
    
    if not query_sql_path.exists():
        logger.warning("query.sql not found, using default table list")
        return [
            'booking_hajj', 'booking_hajj_members', 'booking_hajj_payments',
            'booking_participants', 'booking_payments', 'booking_status_history',
            'bookings', 'detail_packages', 'packages', 'room_prices', 'room_types',
            'users', 'inquiries', 'hajj_packages', 'hajj_package_prices',
            'hajj_hotels', 'hajj_package_hotels', 'room_allotments'
        ]
    
    import re
    schema_text = query_sql_path.read_text()
    table_names = []
    for match in re.finditer(r'CREATE TABLE public\.([a-zA-Z0-9_]+)', schema_text):
        name = match.group(1)
        if name not in table_names:
            table_names.append(name)
    
    return table_names

def fetch_table_data(client, table_name, page_size=1000):
    """Fetch all data from a table using pagination"""
    data = []
    start = 0
    
    while True:
        try:
            response = client.table(table_name).select('*').range(start, start + page_size - 1).execute()
            rows = response.data if hasattr(response, 'data') else response
            
            if not rows or len(rows) == 0:
                break
            
            data.extend(rows)
            
            if len(rows) < page_size:
                break
            
            start += page_size
            
        except Exception as e:
            logger.error(f"Error fetching {table_name}: {e}")
            break
    
    return data

def calculate_table_hash(data):
    """Calculate hash for table data to detect changes"""
    if not data:
        return hashlib.md5(b'empty').hexdigest()
    
    # Sort data by id if available, otherwise by first field
    try:
        sorted_data = sorted(data, key=lambda x: x.get('id', str(x)))
    except:
        sorted_data = data
    
    # Create a stable JSON representation
    json_str = json.dumps(sorted_data, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()

def get_latest_backup():
    """Get the most recent backup file"""
    backup_files = sorted(
        BACKUPS_DIR.glob('supabase_backup_*.json'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not backup_files:
        return None
    
    try:
        with open(backup_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading latest backup: {e}")
        return None

def compare_table_data(current_data, previous_data):
    """Compare current data with previous backup data"""
    if previous_data is None:
        return {'changed': True, 'reason': 'no_previous_backup'}
    
    current_hash = calculate_table_hash(current_data)
    previous_hash = calculate_table_hash(previous_data)
    
    if current_hash == previous_hash:
        return {'changed': False, 'hash': current_hash}
    
    # Calculate differences
    current_ids = {row.get('id') for row in current_data if row.get('id')}
    previous_ids = {row.get('id') for row in previous_data if row.get('id')}
    
    added = current_ids - previous_ids
    removed = previous_ids - current_ids
    
    return {
        'changed': True,
        'hash': current_hash,
        'added_count': len(added),
        'removed_count': len(removed),
        'current_count': len(current_data),
        'previous_count': len(previous_data)
    }

def create_backup(force_full=False):
    """Create backup with smart comparison - only backup changed tables"""
    if not load_env():
        return False
    
    try:
        client = get_supabase_client()
        tables = get_all_tables()
        
        # Get previous backup for comparison
        previous_backup = None if force_full else get_latest_backup()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"supabase_backup_{timestamp}.json"
        backup_path = BACKUPS_DIR / backup_filename
        
        if previous_backup:
            logger.info(f"📊 Smart backup mode: Comparing with previous backup")
            logger.info(f"   Previous backup: {previous_backup['metadata'].get('timestamp', 'unknown')}")
        else:
            logger.info(f"📦 Full backup mode: No previous backup found")
        
        logger.info(f"Starting backup to {backup_path}")
        
        backup_data = {
            'metadata': {
                'backup_date': datetime.now().isoformat(),
                'timestamp': timestamp,
                'backup_type': 'incremental' if previous_backup else 'full',
                'previous_backup': previous_backup['metadata']['timestamp'] if previous_backup else None,
                'total_tables': len(tables),
                'tables': tables
            },
            'data': {}
        }
        
        total_rows = 0
        successful_tables = 0
        failed_tables = []
        unchanged_tables = []
        changed_tables = []
        
        for table in tables:
            logger.info(f"Checking table: {table}")
            try:
                current_data = fetch_table_data(client, table)
                row_count = len(current_data)
                
                # Compare with previous backup
                previous_data = None
                if previous_backup and not force_full:
                    previous_data = previous_backup['data'].get(table)
                    # Handle incremental backup - if table is marked as unchanged, load from referenced backup
                    if isinstance(previous_data, dict):
                        if previous_data.get('_backup_failed'):
                            previous_data = None
                        elif previous_data.get('_unchanged'):
                            # Load from referenced backup
                            ref_timestamp = previous_data.get('_reference_backup')
                            if ref_timestamp:
                                ref_backup_path = BACKUPS_DIR / f"supabase_backup_{ref_timestamp}.json"
                                if ref_backup_path.exists():
                                    try:
                                        with open(ref_backup_path, 'r', encoding='utf-8') as f:
                                            ref_backup = json.load(f)
                                        previous_data = ref_backup['data'].get(table)
                                        if isinstance(previous_data, dict) and previous_data.get('_unchanged'):
                                            previous_data = None  # Keep going back if needed
                                    except Exception as e:
                                        logger.warning(f"Error loading referenced backup for {table}: {e}")
                                        previous_data = None
                                else:
                                    previous_data = None
                            else:
                                previous_data = None
                
                comparison = compare_table_data(current_data, previous_data)
                
                if not comparison['changed'] and not force_full:
                    # Table unchanged, reference previous backup
                    unchanged_tables.append(table)
                    backup_data['data'][table] = {
                        '_unchanged': True,
                        '_reference_backup': previous_backup['metadata']['timestamp'],
                        '_hash': comparison['hash']
                    }
                    logger.info(f"  ⏭️  {table}: {row_count} rows (unchanged, skipped)")
                    continue
                
                # Table changed or force full backup
                if row_count > 0:
                    backup_data['data'][table] = current_data
                    successful_tables += 1
                    total_rows += row_count
                    changed_tables.append(table)
                    
                    if comparison.get('added_count') or comparison.get('removed_count'):
                        logger.info(f"  ✓ {table}: {row_count} rows (changed: +{comparison.get('added_count', 0)} -{comparison.get('removed_count', 0)})")
                    else:
                        logger.info(f"  ✓ {table}: {row_count} rows (changed)")
                else:
                    backup_data['data'][table] = []
                    successful_tables += 1
                    logger.info(f"  ✓ {table}: empty table")
                    
            except Exception as e:
                error_msg = str(e)
                backup_data['data'][table] = {
                    '_error': error_msg,
                    '_backup_failed': True
                }
                failed_tables.append(table)
                logger.error(f"  ✗ {table}: {error_msg}")
        
        # Update metadata
        backup_data['metadata']['total_rows'] = total_rows
        backup_data['metadata']['successful_tables'] = successful_tables
        backup_data['metadata']['failed_tables'] = failed_tables
        backup_data['metadata']['failed_count'] = len(failed_tables)
        backup_data['metadata']['unchanged_tables'] = unchanged_tables
        backup_data['metadata']['changed_tables'] = changed_tables
        backup_data['metadata']['unchanged_count'] = len(unchanged_tables)
        backup_data['metadata']['changed_count'] = len(changed_tables)
        
        # Save backup file
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        # Create summary
        summary = {
            'backup_file': backup_filename,
            'backup_path': str(backup_path),
            'backup_size_mb': round(backup_path.stat().st_size / (1024 * 1024), 2),
            'timestamp': timestamp,
            'backup_type': backup_data['metadata']['backup_type'],
            'total_tables': len(tables),
            'successful_tables': successful_tables,
            'failed_tables': failed_tables,
            'unchanged_tables': unchanged_tables,
            'changed_tables': changed_tables,
            'total_rows': total_rows
        }
        
        # Save summary
        summary_path = SUMMARIES_DIR / f"backup_summary_{timestamp}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info("=" * 60)
        logger.info("BACKUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Backup file: {backup_filename}")
        logger.info(f"Backup type: {backup_data['metadata']['backup_type']}")
        logger.info(f"Backup size: {summary['backup_size_mb']} MB")
        logger.info(f"Total tables: {len(tables)}")
        logger.info(f"Changed tables: {len(changed_tables)}")
        logger.info(f"Unchanged tables: {len(unchanged_tables)} (skipped)")
        logger.info(f"Successful: {successful_tables}")
        logger.info(f"Failed: {len(failed_tables)}")
        logger.info(f"Total rows backed up: {total_rows:,}")
        logger.info("=" * 60)
        
        if unchanged_tables:
            logger.info(f"⏭️  Skipped (unchanged): {', '.join(unchanged_tables[:5])}{'...' if len(unchanged_tables) > 5 else ''}")
        
        if failed_tables:
            logger.warning(f"Failed tables: {', '.join(failed_tables)}")
        
        # Cleanup old backups (keep last 288 = 24 jam dengan backup setiap 5 menit)
        cleanup_old_backups(keep_count=288)
        
        return True
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_old_backups(keep_count=288):
    """Remove old backup files, keeping only the most recent ones"""
    backup_files = sorted(
        BACKUPS_DIR.glob('supabase_backup_*.json'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if len(backup_files) > keep_count:
        files_to_delete = backup_files[keep_count:]
        for file in files_to_delete:
            try:
                # Also delete corresponding summary
                summary_file = SUMMARIES_DIR / file.name.replace('supabase_backup_', 'backup_summary_')
                if summary_file.exists():
                    summary_file.unlink()
                file.unlink()
                logger.info(f"Deleted old backup: {file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {file.name}: {e}")

def list_backups_with_timeline():
    """List all available backups with timeline information"""
    backups = sorted(BACKUPS_DIR.glob('supabase_backup_*.json'), reverse=True)
    
    if not backups:
        logger.info("No backups found")
        return []
    
    backup_list = []
    for idx, backup in enumerate(backups, 1):
        try:
            with open(backup, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            size_mb = backup.stat().st_size / (1024 * 1024)
            backup_date = datetime.fromisoformat(backup_data['metadata']['backup_date'])
            
            backup_list.append({
                'index': idx,
                'filename': backup.name,
                'path': str(backup),
                'size_mb': round(size_mb, 2),
                'date': backup_date,
                'timestamp': backup_data['metadata'].get('timestamp', ''),
                'backup_type': backup_data['metadata'].get('backup_type', 'full'),
                'total_rows': backup_data['metadata'].get('total_rows', 0),
                'total_tables': backup_data['metadata'].get('total_tables', 0),
                'successful_tables': backup_data['metadata'].get('successful_tables', 0),
                'changed_count': backup_data['metadata'].get('changed_count', 0),
                'unchanged_count': backup_data['metadata'].get('unchanged_count', 0)
            })
        except Exception as e:
            logger.warning(f"Error reading backup {backup.name}: {e}")
    
    return backup_list

def restore_backup_interactive():
    """Interactive restore with timeline selection"""
    backups = list_backups_with_timeline()
    
    if not backups:
        logger.error("No backups available for restore")
        return False
    
    print("\n" + "=" * 80)
    print("AVAILABLE BACKUPS (Timeline)")
    print("=" * 80)
    print(f"{'#':<4} {'Date/Time':<20} {'Type':<12} {'Size (MB)':<12} {'Changed':<10} {'Rows':<12}")
    print("-" * 80)
    
    for backup in backups:
        date_str = backup['date'].strftime('%Y-%m-%d %H:%M:%S')
        backup_type = backup['backup_type'].upper()
        print(f"{backup['index']:<4} {date_str:<20} {backup_type:<12} {backup['size_mb']:<12.2f} "
              f"{backup['changed_count']:<10} {backup['total_rows']:<12,}")
    
    print("=" * 80)
    
    try:
        choice = input(f"\nSelect backup to restore (1-{len(backups)}) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            logger.info("Restore cancelled")
            return False
        
        backup_idx = int(choice)
        if backup_idx < 1 or backup_idx > len(backups):
            logger.error("Invalid selection")
            return False
        
        selected_backup = backups[backup_idx - 1]
        
        logger.warning("=" * 80)
        logger.warning("⚠️  WARNING: Restore will overwrite existing data!")
        logger.warning("=" * 80)
        logger.info(f"Selected backup: {selected_backup['filename']}")
        logger.info(f"Backup date: {selected_backup['date'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Backup type: {selected_backup['backup_type']}")
        logger.info(f"Total rows: {selected_backup['total_rows']:,}")
        logger.info(f"Changed tables: {selected_backup['changed_count']}")
        logger.info("\n💡 TIP: Use 'backup_supabase_safe.py --restore' for safe restore with auto-backup")
        
        confirm = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
        if confirm != 'YES':
            logger.info("Restore cancelled")
            return False
        
        return restore_backup(selected_backup['filename'])
        
    except ValueError:
        logger.error("Invalid input. Please enter a number.")
        return False
    except KeyboardInterrupt:
        logger.info("\nRestore cancelled by user")
        return False

def restore_backup(backup_file):
    """Restore data from backup file (supports incremental backups)"""
    backup_path = BACKUPS_DIR / backup_file
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_file}")
        return False
    
    if not load_env():
        return False
    
    try:
        client = get_supabase_client()
        
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        logger.info(f"Restoring from backup: {backup_file}")
        logger.info(f"Backup date: {backup_data['metadata']['backup_date']}")
        logger.info(f"Backup type: {backup_data['metadata'].get('backup_type', 'full')}")
        
        # Handle incremental backup - need to load referenced backups
        if backup_data['metadata'].get('backup_type') == 'incremental':
            previous_timestamp = backup_data['metadata'].get('previous_backup')
            if previous_timestamp:
                logger.info(f"Loading referenced backup: {previous_timestamp}")
                prev_backup_path = BACKUPS_DIR / f"supabase_backup_{previous_timestamp}.json"
                if prev_backup_path.exists():
                    with open(prev_backup_path, 'r', encoding='utf-8') as f:
                        prev_backup = json.load(f)
                    # Merge unchanged tables from previous backup
                    for table, data in backup_data['data'].items():
                        if isinstance(data, dict) and data.get('_unchanged'):
                            backup_data['data'][table] = prev_backup['data'].get(table, [])
        
        restored_tables = 0
        failed_tables = []
        
        for table, data in backup_data['data'].items():
            if isinstance(data, dict) and data.get('_backup_failed'):
                logger.warning(f"Skipping {table} (backup failed)")
                failed_tables.append(table)
                continue
            
            if isinstance(data, dict) and data.get('_unchanged'):
                logger.info(f"Skipping {table} (was unchanged in backup)")
                continue
            
            if not isinstance(data, list):
                logger.warning(f"Skipping {table} (invalid data format)")
                failed_tables.append(table)
                continue
            
            if len(data) == 0:
                logger.info(f"  ✓ {table}: empty table (skipped)")
                continue
            
            try:
                logger.info(f"Restoring {table} ({len(data)} rows)...")
                
                # Define columns to exclude for each table (generated/identity columns)
                excluded_columns = {
                    'booking_hajj': ['booking_number'],  # GENERATED COLUMN
                    'room_allotments': ['id'],  # GENERATED ALWAYS AS IDENTITY
                }
                
                # Filter out excluded columns
                columns_to_exclude = excluded_columns.get(table, [])
                
                # Use UPSERT (update or insert) to handle duplicates
                batch_size = 100
                inserted = 0
                updated = 0
                errors = 0
                
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    
                    # Remove excluded columns from each row
                    filtered_batch = []
                    for row in batch:
                        if isinstance(row, dict):
                            filtered_row = {k: v for k, v in row.items() if k not in columns_to_exclude}
                            filtered_batch.append(filtered_row)
                        else:
                            filtered_batch.append(row)
                    
                    try:
                        # Try upsert (PostgREST supports this via .upsert())
                        client.table(table).upsert(filtered_batch).execute()
                        inserted += len(filtered_batch)
                    except Exception as e:
                        # Fallback: insert one by one, skip duplicates
                        for row in filtered_batch:
                            try:
                                client.table(table).upsert(row).execute()
                                inserted += 1
                            except Exception as insert_error:
                                error_str = str(insert_error)
                                if 'duplicate' in error_str.lower() or '23505' in error_str:
                                    # Duplicate key - try update instead
                                    try:
                                        row_id = row.get('id')
                                        if row_id:
                                            # Also exclude columns for update
                                            update_row = {k: v for k, v in row.items() if k not in columns_to_exclude}
                                            client.table(table).update(update_row).eq('id', row_id).execute()
                                            updated += 1
                                        else:
                                            errors += 1
                                    except:
                                        errors += 1
                                elif 'generated' in error_str.lower() or '428C9' in error_str:
                                    # Generated column error - skip this row or log warning
                                    logger.warning(f"  ⚠️  Skipping row due to generated column: {str(insert_error)[:100]}")
                                    errors += 1
                                else:
                                    errors += 1
                
                if errors == 0:
                    restored_tables += 1
                    logger.info(f"  ✓ {table}: restored ({inserted} inserted, {updated} updated)")
                else:
                    logger.warning(f"  ⚠️  {table}: restored with {errors} errors ({inserted} inserted, {updated} updated)")
                    restored_tables += 1
                
            except Exception as e:
                logger.error(f"  ✗ {table}: {e}")
                failed_tables.append(table)
        
        logger.info("=" * 80)
        logger.info("RESTORE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Restored tables: {restored_tables}")
        logger.info(f"Failed tables: {len(failed_tables)}")
        if failed_tables:
            logger.warning(f"Failed: {', '.join(failed_tables)}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Supabase Database Backup Tool with Smart Comparison')
    parser.add_argument('--restore', type=str, help='Restore from backup file (filename)')
    parser.add_argument('--restore-interactive', action='store_true', help='Interactive restore with timeline selection')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--force-full', action='store_true', help='Force full backup (ignore comparison)')
    
    args = parser.parse_args()
    
    if args.list:
        backups = list_backups_with_timeline()
        if backups:
            print(f"\nAvailable backups ({len(backups)}):")
            print("=" * 80)
            print(f"{'#':<4} {'Date/Time':<20} {'Type':<12} {'Size (MB)':<12} {'Changed':<10} {'Rows':<12}")
            print("-" * 80)
            for backup in backups:
                date_str = backup['date'].strftime('%Y-%m-%d %H:%M:%S')
                backup_type = backup['backup_type'].upper()
                print(f"{backup['index']:<4} {date_str:<20} {backup_type:<12} {backup['size_mb']:<12.2f} "
                      f"{backup['changed_count']:<10} {backup['total_rows']:<12,}")
            print("=" * 80)
        else:
            print("\nNo backups found")
    elif args.restore_interactive:
        restore_backup_interactive()
    elif args.restore:
        restore_backup(args.restore)
    else:
        success = create_backup(force_full=args.force_full)
        sys.exit(0 if success else 1)
