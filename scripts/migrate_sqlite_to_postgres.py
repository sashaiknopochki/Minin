#!/usr/bin/env python3
"""
Data Migration Script: SQLite to PostgreSQL (Supabase)

This script migrates all data from your local SQLite database to the PostgreSQL
database at Supabase. It preserves all IDs, relationships, and data integrity.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Features:
- Connects to both SQLite and PostgreSQL databases
- Migrates data in correct order (respecting foreign key constraints)
- Preserves all primary keys and relationships
- Shows progress with detailed output
- Performs data verification after migration
- Can be run multiple times safely (skips duplicates)
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, MetaData, Table, select, insert, func, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL"""

    def __init__(self, sqlite_path, postgres_uri):
        """Initialize connections to both databases"""
        print("=" * 80)
        print("DATABASE MIGRATION: SQLite → PostgreSQL (Supabase)")
        print("=" * 80)
        print()

        # Create engines
        print(f"📂 Connecting to SQLite database: {sqlite_path}")
        self.sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')

        print(f"🐘 Connecting to PostgreSQL database...")
        self.postgres_engine = create_engine(postgres_uri)

        # Test connections
        try:
            with self.sqlite_engine.connect() as conn:
                print("   ✓ SQLite connection successful")
        except Exception as e:
            print(f"   ✗ SQLite connection failed: {e}")
            sys.exit(1)

        try:
            with self.postgres_engine.connect() as conn:
                print("   ✓ PostgreSQL connection successful")
        except Exception as e:
            print(f"   ✗ PostgreSQL connection failed: {e}")
            sys.exit(1)

        print()

        # Reflect table schemas
        self.sqlite_metadata = MetaData()
        self.sqlite_metadata.reflect(bind=self.sqlite_engine)

        self.postgres_metadata = MetaData()
        self.postgres_metadata.reflect(bind=self.postgres_engine)

        # Create sessions
        SQLiteSession = sessionmaker(bind=self.sqlite_engine)
        self.sqlite_session = SQLiteSession()

        PostgresSession = sessionmaker(bind=self.postgres_engine)
        self.postgres_session = PostgresSession()

    def count_records(self, engine, table_name):
        """Count records in a table"""
        try:
            metadata = MetaData()
            metadata.reflect(bind=engine)
            if table_name not in metadata.tables:
                return 0
            table = metadata.tables[table_name]
            with engine.connect() as conn:
                result = conn.execute(select(func.count()).select_from(table))
                return result.scalar()
        except Exception:
            return 0

    def migrate_table(self, table_name, batch_size=100):
        """Migrate a single table from SQLite to PostgreSQL"""
        print(f"📊 Migrating table: {table_name}")

        # Check if table exists in both databases
        if table_name not in self.sqlite_metadata.tables:
            print(f"   ⚠️  Table '{table_name}' not found in SQLite, skipping")
            return 0

        if table_name not in self.postgres_metadata.tables:
            print(f"   ⚠️  Table '{table_name}' not found in PostgreSQL, skipping")
            return 0

        # Get table objects
        sqlite_table = self.sqlite_metadata.tables[table_name]
        postgres_table = self.postgres_metadata.tables[table_name]

        # Count source records
        with self.sqlite_engine.connect() as conn:
            total_records = conn.execute(select(func.count()).select_from(sqlite_table)).scalar()

        if total_records == 0:
            print(f"   ℹ️  No records to migrate")
            return 0

        print(f"   Found {total_records} records in SQLite")

        # Read all data from SQLite
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(select(sqlite_table))
            rows = result.fetchall()
            columns = result.keys()

        # Prepare data for PostgreSQL
        records_to_insert = []
        for row in rows:
            record = dict(zip(columns, row))
            records_to_insert.append(record)

        # Insert into PostgreSQL in batches
        migrated_count = 0
        skipped_count = 0

        with self.postgres_engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                for i in range(0, len(records_to_insert), batch_size):
                    batch = records_to_insert[i:i + batch_size]

                    for record in batch:
                        try:
                            # Try to insert record
                            conn.execute(insert(postgres_table).values(**record))
                            migrated_count += 1
                        except Exception as e:
                            # Record likely already exists (duplicate key)
                            if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                                skipped_count += 1
                            else:
                                # Unknown error, re-raise
                                raise

                    # Show progress
                    progress = min(i + batch_size, len(records_to_insert))
                    print(f"   Progress: {progress}/{total_records} records processed...", end='\r')

                # Commit transaction
                trans.commit()
                print(f"   ✓ Migrated {migrated_count} records (skipped {skipped_count} duplicates)")

                # Reset sequence for auto-increment columns (if table has primary key)
                primary_key_columns = [col.name for col in postgres_table.columns if col.primary_key]
                if primary_key_columns and records_to_insert:
                    pk_col = primary_key_columns[0]
                    max_id = max(record.get(pk_col, 0) for record in records_to_insert if record.get(pk_col) is not None)
                    if max_id and isinstance(max_id, int):
                        sequence_name = f"{table_name}_{pk_col}_seq"
                        try:
                            conn.execute(text(f"SELECT setval('{sequence_name}', {max_id}, true)"))
                            conn.commit()
                            print(f"   ✓ Reset sequence {sequence_name} to {max_id}")
                        except Exception:
                            # Sequence might not exist or have different name
                            pass

            except Exception as e:
                trans.rollback()
                print(f"   ✗ Migration failed: {e}")
                raise

        return migrated_count

    def verify_migration(self):
        """Verify that data was migrated correctly"""
        print()
        print("=" * 80)
        print("VERIFICATION: Comparing record counts")
        print("=" * 80)
        print()

        tables = ['users', 'languages', 'phrases', 'phrase_translations',
                  'user_searches', 'sessions', 'user_learning_progress',
                  'quiz_attempts', 'llm_pricing']

        all_match = True

        print(f"{'Table':<25} {'SQLite':<15} {'PostgreSQL':<15} {'Status'}")
        print("-" * 80)

        for table_name in tables:
            sqlite_count = self.count_records(self.sqlite_engine, table_name)
            postgres_count = self.count_records(self.postgres_engine, table_name)

            status = "✓ Match" if sqlite_count == postgres_count else "✗ Mismatch"
            if sqlite_count != postgres_count:
                all_match = False

            print(f"{table_name:<25} {sqlite_count:<15} {postgres_count:<15} {status}")

        print("-" * 80)

        if all_match:
            print("\n✓ All tables verified successfully!")
        else:
            print("\n⚠️  Some tables have mismatched counts. Please review.")

        return all_match

    def run_migration(self):
        """Execute full migration in correct order"""
        print("Starting data migration...")
        print()

        # Migration order (respecting foreign key constraints)
        migration_order = [
            'languages',              # No dependencies
            'users',                  # No dependencies
            'llm_pricing',            # No dependencies
            'phrases',                # Depends on languages
            'sessions',               # Depends on users
            'phrase_translations',    # Depends on phrases and languages
            'user_searches',          # Depends on users, phrases, sessions
            'user_learning_progress', # Depends on users and phrases
            'quiz_attempts',          # Depends on users and phrases
        ]

        total_migrated = 0

        for table_name in migration_order:
            count = self.migrate_table(table_name)
            total_migrated += count
            print()

        print("=" * 80)
        print(f"Migration completed! Total records migrated: {total_migrated}")
        print("=" * 80)
        print()

        # Verify migration
        self.verify_migration()

    def close(self):
        """Close database connections"""
        self.sqlite_session.close()
        self.postgres_session.close()
        self.sqlite_engine.dispose()
        self.postgres_engine.dispose()


def main():
    """Main entry point"""
    # Configuration
    sqlite_path = 'instance/database.db'
    postgres_uri = os.getenv('DATABASE_URI')

    if not postgres_uri:
        print("❌ Error: DATABASE_URI environment variable not set!")
        print("Please ensure your .env file contains DATABASE_URI")
        sys.exit(1)

    if not os.path.exists(sqlite_path):
        print(f"❌ Error: SQLite database not found at {sqlite_path}")
        sys.exit(1)

    # Confirm with user
    print("This script will migrate data from SQLite to PostgreSQL.")
    print(f"Source: {sqlite_path}")
    print(f"Target: PostgreSQL at Supabase")
    print()
    response = input("Continue? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        sys.exit(0)

    print()

    # Run migration
    migrator = DatabaseMigrator(sqlite_path, postgres_uri)

    try:
        migrator.run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        migrator.close()

    print()
    print("=" * 80)
    print("🎉 Migration complete! Your data is now in PostgreSQL.")
    print("=" * 80)


if __name__ == '__main__':
    main()