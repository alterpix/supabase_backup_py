#!/usr/bin/env python3
"""
Supabase Database Backup & Restore Tool - All-in-One
Integrated tool dengan semua fitur:
- Smart backup dengan comparison
- Optimized backup dengan multithreading
- Safe restore dengan safety backup
- Optimized restore dengan parallel processing
- Compression support
- Progress bar
"""
import os
import json
import sys
import hashlib
import gzip
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Try to import tqdm for progress bar (optional)
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Dummy tqdm if not available
    class tqdm:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def update(self, n=1):
            pass
        def close(self):
            pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'logs' / 'backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directories
BASE_DIR = Path(__file__).resolve().parent
BACKUPS_DIR = BASE_DIR / 'backups'
SAFETY_BACKUPS_DIR = BASE_DIR / 'safety_backups'
SUMMARIES_DIR = BASE_DIR / 'summaries'
LOGS_DIR = BASE_DIR / 'logs'

# Create subdirectories
BACKUPS_DIR.mkdir(exist_ok=True)
SAFETY_BACKUPS_DIR.mkdir(exist_ok=True)
SUMMARIES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Thread-safe locks
progress_lock = Lock()
result_lock = Lock()

# Configuration
DEFAULT_MAX_WORKERS_BACKUP = 5
DEFAULT_MAX_WORKERS_RESTORE = 3
DEFAULT_BATCH_SIZE = 100
DEFAULT_COMPRESS = True
DEFAULT_SHOW_PROGRESS = True

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def load_env():
    """Load environment variables from .env file"""
    env_path = BASE_DIR / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env from {env_path}")
        return True
    
    logger.error("No .env file found!")
    return False

