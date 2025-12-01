# Database Safety Guide - Development Best Practices

## Overview

This guide provides best practices to prevent database corruption and data loss during development of the Minin app.

---

## Critical Rules

### 1. **NEVER Track the Database File in Git**

**Add to `.gitignore`:**
```gitignore
# Database files
*.db
*.sqlite
*.sqlite3
instance/
migrations/versions/*.pyc

# But DO track migrations
!migrations/
!migrations/versions/*.py
```

**Why:** Database files contain user data and can become corrupted. Migrations are the source of truth, not the database file itself.

---

### 2. **Always Backup Before Major Changes**

**Before implementing new features:**

```bash
# Backup the database
cp instance/minin.db instance/minin.db.backup_$(date +%Y%m%d_%H%M%S)

# Or use a script
python backup_db.py
```

**Create `backup_db.py`:**
```python
import shutil
from datetime import datetime
import os

def backup_database():
    """Backup the database with timestamp"""
    if os.path.exists('instance/minin.db'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'instance/minin.db.backup_{timestamp}'
        shutil.copy2('instance/minin.db', backup_name)
        print(f"✅ Database backed up to: {backup_name}")
        
        # Keep only last 5 backups
        backups = sorted([f for f in os.listdir('instance') if f.startswith('minin.db.backup_')])
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                os.remove(f'instance/{old_backup}')
                print(f"🗑️  Removed old backup: {old_backup}")
    else:
        print("❌ No database file found to backup")

if __name__ == '__main__':
    backup_database()
```

**Usage:**
```bash
python backup_db.py
```

---

### 3. **Use Migrations Properly**

**When adding new services (NO schema changes):**
```bash
# DON'T run migrations if you're only adding Python code
# Services are just Python files - they don't change the database
```

**When actually changing models:**
```bash
# Generate migration
flask db migrate -m "Add new field to user_learning_progress"

# Review the migration file BEFORE applying
# Check migrations/versions/xxxxx_add_new_field.py

# Apply migration
flask db upgrade

# If something goes wrong
flask db downgrade  # Go back one step
```

**IMPORTANT:** For this quiz implementation, you should NOT need any migrations since the schema is already complete!

---

### 4. **Separate Development and Test Databases**

**Create `config.py` if you don't have it:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/minin_dev.db'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/minin_test.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

**Use in `app.py`:**
```python
from config import config

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    # ... rest of setup
```

**Run tests:**
```bash
# Tests use test database, development database stays safe
FLASK_ENV=testing python -m pytest tests/
```

---

### 5. **Safe Service Implementation Pattern**

**When implementing services (Steps 1.1-1.5):**

```python
# services/quiz_trigger_service.py

# ✅ SAFE - Just querying, no schema changes
class QuizTriggerService:
    @staticmethod
    def should_trigger_quiz(user):
        # Query existing tables
        eligible_phrase = UserLearningProgress.query.filter(
            # ... filters
        ).first()
        return eligible_phrase

# ✅ SAFE - Just creating records with existing schema
class QuizAttemptService:
    @staticmethod
    def create_quiz_attempt(user_id, phrase_id):
        quiz_attempt = QuizAttempt(
            user_id=user_id,
            phrase_id=phrase_id,
            # ... existing fields only
        )
        db.session.add(quiz_attempt)
        db.session.flush()
        return quiz_attempt
```

**What's UNSAFE:**
```python
# ❌ DANGEROUS - Don't do this in services!
db.create_all()  # Creates tables, can corrupt if schema mismatches
db.drop_all()    # Deletes all data!
db.session.execute('ALTER TABLE ...')  # Direct SQL changes
```

---

### 6. **Check Database Integrity**

**Create `check_db.py`:**
```python
from app import create_app
from models import db
from models.user import User
from models.language import Language
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress

app = create_app('development')

def check_database():
    """Check if database is working correctly"""
    with app.app_context():
        try:
            # Check if tables exist
            print("Checking database integrity...")
            
            user_count = User.query.count()
            print(f"✅ Users table: {user_count} records")
            
            language_count = Language.query.count()
            print(f"✅ Languages table: {language_count} records")
            
            phrase_count = Phrase.query.count()
            print(f"✅ Phrases table: {phrase_count} records")
            
            progress_count = UserLearningProgress.query.count()
            print(f"✅ Learning progress table: {progress_count} records")
            
            print("\n✅ Database is healthy!")
            return True
            
        except Exception as e:
            print(f"\n❌ Database error: {e}")
            return False

if __name__ == '__main__':
    check_database()
```

