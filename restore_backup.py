#!/usr/bin/env python3
"""
Script untuk restore backup dengan timeline selection
Alias untuk: python backup_supabase.py --restore-interactive
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backup_supabase import restore_backup_interactive

if __name__ == '__main__':
    restore_backup_interactive()