def get_supabase_client():
    """Get Supabase client"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        return None
    
    try:
        client = create_client(supabase_url, supabase_key)
        logger.info("✅ Connected to Supabase")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        return None

def get_all_tables():
    """Get list of all tables from query.sql or use default list"""
    query_sql_path = BASE_DIR / 'query.sql'
    if not query_sql_path.exists():
        query_sql_path = BASE_DIR.parent / 'query.sql'
    
    if query_sql_path.exists():
        with open(query_sql_path, 'r', encoding='utf-8') as f:
            schema_text = f.read()
        
        table_names = []
        for match in re.finditer(r'CREATE TABLE public\.([a-zA-Z0-9_]+)', schema_text):
            name = match.group(1)
            if name not in table_names:
                table_names.append(name)
        
        if table_names:
            return table_names
    
    # Default table list (fallback)
    return [
        'booking_hajj', 'booking_hajj_members', 'booking_hajj_payments',
        'booking_participants', 'booking_payments', 'booking_status_history',
        'bookings', 'detail_packages', 'excluded_items', 'faqs',
        'flight_details', 'form_visitors', 'hajj_hotels', 'hajj_package_hotels',
        'hajj_package_prices', 'hajj_packages', 'heartbeat', 'hotel_details',
        'included_items', 'inquiries', 'itineraries', 'package_pembayaran',
        'package_room_price_rooms', 'package_room_prices', 'packages',
        'room_allotments', 'room_prices', 'room_types', 'users'
    ]

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
    
    try:
        sorted_data = sorted(data, key=lambda x: x.get('id', str(x)))
    except:
        sorted_data = data
    
    json_str = json.dumps(sorted_data, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()

def compare_table_data(current_data, previous_data):
    """Compare current data with previous backup data"""
    if previous_data is None:
        return {'changed': True, 'reason': 'no_previous_backup'}
    
    current_hash = calculate_table_hash(current_data)
    previous_hash = calculate_table_hash(previous_data)
    
    if current_hash == previous_hash:
        return {'changed': False, 'hash': current_hash}
    
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

def get_latest_backup():
    """Get the most recent backup file"""
    backup_files = sorted(
        BACKUPS_DIR.glob('supabase_backup_*.json*'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not backup_files:
        return None
    
    try:
        backup_path = backup_files[0]
        if str(backup_path).endswith('.gz'):
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(backup_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading latest backup: {e}")
        return None

def get_table_row_counts(client, tables):
    """Get current row counts for all tables"""
    counts = {}
    for table in tables:
        try:
            result = client.table(table).select('id', count='exact').limit(1).execute()
            count = result.count if hasattr(result, 'count') else len(result.data) if hasattr(result, 'data') else 0
            counts[table] = count
        except:
            counts[table] = 0
    return counts

def validate_backup_data(backup_data):
    """Validate backup data before restore"""
    errors = []
    warnings = []
    
    if not backup_data.get('metadata'):
        errors.append("Missing metadata in backup")
        return False, errors, warnings
    
    if not backup_data.get('data'):
        errors.append("Missing data in backup")
        return False, errors, warnings
    
    critical_tables = ['users', 'packages', 'bookings']
    for table in critical_tables:
        if table not in backup_data['data']:
            warnings.append(f"Critical table '{table}' not found in backup")
    
    for table, data in backup_data['data'].items():
        if isinstance(data, dict) and data.get('_backup_failed'):
            warnings.append(f"Table '{table}' had backup errors")
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                if 'id' not in data[0] and table not in ['room_allotments']:
                    warnings.append(f"Table '{table}' rows missing 'id' field")
    
    return len(errors) == 0, errors, warnings

# ============================================================================
# BACKUP FUNCTIONS
# ============================================================================

def fetch_table_with_progress(client, table, previous_backup, force_full, progress_bar=None):
    """Fetch and process a single table (for multithreading)"""
    try:
        current_data = fetch_table_data(client, table)
        row_count = len(current_data)
        
        previous_data = None
        if previous_backup and not force_full:
            previous_data = previous_backup['data'].get(table)
            if isinstance(previous_data, dict):
                if previous_data.get('_backup_failed'):
                    previous_data = None
                elif previous_data.get('_unchanged'):
                    ref_timestamp = previous_data.get('_reference_backup')
                    if ref_timestamp:
                        ref_backup_path = BACKUPS_DIR / f"supabase_backup_{ref_timestamp}.json"
                        if not ref_backup_path.exists():
                            ref_backup_path = BACKUPS_DIR / f"supabase_backup_{ref_timestamp}.json.gz"
                        if ref_backup_path.exists():
                            try:
                                if str(ref_backup_path).endswith('.gz'):
                                    with gzip.open(ref_backup_path, 'rt', encoding='utf-8') as f:
                                        ref_backup = json.load(f)
                                else:
                                    with open(ref_backup_path, 'r', encoding='utf-8') as f:
                                        ref_backup = json.load(f)
                                previous_data = ref_backup['data'].get(table)
                                if isinstance(previous_data, dict) and previous_data.get('_unchanged'):
                                    previous_data = None
                            except Exception as e:
                                logger.warning(f"Error loading referenced backup for {table}: {e}")
                                previous_data = None
                        else:
                            previous_data = None
                    else:
                        previous_data = None
        
        comparison = compare_table_data(current_data, previous_data)
        
        result = {
            'table': table,
            'success': True,
            'data': current_data,
            'row_count': row_count,
            'comparison': comparison,
            'error': None
        }
        
        if progress_bar:
            with progress_lock:
                progress_bar.update(1)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        result = {
            'table': table,
            'success': False,
            'data': None,
            'row_count': 0,
            'comparison': None,
            'error': error_msg
        }
        
        if progress_bar:
            with progress_lock:
                progress_bar.update(1)
        
        return result

def create_backup(force_full=False, max_workers=None, compress=None, show_progress=None):
    """Create backup with optional multithreading and compression"""
    if not load_env():
        return False
    
    max_workers = max_workers if max_workers else (DEFAULT_MAX_WORKERS_BACKUP if max_workers is None else 1)
    compress = compress if compress is not None else DEFAULT_COMPRESS
    show_progress = show_progress if show_progress is not None else DEFAULT_SHOW_PROGRESS
    
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        tables = get_all_tables()
        previous_backup = None if force_full else get_latest_backup()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"supabase_backup_{timestamp}.json"
        if compress:
            backup_filename += ".gz"
        backup_path = BACKUPS_DIR / backup_filename
        
        if previous_backup:
            logger.info(f"📊 Smart backup mode: Comparing with previous backup")
        else:
            logger.info(f"📦 Full backup mode: No previous backup found")
        
        use_multithreading = max_workers > 1
        if use_multithreading:
            logger.info(f"🚀 Optimized mode: {max_workers} workers, compression: {compress}")
        else:
            logger.info(f"📦 Standard mode: Sequential, compression: {compress}")
        
        backup_data = {
            'metadata': {
                'backup_date': datetime.now().isoformat(),
                'timestamp': timestamp,
                'backup_type': 'incremental' if previous_backup else 'full',
                'previous_backup': previous_backup['metadata']['timestamp'] if previous_backup else None,
                'total_tables': len(tables),
                'tables': tables,
                'optimized': use_multithreading,
                'max_workers': max_workers if use_multithreading else None,
                'compressed': compress
            },
            'data': {}
        }
        
        total_rows = 0
        successful_tables = 0
        failed_tables = []
        unchanged_tables = []
        changed_tables = []
        
        # Progress bar
        if show_progress and HAS_TQDM:
            progress_bar = tqdm(total=len(tables), desc="Backing up tables", unit="table")
        else:
            progress_bar = None
        
        try:
            if use_multithreading:
                # Multithreaded backup
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_table = {
                        executor.submit(fetch_table_with_progress, client, table, previous_backup, force_full, progress_bar): table
                        for table in tables
                    }
                    
                    for future in as_completed(future_to_table):
                        table = future_to_table[future]
                        try:
                            result = future.result()
                            
                            if not result['success']:
                                backup_data['data'][result['table']] = {
                                    '_error': result['error'],
                                    '_backup_failed': True
                                }
                                failed_tables.append(result['table'])
                                logger.error(f"  ✗ {result['table']}: {result['error']}")
                                continue
                            
                            comparison = result['comparison']
                            if not comparison['changed'] and not force_full:
                                unchanged_tables.append(result['table'])
                                backup_data['data'][result['table']] = {
                                    '_unchanged': True,
                                    '_reference_backup': previous_backup['metadata']['timestamp'],
                                    '_hash': comparison['hash']
                                }
                                logger.info(f"  ⏭️  {result['table']}: {result['row_count']} rows (unchanged, skipped)")
                                continue
                            
                            row_count = result['row_count']
                            if row_count > 0:
                                backup_data['data'][result['table']] = result['data']
                                successful_tables += 1
                                total_rows += row_count
                                changed_tables.append(result['table'])
                                
                                if comparison.get('added_count') or comparison.get('removed_count'):
                                    logger.info(f"  ✓ {result['table']}: {row_count} rows (changed: +{comparison.get('added_count', 0)} -{comparison.get('removed_count', 0)})")
                                else:
                                    logger.info(f"  ✓ {result['table']}: {row_count} rows (changed)")
                            else:
                                backup_data['data'][result['table']] = []
                                successful_tables += 1
                                logger.info(f"  ✓ {result['table']}: empty table")
                                
                        except Exception as e:
                            logger.error(f"  ✗ {table}: {e}")
                            backup_data['data'][table] = {
                                '_error': str(e),
                                '_backup_failed': True
                            }
                            failed_tables.append(table)
            else:
                # Sequential backup
                for table in tables:
                    logger.info(f"Checking table: {table}")
                    try:
                        current_data = fetch_table_data(client, table)
                        row_count = len(current_data)
                        
                        previous_data = None
                        if previous_backup and not force_full:
                            previous_data = previous_backup['data'].get(table)
                            if isinstance(previous_data, dict):
                                if previous_data.get('_backup_failed'):
                                    previous_data = None
                                elif previous_data.get('_unchanged'):
                                    ref_timestamp = previous_data.get('_reference_backup')
                                    if ref_timestamp:
                                        ref_backup_path = BACKUPS_DIR / f"supabase_backup_{ref_timestamp}.json"
                                        if not ref_backup_path.exists():
                                            ref_backup_path = BACKUPS_DIR / f"supabase_backup_{ref_timestamp}.json.gz"
                                        if ref_backup_path.exists():
                                            try:
                                                if str(ref_backup_path).endswith('.gz'):
                                                    with gzip.open(ref_backup_path, 'rt', encoding='utf-8') as f:
                                                        ref_backup = json.load(f)
                                                else:
                                                    with open(ref_backup_path, 'r', encoding='utf-8') as f:
                                                        ref_backup = json.load(f)
                                                previous_data = ref_backup['data'].get(table)
                                                if isinstance(previous_data, dict) and previous_data.get('_unchanged'):
                                                    previous_data = None
                                            except Exception as e:
                                                logger.warning(f"Error loading referenced backup for {table}: {e}")
                                                previous_data = None
                                        else:
                                            previous_data = None
                                    else:
                                        previous_data = None
                        
                        comparison = compare_table_data(current_data, previous_data)
                        
                        if not comparison['changed'] and not force_full:
                            unchanged_tables.append(table)
                            backup_data['data'][table] = {
                                '_unchanged': True,
                                '_reference_backup': previous_backup['metadata']['timestamp'],
                                '_hash': comparison['hash']
                            }
                            logger.info(f"  ⏭️  {table}: {row_count} rows (unchanged, skipped)")
                            continue
                        
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
                        
                        if progress_bar:
                            progress_bar.update(1)
                            
                    except Exception as e:
                        error_msg = str(e)
                        backup_data['data'][table] = {
                            '_error': error_msg,
                            '_backup_failed': True
                        }
                        failed_tables.append(table)
                        logger.error(f"  ✗ {table}: {error_msg}")
                        if progress_bar:
                            progress_bar.update(1)
        finally:
            if progress_bar:
                progress_bar.close()
        
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
        logger.info(f"Saving backup file...")
        if compress:
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        else:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        file_size = backup_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Backup completed: {backup_filename} ({file_size:.2f} MB)")
        
        # Create summary
        summary = {
            'backup_file': backup_filename,
            'backup_date': backup_data['metadata']['backup_date'],
            'backup_type': backup_data['metadata']['backup_type'],
            'total_tables': len(tables),
            'successful_tables': successful_tables,
            'failed_tables': len(failed_tables),
            'unchanged_tables': len(unchanged_tables),
            'changed_tables': len(changed_tables),
            'total_rows': total_rows,
            'file_size_mb': round(file_size, 2),
            'compressed': compress,
            'optimized': use_multithreading,
            'max_workers': max_workers if use_multithreading else None
        }
        
        summary_path = SUMMARIES_DIR / f"backup_summary_{timestamp}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Cleanup old backups (keep 288 = 24 hours with 5-min intervals)
        cleanup_old_backups(keep_count=288)
        
        logger.info("=" * 80)
        logger.info("📊 BACKUP SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Backup file: {backup_filename}")
        logger.info(f"Backup type: {backup_data['metadata']['backup_type'].upper()}")
        logger.info(f"Total tables: {len(tables)}")
        logger.info(f"Successful: {successful_tables}")
        logger.info(f"Failed: {len(failed_tables)}")
        logger.info(f"Unchanged: {len(unchanged_tables)}")
        logger.info(f"Changed: {len(changed_tables)}")
        logger.info(f"Total rows: {total_rows:,}")
        logger.info(f"File size: {file_size:.2f} MB")
        logger.info(f"Compressed: {compress}")
        if use_multithreading:
            logger.info(f"Workers: {max_workers}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_old_backups(keep_count=288):
    """Cleanup old backups, keep only latest N backups"""
    backup_files = sorted(
        BACKUPS_DIR.glob('supabase_backup_*.json*'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if len(backup_files) > keep_count:
        deleted = 0
        for backup_file in backup_files[keep_count:]:
            try:
                backup_file.unlink()
                # Also delete corresponding summary
                summary_file = SUMMARIES_DIR / backup_file.name.replace('supabase_backup_', 'backup_summary_').replace('.gz', '')
                if summary_file.exists():
                    summary_file.unlink()
                deleted += 1
            except Exception as e:
                logger.warning(f"Error deleting {backup_file}: {e}")
        
        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old backup(s)")

def list_backups():
    """List all available backups"""
    backup_files = sorted(
        BACKUPS_DIR.glob('supabase_backup_*.json*'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not backup_files:
        print("\nNo backups found")
        return
    
    print("\n" + "=" * 80)
    print("AVAILABLE BACKUPS")
    print("=" * 80)
    print(f"{'#':<4} {'Date/Time':<20} {'Type':<12} {'Size (MB)':<12} {'Changed':<10} {'Rows':<12}")
    print("-" * 80)
    
    for idx, backup_file in enumerate(backup_files, 1):
        try:
            is_gz = str(backup_file).endswith('.gz')
            if is_gz:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            date = datetime.fromisoformat(data['metadata']['backup_date'])
            backup_type = data['metadata'].get('backup_type', 'full')
            changed_count = data['metadata'].get('changed_count', 0)
            total_rows = data['metadata'].get('total_rows', 0)
            
            print(f"{idx:<4} {date.strftime('%Y-%m-%d %H:%M:%S'):<20} {backup_type.upper():<12} {size_mb:<12.2f} "
                  f"{changed_count:<10} {total_rows:<12,}")
        except Exception as e:
            print(f"{idx:<4} {backup_file.name} (error: {str(e)[:30]})")
    
    print("=" * 80)

# ============================================================================
# SAFETY BACKUP FUNCTIONS
# ============================================================================

def create_safety_backup():
    """Create safety backup before restore - snapshot current state"""
    if not load_env():
        return None
    
    try:
        client = get_supabase_client()
        if not client:
            return None
        
        tables = get_all_tables()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_backup_filename = f"safety_backup_{timestamp}.json.gz"
        safety_backup_path = SAFETY_BACKUPS_DIR / safety_backup_filename
        
        logger.info(f"🛡️  Creating safety backup: {safety_backup_filename}")
        
        backup_data = {
            'metadata': {
                'backup_date': datetime.now().isoformat(),
                'timestamp': timestamp,
                'backup_type': 'safety',
                'purpose': 'pre_restore_snapshot',
                'total_tables': len(tables),
                'tables': tables
            },
            'data': {}
        }
        
        total_rows = 0
        successful_tables = 0
        failed_tables = []
        
        for table in tables:
            try:
                table_data = fetch_table_data(client, table)
                row_count = len(table_data)
                total_rows += row_count
                
                if row_count > 0:
                    backup_data['data'][table] = table_data
                    successful_tables += 1
                    logger.info(f"  ✓ {table}: {row_count} rows")
                else:
                    backup_data['data'][table] = []
                    successful_tables += 1
                    
            except Exception as e:
                error_msg = str(e)
                backup_data['data'][table] = {
                    '_error': error_msg,
                    '_backup_failed': True
                }
                failed_tables.append(table)
                logger.warning(f"  ⚠️  {table}: {error_msg}")
        
        backup_data['metadata']['total_rows'] = total_rows
        backup_data['metadata']['successful_tables'] = successful_tables
        backup_data['metadata']['failed_tables'] = failed_tables
        
        # Save safety backup (always compressed)
        with gzip.open(safety_backup_path, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        logger.info(f"✅ Safety backup created: {safety_backup_filename} ({round(safety_backup_path.stat().st_size / (1024 * 1024), 2)} MB)")
        
        return safety_backup_filename
        
    except Exception as e:
        logger.error(f"❌ Safety backup failed: {e}")
        return None

# ============================================================================
# RESTORE FUNCTIONS
# ============================================================================

def restore_table_batch(client, table, batch, columns_to_exclude, progress_bar=None):
    """Restore a single batch of rows for a table (thread-safe)"""
    inserted = 0
    updated = 0
    errors = 0
    error_details = []
    
    filtered_batch = []
    for row in batch:
        if isinstance(row, dict):
            filtered_row = {k: v for k, v in row.items() if k not in columns_to_exclude}
            filtered_batch.append(filtered_row)
        else:
            filtered_batch.append(row)
    
    try:
        client.table(table).upsert(filtered_batch).execute()
        inserted += len(filtered_batch)
    except Exception as e:
        for row in filtered_batch:
            try:
                client.table(table).upsert(row).execute()
                inserted += 1
            except Exception as insert_error:
                error_str = str(insert_error)
                if 'duplicate' in error_str.lower() or '23505' in error_str:
                    try:
                        row_id = row.get('id')
                        if row_id:
                            update_row = {k: v for k, v in row.items() if k not in columns_to_exclude}
                            client.table(table).update(update_row).eq('id', row_id).execute()
                            updated += 1
                        else:
                            errors += 1
                            error_details.append(str(insert_error)[:200])
                    except:
                        errors += 1
                        error_details.append(str(insert_error)[:200])
                elif 'generated' in error_str.lower() or '428C9' in error_str:
                    errors += 1
                else:
                    errors += 1
                    error_details.append(str(insert_error)[:200])
    
    if progress_bar:
        with progress_lock:
            progress_bar.update(len(batch))
    
    return {
        'inserted': inserted,
        'updated': updated,
        'errors': errors,
        'error_details': error_details[:5]
    }

def restore_backup(backup_file, skip_safety_backup=False, max_workers=None, show_progress=None):
    """
    Restore from backup with optional safety backup and multithreading
    
    Args:
        backup_file: Backup file name
        skip_safety_backup: Skip creating safety backup
        max_workers: Number of parallel workers (None = sequential)
        show_progress: Show progress bar
    
    Returns:
        tuple: (success: bool, safety_backup_file: str or None, restore_log: dict)
    """
    backup_path = BACKUPS_DIR / backup_file
    if not backup_path.exists():
        backup_path = BACKUPS_DIR / f"{backup_file}.gz"
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False, None, {}
    
    max_workers = max_workers if max_workers else (DEFAULT_MAX_WORKERS_RESTORE if max_workers is None else 1)
    show_progress = show_progress if show_progress is not None else DEFAULT_SHOW_PROGRESS
    use_multithreading = max_workers > 1
    
    if not load_env():
        return False, None, {}
    
    # Create safety backup
    safety_backup_file = None
    if not skip_safety_backup:
        logger.info("=" * 80)
        logger.info("🛡️  STEP 1: Creating Safety Backup")
        logger.info("=" * 80)
        safety_backup_file = create_safety_backup()
        if not safety_backup_file:
            logger.error("❌ Failed to create safety backup. Restore cancelled for safety.")
            return False, None, {}
        logger.info(f"✅ Safety backup created: {safety_backup_file}")
    else:
        logger.warning("⚠️  Safety backup skipped (not recommended!)")
    
    try:
        client = get_supabase_client()
        if not client:
            return False, safety_backup_file, {}
        
        # Load backup
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STEP 2: Loading Backup Data")
        logger.info("=" * 80)
        
        is_gz = str(backup_path).endswith('.gz')
        if is_gz:
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
        else:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        
        logger.info(f"✅ Backup loaded: {backup_file}")
        logger.info(f"   Backup date: {backup_data['metadata']['backup_date']}")
        logger.info(f"   Backup type: {backup_data['metadata'].get('backup_type', 'full')}")
        
        # Validate
        is_valid, errors, warnings = validate_backup_data(backup_data)
        if not is_valid:
            logger.error("❌ Backup validation failed:")
            for error in errors:
                logger.error(f"   - {error}")
            return False, safety_backup_file, {'errors': errors, 'warnings': warnings}
        
        if warnings:
            logger.warning("⚠️  Backup validation warnings:")
            for warning in warnings:
                logger.warning(f"   - {warning}")
        
        # Get current state
        logger.info("\n" + "=" * 80)
        logger.info("📊 STEP 3: Recording Current State")
        logger.info("=" * 80)
        
        tables = backup_data['metadata']['tables']
        before_counts = get_table_row_counts(client, tables)
        logger.info(f"Recorded row counts for {len(before_counts)} tables")
        
        # Handle incremental backup
        if backup_data['metadata'].get('backup_type') == 'incremental':
            previous_timestamp = backup_data['metadata'].get('previous_backup')
            if previous_timestamp:
                logger.info(f"Loading referenced backup: {previous_timestamp}")
                prev_backup_path = BACKUPS_DIR / f"supabase_backup_{previous_timestamp}.json"
                if not prev_backup_path.exists():
                    prev_backup_path = BACKUPS_DIR / f"supabase_backup_{previous_timestamp}.json.gz"
                if prev_backup_path.exists():
                    try:
                        if str(prev_backup_path).endswith('.gz'):
                            with gzip.open(prev_backup_path, 'rt', encoding='utf-8') as f:
                                prev_backup = json.load(f)
                        else:
                            with open(prev_backup_path, 'r', encoding='utf-8') as f:
                                prev_backup = json.load(f)
                        for table, data in backup_data['data'].items():
                            if isinstance(data, dict) and data.get('_unchanged'):
                                backup_data['data'][table] = prev_backup['data'].get(table, [])
                    except Exception as e:
                        logger.warning(f"Error loading referenced backup: {e}")
        
        # Restore
        logger.info("\n" + "=" * 80)
        logger.info("🔄 STEP 4: Restoring Data")
        logger.info("=" * 80)
        if use_multithreading:
            logger.info(f"   Mode: Optimized ({max_workers} workers)")
        else:
            logger.info(f"   Mode: Standard (sequential)")
        
        restore_log = {
            'started_at': datetime.now().isoformat(),
            'backup_file': backup_file,
            'safety_backup_file': safety_backup_file,
            'before_counts': before_counts,
            'tables_restored': {},
            'tables_failed': [],
            'total_inserted': 0,
            'total_updated': 0,
            'total_errors': 0,
            'optimized': use_multithreading,
            'max_workers': max_workers if use_multithreading else None
        }
        
        excluded_columns = {
            'booking_hajj': ['booking_number'],
            'room_allotments': ['id'],
        }
        
        # Prepare restore tasks
        restore_tasks = []
        total_batches = 0
        
        for table in tables:
            data = backup_data['data'].get(table)
            
            if isinstance(data, dict) and data.get('_backup_failed'):
                logger.warning(f"Skipping {table} (backup failed)")
                restore_log['tables_failed'].append({'table': table, 'reason': 'backup_failed'})
                continue
            
            if isinstance(data, dict) and data.get('_unchanged'):
                logger.info(f"Skipping {table} (was unchanged in backup)")
                continue
            
            if not isinstance(data, list) or len(data) == 0:
                if len(data) == 0:
                    logger.info(f"  ✓ {table}: empty table (skipped)")
                continue
            
            columns_to_exclude = excluded_columns.get(table, [])
            for i in range(0, len(data), DEFAULT_BATCH_SIZE):
                batch = data[i:i + DEFAULT_BATCH_SIZE]
                restore_tasks.append((table, batch, columns_to_exclude))
                total_batches += 1
        
        # Progress bar
        if show_progress and HAS_TQDM:
            progress_bar = tqdm(total=total_batches, desc="Restoring", unit="batch")
        else:
            progress_bar = None
        
        try:
            table_results = {}
            
            if use_multithreading:
                # Parallel restore
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_task = {
                        executor.submit(restore_table_batch, client, table, batch, columns_to_exclude, progress_bar): (table, batch)
                        for table, batch, columns_to_exclude in restore_tasks
                    }
                    
                    for future in as_completed(future_to_task):
                        table, batch = future_to_task[future]
                        try:
                            result = future.result()
                            
                            if table not in table_results:
                                table_results[table] = {
                                    'inserted': 0,
                                    'updated': 0,
                                    'errors': 0,
                                    'error_details': []
                                }
                            
                            table_results[table]['inserted'] += result['inserted']
                            table_results[table]['updated'] += result['updated']
                            table_results[table]['errors'] += result['errors']
                            table_results[table]['error_details'].extend(result['error_details'])
                            
                        except Exception as e:
                            logger.error(f"  ❌ Error restoring batch for {table}: {e}")
                            if table not in table_results:
                                table_results[table] = {
                                    'inserted': 0,
                                    'updated': 0,
                                    'errors': 0,
                                    'error_details': []
                                }
            else:
                # Sequential restore
                for table, batch, columns_to_exclude in restore_tasks:
                    try:
                        result = restore_table_batch(client, table, batch, columns_to_exclude, progress_bar)
                        
                        if table not in table_results:
                            table_results[table] = {
                                'inserted': 0,
                                'updated': 0,
                                'errors': 0,
                                'error_details': []
                            }
                        
                        table_results[table]['inserted'] += result['inserted']
                        table_results[table]['updated'] += result['updated']
                        table_results[table]['errors'] += result['errors']
                        table_results[table]['error_details'].extend(result['error_details'])
                    except Exception as e:
                        logger.error(f"  ❌ Error restoring batch for {table}: {e}")
        finally:
            if progress_bar:
                progress_bar.close()
        
        # Update restore log
        restored_tables = 0
        for table, result in table_results.items():
            restore_log['tables_restored'][table] = result
            restore_log['total_inserted'] += result['inserted']
            restore_log['total_updated'] += result['updated']
            restore_log['total_errors'] += result['errors']
            
            if result['errors'] == 0:
                restored_tables += 1
                logger.info(f"  ✅ {table}: restored ({result['inserted']} inserted, {result['updated']} updated)")
            else:
                restored_tables += 1
                logger.warning(f"  ⚠️  {table}: restored with {result['errors']} errors ({result['inserted']} inserted, {result['updated']} updated)")
        
        # Verify restore
        logger.info("\n" + "=" * 80)
        logger.info("✅ STEP 5: Verifying Restore")
        logger.info("=" * 80)
        
        after_counts = get_table_row_counts(client, tables)
        restore_log['after_counts'] = after_counts
        restore_log['completed_at'] = datetime.now().isoformat()
        
        # Save restore log
        restore_log_path = SUMMARIES_DIR / f"restore_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(restore_log_path, 'w', encoding='utf-8') as f:
            json.dump(restore_log, f, indent=2, default=str, ensure_ascii=False)
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESTORE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Restored tables: {restored_tables}")
        logger.info(f"Failed tables: {len(restore_log['tables_failed'])}")
        logger.info(f"Total inserted: {restore_log['total_inserted']:,}")
        logger.info(f"Total updated: {restore_log['total_updated']:,}")
        logger.info(f"Total errors: {restore_log['total_errors']:,}")
        logger.info(f"Safety backup: {safety_backup_file}")
        if use_multithreading:
            logger.info(f"Workers: {max_workers}")
        logger.info("=" * 80)
        
        return True, safety_backup_file, restore_log
        
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False, safety_backup_file, {'error': str(e)}

def restore_backup_interactive():
    """Interactive restore with timeline selection"""
    backups = []
    backup_files = sorted(
        BACKUPS_DIR.glob('supabase_backup_*.json*'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    for idx, backup_file in enumerate(backup_files, 1):
        try:
            is_gz = str(backup_file).endswith('.gz')
            if is_gz:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            date = datetime.fromisoformat(data['metadata']['backup_date'])
            backup_type = data['metadata'].get('backup_type', 'full')
            changed_count = data['metadata'].get('changed_count', 0)
            total_rows = data['metadata'].get('total_rows', 0)
            
            backups.append({
                'index': idx,
                'filename': backup_file.name.replace('.gz', ''),
                'date': date,
                'backup_type': backup_type,
                'size_mb': size_mb,
                'changed_count': changed_count,
                'total_rows': total_rows
            })
        except:
            pass
    
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
        logger.info("\n💡 TIP: Use 'restore --safe' for automatic safety backup")
        
        confirm = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
        if confirm != 'YES':
            logger.info("Restore cancelled")
            return False
        
        success, safety_backup, log = restore_backup(selected_backup['filename'], skip_safety_backup=True)
        return success
        
    except ValueError:
        logger.error("Invalid input. Please enter a number.")
        return False
    except KeyboardInterrupt:
        logger.info("\nRestore cancelled by user")
        return False

def rollback_from_safety_backup(safety_backup_file):
    """Rollback database to safety backup state"""
    safety_backup_path = SAFETY_BACKUPS_DIR / safety_backup_file
    if not safety_backup_path.exists():
        logger.error(f"Safety backup file not found: {safety_backup_file}")
        return False
    
    logger.warning("=" * 80)
    logger.warning("⚠️  ROLLBACK OPERATION")
    logger.warning("=" * 80)
    logger.warning(f"Rolling back to: {safety_backup_file}")
    logger.warning("This will restore database to state before previous restore operation.")
    
    confirm = input("\nAre you sure you want to rollback? Type 'ROLLBACK' to confirm: ")
    if confirm != 'ROLLBACK':
        logger.info("Rollback cancelled")
        return False
    
    logger.info("\n🛡️  Creating safety backup before rollback...")
    pre_rollback_backup = create_safety_backup()
    
    logger.info(f"\n🔄 Restoring from safety backup: {safety_backup_file}")
    success, _, _ = restore_backup(safety_backup_file, skip_safety_backup=True)
    
    if success:
        logger.info("✅ Rollback completed successfully")
        if pre_rollback_backup:
            logger.info(f"💾 Pre-rollback backup saved: {pre_rollback_backup}")
    else:
        logger.error("❌ Rollback failed!")
        if pre_rollback_backup:
            logger.error(f"💡 Pre-rollback backup available: {pre_rollback_backup}")
    
    return success

def list_safety_backups():
    """List all safety backups"""
    safety_backups = sorted(SAFETY_BACKUPS_DIR.glob('safety_backup_*.json*'), reverse=True)
    if safety_backups:
        print(f"\n🛡️  Safety Backups ({len(safety_backups)}):")
        print("=" * 80)
        for backup in safety_backups[:10]:
            try:
                is_gz = str(backup).endswith('.gz')
                if is_gz:
                    with gzip.open(backup, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    with open(backup, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                size_mb = backup.stat().st_size / (1024 * 1024)
                date = datetime.fromisoformat(data['metadata']['backup_date'])
                print(f"  {backup.name}")
                print(f"    Date: {date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Size: {size_mb:.2f} MB")
                print(f"    Rows: {data['metadata'].get('total_rows', 0):,}")
                print()
            except:
                print(f"  {backup.name} (error reading)")
        print("=" * 80)
    else:
        print("\nNo safety backups found")

# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Supabase Database Backup & Restore Tool - All-in-One',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create backup (smart mode, optimized)
  %(prog)s backup
  
  # Create full backup
  %(prog)s backup --force-full
  
  # Create backup with custom workers
  %(prog)s backup --workers 10
  
  # List backups
  %(prog)s list
  
  # Safe restore (with auto safety backup)
  %(prog)s restore --safe <backup_file>
  
  # Optimized restore
  %(prog)s restore --safe <backup_file> --workers 5
  
  # Interactive restore
  %(prog)s restore --interactive
  
  # Rollback from safety backup
  %(prog)s rollback <safety_backup_file>
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('--force-full', action='store_true', help='Force full backup (ignore comparison)')
    backup_parser.add_argument('--workers', type=int, default=DEFAULT_MAX_WORKERS_BACKUP, help=f'Number of parallel workers (default: {DEFAULT_MAX_WORKERS_BACKUP}, use 1 for sequential)')
    backup_parser.add_argument('--no-compress', action='store_true', help='Disable compression')
    backup_parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available backups')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_group = restore_parser.add_mutually_exclusive_group(required=True)
    restore_group.add_argument('--file', type=str, help='Backup file to restore from')
    restore_group.add_argument('--interactive', action='store_true', help='Interactive restore with timeline selection')
    restore_parser.add_argument('--safe', action='store_true', help='Safe restore with automatic safety backup')
    restore_parser.add_argument('--workers', type=int, default=DEFAULT_MAX_WORKERS_RESTORE, help=f'Number of parallel workers (default: {DEFAULT_MAX_WORKERS_RESTORE}, use 1 for sequential)')
    restore_parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback from safety backup')
    rollback_parser.add_argument('safety_backup', type=str, help='Safety backup file to rollback from')
    
    # List safety command
    list_safety_parser = subparsers.add_parser('list-safety', help='List safety backups')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'backup':
        compress = not args.no_compress
        show_progress = not args.no_progress and HAS_TQDM
        
        if not HAS_TQDM and not args.no_progress:
            logger.warning("⚠️  tqdm not installed. Install with: pip install tqdm")
            logger.warning("   Progress bar disabled. Continuing without progress bar...")
        
        success = create_backup(
            force_full=args.force_full,
            max_workers=args.workers,
            compress=compress,
            show_progress=show_progress
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        list_backups()
    
    elif args.command == 'restore':
        if args.interactive:
            success = restore_backup_interactive()
            sys.exit(0 if success else 1)
        else:
            show_progress = not args.no_progress and HAS_TQDM
            if not HAS_TQDM and not args.no_progress:
                logger.warning("⚠️  tqdm not installed. Progress bar disabled.")
            
            success, safety_backup, log = restore_backup(
                args.file,
                skip_safety_backup=not args.safe,
                max_workers=args.workers,
                show_progress=show_progress
            )
            
            if success:
                print(f"\n✅ Restore completed!")
                if safety_backup:
                    print(f"🛡️  Safety backup: {safety_backup}")
            else:
                print(f"\n❌ Restore failed!")
                if safety_backup:
                    print(f"🛡️  Safety backup available: {safety_backup}")
            sys.exit(0 if success else 1)
    
    elif args.command == 'rollback':
        success = rollback_from_safety_backup(args.safety_backup)
        sys.exit(0 if success else 1)
    
    elif args.command == 'list-safety':
        list_safety_backups()

if __name__ == '__main__':
    main()

