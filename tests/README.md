# Tests

This directory contains all tests for the Minin application.

## Test Files

- **test_models.py** - Integration tests for all SQLAlchemy models
- **test_auth.py** - Integration tests for Google OAuth authentication

## Running Tests

### Run All Tests

```bash
# From the Minin directory
python -m unittest discover tests

# Or run with verbose output
python -m unittest discover tests -v
```

### Run Specific Test File

```bash
# Run model tests
python tests/test_models.py

# Run auth tests
python tests/test_auth.py

# Or using unittest
python -m unittest tests.test_models
python -m unittest tests.test_auth
```

### Run from PyCharm

Right-click on the test file or test class and select "Run 'test_xxx'"

## Test Database

Tests create temporary databases:
- `instance/test_database.db` - for model tests
- `instance/test_auth.db` - for auth tests

These are automatically cleaned up after tests complete.

## Requirements

All test dependencies are in `requirements.txt`. No additional packages needed - tests use Python's built-in `unittest` framework.