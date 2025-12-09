# Utility Scripts

This directory contains utility scripts for database management, development, and debugging.

## Database Scripts

### `populate_languages.py`

**Purpose**: Initialize the `languages` table with supported language data

**Usage**:
```bash
python scripts/populate_languages.py
```

**When to use**:
- After initial database setup
- When adding new supported languages
- When resetting the languages table

**Details**: Populates the database with language definitions including ISO 639-1 codes, names, and native names for all supported languages in the application.

---

### `backup_db.py`

**Purpose**: Create timestamped backups of the SQLite database

**Usage**:
```bash
python scripts/backup_db.py
```

**When to use**:
- Before running migrations
- Before making significant data changes
- As part of regular backup routines

**Details**: Creates a backup in the `instance/` directory with timestamp (e.g., `database_backup_20251209_143022.db`)

---

### `check_db.py`

**Purpose**: Database health check and verification

**Usage**:
```bash
python scripts/check_db.py
```

**When to use**:
- Diagnosing database issues
- Verifying data integrity
- Checking table structure after migrations

**Details**: Runs diagnostic queries to verify database structure, relationships, and data consistency.

---

## Development & Debugging Scripts

### `debug_quiz_data.py`

**Purpose**: Inspect and debug quiz-related data

**Usage**:
```bash
python scripts/debug_quiz_data.py
```

**When to use**:
- Debugging quiz generation issues
- Inspecting quiz attempt history
- Verifying quiz data relationships

**Details**: Provides detailed output of quiz attempts, questions, and related learning progress data for debugging purposes.

---

### `demo_caching_workflow.py`

**Purpose**: Demonstrate the multi-language translation caching system

**Usage**:
```bash
python scripts/demo_caching_workflow.py
```

**When to use**:
- Understanding how translation caching works
- Testing cache behavior
- Demonstrating the system to new developers

**Details**: Interactive demonstration of how phrases are cached across multiple target languages, showing cache hits and misses.

---

### `watch_logs.sh`

**Purpose**: Real-time log monitoring script

**Usage**:
```bash
./scripts/watch_logs.sh
```

**When to use**:
- Debugging application behavior in real-time
- Monitoring during development
- Troubleshooting production issues

**Details**: Shell script that tails application logs with color coding and filtering for easier debugging.

---

## Notes

- All scripts should be run from the project root directory
- Ensure your virtual environment is activated before running Python scripts
- Database scripts require the Flask app context and will use the `DATABASE_URI` from your `.env` file
- Make sure `watch_logs.sh` has execute permissions: `chmod +x scripts/watch_logs.sh`