**Run after implementing services:**
```bash
python check_db.py
```

---

### 7. **Recovery Steps (If Database Breaks Again)**

**Immediate Recovery:**
```bash
# 1. Stop the Flask app immediately
# Ctrl+C or kill the process

# 2. Restore from backup
cp instance/minin.db.backup_YYYYMMDD_HHMMSS instance/minin.db

# 3. Check integrity
python check_db.py

# 4. If backup doesn't exist, restore from git (if tracked)
git checkout HEAD~1 instance/minin.db  # If tracked (not recommended)

# 5. If no backup and not tracked, recreate fresh
rm instance/minin.db
flask db upgrade
python populate_languages.py  # If you have a seed script
```

**Full Reset (Last Resort):**
```bash
# Delete everything
rm -rf instance/
rm -rf migrations/

# Start fresh
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Repopulate base data
python populate_languages.py
```

---

### 8. **Debug Logging**

**Add to service files during development:**
```python
import logging

logger = logging.getLogger(__name__)

class QuizTriggerService:
    @staticmethod
    def should_trigger_quiz(user):
        logger.info(f"Checking quiz trigger for user {user.id}")
        logger.debug(f"User searches: {user.searches_since_last_quiz}/{user.quiz_frequency}")
        
        try:
            # ... service logic
            logger.info(f"Quiz trigger result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in quiz trigger: {e}", exc_info=True)
            raise
```

**Configure logging in `app.py`:**
```python
import logging

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if config_name == 'development' else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    
    # ... rest of setup
```

---

### 9. **Git Commit Strategy**

**For each implementation step:**

```bash
# 1. Backup database before starting
python backup_db.py

# 2. Implement the feature
# Create services/quiz_trigger_service.py

# 3. Test manually
python check_db.py
# Try using the app

# 4. If everything works, commit
git add services/quiz_trigger_service.py
git commit -m "Implement QuizTriggerService (Step 1.1)"

# 5. If something breaks, you can revert
git reset --hard HEAD~1

# DON'T commit database file itself
```

**Good commit messages:**
```bash
git commit -m "Add QuizTriggerService - no DB changes"
git commit -m "Add QuizAttemptService - no DB changes"
git commit -m "Add quiz endpoints - no DB changes"
```

---

### 10. **Before Starting Each Step**

**Pre-flight checklist:**

```bash
# 1. Backup
python backup_db.py

# 2. Check current state
python check_db.py

# 3. Verify no uncommitted changes
git status

# 4. Create feature branch (optional but recommended)
git checkout -b feature/quiz-trigger-service

# 5. Implement the feature

# 6. Test

# 7. Commit if successful
git commit -m "Implement QuizTriggerService"

# 8. Merge back to main
git checkout main
git merge feature/quiz-trigger-service
```

---

## What to Do Right Now

### 1. **Add Database to .gitignore**
```bash
echo "*.db" >> .gitignore
echo "instance/" >> .gitignore
git rm --cached instance/minin.db  # If tracked
git commit -m "Stop tracking database file"
```

### 2. **Create Backup Script**
```bash
# Copy the backup_db.py script from above
python backup_db.py  # Create first backup
```

### 3. **Create Check Script**
```bash
# Copy the check_db.py script from above
python check_db.py  # Verify database health
```

### 4. **Document Current State**
```bash
# Check what you have
python check_db.py > db_state_before_quiz_implementation.txt
git add db_state_before_quiz_implementation.txt
git commit -m "Document DB state before quiz implementation"
```

---

## Why The "Magic Recovery" Worked

When you did `git checkout` 2 steps back then forward again:

1. **Code was restored** to working state
2. **Database file wasn't tracked** (or was ignored), so it stayed as-is
3. **Models matched database** again, so everything worked
4. The broken code that corrupted things was removed

This worked by accident, but it's not reliable! Follow the backup strategy above.

---

## Summary

### ✅ DO:
- Backup before each major change
- Use separate test database
- Check database integrity regularly
- Commit code in small steps
- Add database files to .gitignore

### ❌ DON'T:
- Track database files in git
- Run migrations for service implementations
- Call `db.drop_all()` or `db.create_all()` in production code
- Implement multiple steps without testing
- Skip backups

---

## Emergency Contact

If database breaks again and these steps don't help, you can:
1. Check `app.log` for error messages
2. Post the error to the development chat
3. Restore from the most recent backup

**Remember:** Services are just Python code - they shouldn't break your database!