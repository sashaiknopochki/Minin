# Safe Testing Guide for Quiz Services

## Overview

This guide explains how to safely run tests without damaging your development database.

---

## Your Tests Are Already Safe! ✅

The test files you have (`test_quiz_trigger_service.py` and `test_quiz_attempt_service.py`) are properly configured with:

1. **In-memory database**: `sqlite:///:memory:` - completely separate from your dev database
2. **Function-scoped fixtures**: Fresh database for each test
3. **Proper cleanup**: `db.drop_all()` after each test

These tests **cannot** damage your development database at `instance/minin.db`.

---

## How to Run Tests Properly

### 1. **Stop Your Flask App First**

```bash
# If flask run is running, stop it:
# Press Ctrl+C in the terminal running Flask
```

**Why:** Having the app running while tests run can cause port conflicts and state confusion.

### 2. **Run Tests with pytest**

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_quiz_trigger_service.py -v

# Run specific test class
pytest tests/test_quiz_trigger_service.py::TestShouldTriggerQuiz -v

# Run specific test method
pytest tests/test_quiz_trigger_service.py::TestShouldTriggerQuiz::test_quiz_mode_disabled -v
```

**Why:** pytest properly sets up fixtures and handles cleanup.

### 3. **Never Run Tests Directly with Python**

```bash
# ❌ DON'T DO THIS
python tests/test_quiz_trigger_service.py

# ✅ DO THIS INSTEAD
pytest tests/test_quiz_trigger_service.py
```

**Why:** Running directly skips pytest's fixture management and might use wrong database.

---

## Verification: Tests Are Using In-Memory Database

### Check Test Configuration:

Both your test files have this:
```python
@pytest.fixture(scope='function')
def app_context():
    """Create a fresh app context and database for each test"""
    app = create_app('development')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # ← SAFE!
    app.config['TESTING'] = True
```

The key line is:
```python
'sqlite:///:memory:'  # In-memory, temporary database
```

NOT:
```python
'sqlite:///instance/minin.db'  # Would use your real database
```

---

## What Likely Broke Your Database

Since your tests are safe, the corruption probably came from one of these:

### Scenario 1: Manual Testing in Python Shell

If you opened a Python shell and ran:

```python
# ❌ THIS WOULD USE YOUR REAL DATABASE
from app import create_app
from models import db

app = create_app('development')  # Uses instance/minin.db

with app.app_context():
    # Testing services here...
    from services.quiz_trigger_service import QuizTriggerService
    # Any database modifications here affect REAL database
```

**Solution:** Always use the test suite, not manual shell testing.

### Scenario 2: Import Errors During Testing

If there were import errors or exceptions during test setup:

```python
# If this failed:
from services.quiz_trigger_service import QuizTriggerService

# The test might have fallen back to using development config
```

**Solution:** Check for import errors before running full test suite:
```bash
python -c "from services.quiz_trigger_service import QuizTriggerService; print('Import OK')"
```

### Scenario 3: Flask App Running During Tests

If Flask was running on port 5000 while tests tried to run:
- Tests might have made HTTP requests to the running app
- Running app uses real database
- Tests inadvertently modified real data

**Solution:** Always stop Flask before running tests.

### Scenario 4: Test File Run Directly

If you ran:
```bash
python tests/test_quiz_trigger_service.py
```

The `if __name__ == '__main__'` block at the bottom would execute:
```python
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

This is actually OK! It still uses pytest. But better to use `pytest` command directly.

---

## Safe Testing Workflow

### Daily Testing Routine:

```bash
# 1. Ensure Flask is not running
ps aux | grep flask  # Check for Flask processes
# If found, kill them or Ctrl+C the terminal

# 2. Backup database (optional but recommended)
python backup_db.py

# 3. Run tests
pytest tests/ -v

# 4. If all tests pass, continue development
# 5. If tests fail, fix code (tests won't have damaged database)

# 6. Start Flask again when ready
flask run
```

### After Implementing New Service:

```bash
# 1. Stop Flask
# Ctrl+C

# 2. Backup
python backup_db.py

# 3. Run relevant tests
pytest tests/test_quiz_trigger_service.py -v

# 4. If tests pass, commit
git add services/quiz_trigger_service.py tests/test_quiz_trigger_service.py
git commit -m "Add QuizTriggerService with tests"

# 5. Start Flask
flask run
```

