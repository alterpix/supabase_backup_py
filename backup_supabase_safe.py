#!/usr/bin/env python3
"""
Script Otomatisasi Backup Database Supabase dengan Safety Features
- Safety backup otomatis sebelum restore
- Rollback mechanism jika restore gagal
- Validasi data sebelum restore
- Recovery mechanism
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
import shutil

# Import functions from main backup script
# Note: We need to import the module and access its functions
import backup_supabase as backup_module

# Get directories and functions from backup module
# Use same directory structure as backup_supabase.py
BACKUP_DIR = Path(__file__).resolve().parent
BACKUPS_DIR = BACKUP_DIR / 'backups'
SUMMARIES_DIR = BACKUP_DIR / 'summaries'
LOGS_DIR = BACKUP_DIR / 'logs'

# Import functions from backup module
load_env = backup_module.load_env
get_supabase_client = backup_module.get_supabase_client
get_all_tables = backup_module.get_all_tables
fetch_table_data = backup_module.fetch_table_data
calculate_table_hash = backup_module.calculate_table_hash

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SAFETY_BACKUPS_DIR = BACKUPS_DIR.parent / 'safety_backups'
SAFETY_BACKUPS_DIR.mkdir(exist_ok=True)

def create_safety_backup():
    """Create safety backup before restore - snapshot current state"""
    if not load_env():
        return None
    
    try:
        client = get_supabase_client()
        tables = get_all_tables()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_backup_filename = f"safety_backup_{timestamp}.json"
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
        
        # Save safety backup
        with open(safety_backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        logger.info(f"✅ Safety backup created: {safety_backup_filename} ({round(safety_backup_path.stat().st_size / (1024 * 1024), 2)} MB)")
        
        return safety_backup_filename
        
    except Exception as e:
        logger.error(f"❌ Safety backup failed: {e}")
        return None

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
    
    # Check for critical tables
    critical_tables = ['users', 'packages', 'bookings']
    for table in critical_tables:
        if table not in backup_data['data']:
            warnings.append(f"Critical table '{table}' not found in backup")
    
    # Check data integrity
    for table, data in backup_data['data'].items():
        if isinstance(data, dict) and data.get('_backup_failed'):
            warnings.append(f"Table '{table}' had backup errors")
        elif isinstance(data, list):
            # Check for required fields in first row
            if len(data) > 0 and isinstance(data[0], dict):
                if 'id' not in data[0] and table not in ['room_allotments']:
                    warnings.append(f"Table '{table}' rows missing 'id' field")
    
    return len(errors) == 0, errors, warnings

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

def restore_backup_safe(backup_file, skip_safety_backup=False):
    """
    Safe restore with automatic safety backup and rollback mechanism
    
    Args:
        backup_file: Backup file to restore from
        skip_safety_backup: Skip creating safety backup (not recommended)
    
    Returns:
        tuple: (success: bool, safety_backup_file: str or None, restore_log: dict)
    """
    backup_path = BACKUPS_DIR / backup_file
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_file}")
        return False, None, {}
    
    if not load_env():
        return False, None, {}
    
    # Step 1: Create safety backup
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
        
        # Step 2: Load and validate backup
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STEP 2: Validating Backup Data")
        logger.info("=" * 80)
        
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
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
        
        logger.info("✅ Backup validation passed")
        
        # Step 3: Get current state (for rollback reference)
        logger.info("\n" + "=" * 80)
        logger.info("📊 STEP 3: Recording Current State")
        logger.info("=" * 80)
        
        tables = backup_data['metadata']['tables']
        before_counts = get_table_row_counts(client, tables)
        logger.info(f"Recorded row counts for {len(before_counts)} tables")
        
        # Step 4: Handle incremental backup
        if backup_data['metadata'].get('backup_type') == 'incremental':
            previous_timestamp = backup_data['metadata'].get('previous_backup')
            if previous_timestamp:
                logger.info(f"Loading referenced backup: {previous_timestamp}")
                prev_backup_path = BACKUPS_DIR / f"supabase_backup_{previous_timestamp}.json"
                if prev_backup_path.exists():
                    with open(prev_backup_path, 'r', encoding='utf-8') as f:
                        prev_backup = json.load(f)
                    for table, data in backup_data['data'].items():
                        if isinstance(data, dict) and data.get('_unchanged'):
                            backup_data['data'][table] = prev_backup['data'].get(table, [])
        
        # Step 5: Restore with tracking
        logger.info("\n" + "=" * 80)
        logger.info("🔄 STEP 4: Restoring Data")
        logger.info("=" * 80)
        
        restore_log = {
            'started_at': datetime.now().isoformat(),
            'backup_file': backup_file,
            'safety_backup_file': safety_backup_file,
            'before_counts': before_counts,
            'tables_restored': {},
            'tables_failed': [],
            'total_inserted': 0,
            'total_updated': 0,
            'total_errors': 0
        }
        
        restored_tables = 0
        failed_tables = []
        
        # Define columns to exclude
        excluded_columns = {
            'booking_hajj': ['booking_number'],
            'room_allotments': ['id'],
        }
        
        for table in tables:
            data = backup_data['data'].get(table)
            
            if isinstance(data, dict) and data.get('_backup_failed'):
                logger.warning(f"Skipping {table} (backup failed)")
                failed_tables.append(table)
                restore_log['tables_failed'].append({'table': table, 'reason': 'backup_failed'})
                continue
            
            if isinstance(data, dict) and data.get('_unchanged'):
                logger.info(f"Skipping {table} (was unchanged in backup)")
                continue
            
            if not isinstance(data, list):
                logger.warning(f"Skipping {table} (invalid data format)")
                failed_tables.append(table)
                restore_log['tables_failed'].append({'table': table, 'reason': 'invalid_format'})
                continue
            
            if len(data) == 0:
                logger.info(f"  ✓ {table}: empty table (skipped)")
                continue
            
            try:
                logger.info(f"Restoring {table} ({len(data)} rows)...")
                
                columns_to_exclude = excluded_columns.get(table, [])
                batch_size = 100
                inserted = 0
                updated = 0
                errors = 0
                error_details = []
                
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    
                    # Remove excluded columns
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
                        # Fallback: insert one by one
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
                                    logger.warning(f"  ⚠️  Skipping row due to generated column")
                                    errors += 1
                                else:
                                    errors += 1
                                    error_details.append(str(insert_error)[:200])
                
                if errors == 0:
                    restored_tables += 1
                    logger.info(f"  ✅ {table}: restored ({inserted} inserted, {updated} updated)")
                    restore_log['tables_restored'][table] = {
                        'inserted': inserted,
                        'updated': updated,
                        'errors': 0
                    }
                else:
                    logger.warning(f"  ⚠️  {table}: restored with {errors} errors ({inserted} inserted, {updated} updated)")
                    restored_tables += 1
                    restore_log['tables_restored'][table] = {
                        'inserted': inserted,
                        'updated': updated,
                        'errors': errors,
                        'error_details': error_details[:5]  # Keep first 5 errors
                    }
                
                restore_log['total_inserted'] += inserted
                restore_log['total_updated'] += updated
                restore_log['total_errors'] += errors
                
            except Exception as e:
                logger.error(f"  ❌ {table}: {e}")
                failed_tables.append(table)
                restore_log['tables_failed'].append({
                    'table': table,
                    'reason': str(e)[:200]
                })
        
        # Step 6: Verify restore
        logger.info("\n" + "=" * 80)
        logger.info("✅ STEP 5: Verifying Restore")
        logger.info("=" * 80)
        
        after_counts = get_table_row_counts(client, tables)
        restore_log['after_counts'] = after_counts
        restore_log['completed_at'] = datetime.now().isoformat()
        
        # Compare counts
        verification_passed = True
        for table in tables:
            before = before_counts.get(table, 0)
            after = after_counts.get(table, 0)
            expected = len(backup_data['data'].get(table, [])) if isinstance(backup_data['data'].get(table), list) else before
            
            if table in restore_log['tables_restored']:
                logger.info(f"  {table}: {before} → {after} rows (expected: {expected})")
                if after < expected * 0.9:  # Allow 10% tolerance
                    logger.warning(f"    ⚠️  Row count lower than expected!")
                    verification_passed = False
        
        # Step 7: Save restore log
        restore_log_path = SUMMARIES_DIR / f"restore_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(restore_log_path, 'w', encoding='utf-8') as f:
            json.dump(restore_log, f, indent=2, default=str, ensure_ascii=False)
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESTORE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Restored tables: {restored_tables}")
        logger.info(f"Failed tables: {len(failed_tables)}")
        logger.info(f"Total inserted: {restore_log['total_inserted']:,}")
        logger.info(f"Total updated: {restore_log['total_updated']:,}")
        logger.info(f"Total errors: {restore_log['total_errors']:,}")
        logger.info(f"Safety backup: {safety_backup_file}")
        logger.info(f"Restore log: {restore_log_path.name}")
        logger.info("=" * 80)
        
        if failed_tables:
            logger.warning(f"⚠️  Failed tables: {', '.join(failed_tables)}")
            logger.warning(f"💡 Use safety backup '{safety_backup_file}' to rollback if needed")
        
        if not verification_passed:
            logger.warning("⚠️  Verification warnings detected. Please review restore log.")
        
        return True, safety_backup_file, restore_log
        
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        import traceback
        traceback.print_exc()
        
        if safety_backup_file:
            logger.error(f"💡 Safety backup available: {safety_backup_file}")
            logger.error(f"   Use restore_backup_safe('{safety_backup_file}') to rollback")
        
        return False, safety_backup_file, {'error': str(e)}

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
    
    # Create another safety backup before rollback (safety of safety!)
    logger.info("\n🛡️  Creating safety backup before rollback...")
    pre_rollback_backup = create_safety_backup()
    
    # Restore from safety backup
    logger.info(f"\n🔄 Restoring from safety backup: {safety_backup_file}")
    success, _, _ = restore_backup_safe(safety_backup_file, skip_safety_backup=True)
    
    if success:
        logger.info("✅ Rollback completed successfully")
        if pre_rollback_backup:
            logger.info(f"💾 Pre-rollback backup saved: {pre_rollback_backup}")
    else:
        logger.error("❌ Rollback failed!")
        if pre_rollback_backup:
            logger.error(f"💡 Pre-rollback backup available: {pre_rollback_backup}")
    
    return success

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Safe Supabase Database Restore with Safety Features')
    parser.add_argument('--restore', type=str, help='Restore from backup file (filename)')
    parser.add_argument('--rollback', type=str, help='Rollback from safety backup file')
    parser.add_argument('--list-safety', action='store_true', help='List safety backups')
    parser.add_argument('--skip-safety', action='store_true', help='Skip safety backup (not recommended)')
    
    args = parser.parse_args()
    
    if args.list_safety:
        safety_backups = sorted(SAFETY_BACKUPS_DIR.glob('safety_backup_*.json'), reverse=True)
        if safety_backups:
            print(f"\n🛡️  Safety Backups ({len(safety_backups)}):")
            print("=" * 80)
            for backup in safety_backups[:10]:
                try:
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
    elif args.rollback:
        rollback_from_safety_backup(args.rollback)
    elif args.restore:
        success, safety_backup, log = restore_backup_safe(args.restore, skip_safety_backup=args.skip_safety)
        if success:
            print(f"\n✅ Restore completed!")
            if safety_backup:
                print(f"🛡️  Safety backup: {safety_backup}")
        else:
            print(f"\n❌ Restore failed!")
            if safety_backup:
                print(f"🛡️  Safety backup available: {safety_backup}")
            sys.exit(1)
    else:
        parser.print_help()

