"""
Database Backup Script
Run this before making any major changes to backup your database
"""

import shutil
from datetime import datetime
import os
import glob


def backup_database():
    """Backup the database with timestamp"""
    db_path = 'instance/database.db'

    if not os.path.exists(db_path):
        print("❌ No database file found to backup")
        return False

    # Create backup with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'instance/database.db.backup_{timestamp}'

    try:
        shutil.copy2(db_path, backup_name)
        file_size = os.path.getsize(backup_name) / 1024  # KB
        print(f"✅ Database backed up to: {backup_name}")
        print(f"📦 Backup size: {file_size:.2f} KB")

        # Keep only last 10 backups
        backups = sorted(glob.glob('instance/database.db.backup_*'))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(old_backup)
                print(f"🗑️  Removed old backup: {os.path.basename(old_backup)}")

        print(f"\n💾 Total backups: {min(len(backups), 10)}")
        return True

    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("DATABASE BACKUP")
    print("=" * 50)
    backup_database()
    print("=" * 50)