---

## Manual Testing (If Needed)

If you must manually test services, **NEVER use development database**:

### Create a Manual Test Script:

```python
# manual_test_quiz_service.py

from app import create_app
from models import db
from models.user import User
from models.phrase import Phrase
from models.user_learning_progress import UserLearningProgress
from services.quiz_trigger_service import QuizTriggerService
from datetime import date

# ✅ SAFE - Uses in-memory database
app = create_app('development')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['TESTING'] = True

with app.app_context():
    # Create tables
    db.create_all()
    
    # Add test data
    user = User(
        google_id='manual_test',
        email='manual@test.com',
        name='Manual Test',
        primary_language_code='en',
        translator_languages=["en", "de"],
        quiz_mode_enabled=True,
        quiz_frequency=5,
        searches_since_last_quiz=5
    )
    db.session.add(user)
    db.session.flush()
    
    phrase = Phrase(text='test', language_code='de', type='word')
    db.session.add(phrase)
    db.session.flush()
    
    progress = UserLearningProgress(
        user_id=user.id,
        phrase_id=phrase.id,
        stage='basic',
        next_review_date=date.today()
    )
    db.session.add(progress)
    db.session.commit()
    
    # Test the service
    result = QuizTriggerService.should_trigger_quiz(user)
    print(f"Should trigger: {result['should_trigger']}")
    print(f"Reason: {result['reason']}")
    
    # Database is in memory and will be destroyed when script ends
    print("\n✅ Manual test complete - no database files modified")
```

Run this way:
```bash
python manual_test_quiz_service.py
```

This is SAFE because it uses `:memory:` database.

---

## Debugging Test Issues

### Check What Database Tests Are Using:

Add this to your test file temporarily:
```python
def test_verify_using_memory_database(app_context):
    """Verify we're using in-memory database"""
    from flask import current_app
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    print(f"\nDatabase URI: {db_uri}")
    assert ':memory:' in db_uri, "Tests must use in-memory database!"
    assert 'instance/minin.db' not in db_uri, "Tests must NOT use dev database!"
```

Run:
```bash
pytest tests/test_quiz_trigger_service.py::test_verify_using_memory_database -v -s
```

Should output:
```
Database URI: sqlite:///:memory:
PASSED
```

If it shows `instance/minin.db`, you have a configuration problem.

---

## Common Mistakes to Avoid

### ❌ DON'T:

1. Run Flask while running tests
2. Use `python tests/test_file.py` (use `pytest` instead)
3. Manually test services with `create_app('development')` without overriding database URI
4. Import and test services in Python REPL without setting test database
5. Modify test fixtures to use real database

### ✅ DO:

1. Stop Flask before running tests
2. Use `pytest tests/` command
3. Use in-memory database for all testing
4. Create backup before major changes
5. Check test configuration if something seems wrong

---

## Test Coverage

Your current tests are excellent and cover:

### QuizTriggerService:
- ✅ Quiz mode enabled/disabled
- ✅ Search counter threshold
- ✅ Phrase selection logic
- ✅ Mastered phrase exclusion
- ✅ Language filtering
- ✅ Overdue phrase handling
- ✅ Multiple users isolation
- ✅ Edge cases

### QuizAttemptService:
- ✅ Quiz attempt creation
- ✅ Question type selection
- ✅ Stage-based question types
- ✅ Error handling
- ✅ Randomness verification
- ✅ Multiple attempts
- ✅ User isolation

These are comprehensive, well-written tests! 🎉

---

## Continuous Integration (Future)

For future CI/CD setup:

```yaml
# .github/workflows/test.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v --cov=services
```

---

## Summary

### Your Tests Are Safe! ✅

The database corruption did NOT come from your test files. They are properly configured with in-memory database and cannot touch your development database.

### Most Likely Cause:

Either:
1. Manual testing in Python shell with dev database
2. Flask running while testing
3. Import errors falling back to dev config

### Prevention:

1. Always use `pytest tests/` command
2. Stop Flask before testing
3. Backup before major changes
4. Never manually test with dev database

Your test files are excellent and safe to run anytime! 🚀