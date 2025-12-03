# Logging Guide for Minin

## Overview

The Minin application uses comprehensive file and console logging to track application behavior, errors, and debugging information.

## Log Locations

### 1. **Console Output** (Terminal)
When you run `python app.py`, logs appear directly in your terminal in real-time.

### 2. **Log Files** (`logs/` directory)
All logs are automatically saved to files with rotation:
- **Primary log**: `logs/minin.log`
- **Rotated logs**: `logs/minin.log.1`, `logs/minin.log.2`, etc.
- **Rotation**: When `minin.log` reaches 10MB, it rotates to `.1`, keeping last 10 files

## Log Format

### Console Format (Terminal)
```
LEVEL    [module_name] message
```
Example:
```
INFO     [answer_evaluation_service] Quiz attempt 123 evaluated: was_correct=True
ERROR    [learning_progress_service] Quiz attempt not found: 456
```

### File Format (logs/minin.log)
```
timestamp LEVEL    [module:line] message
```
Example:
```
2025-12-03 18:54:07 INFO     [answer_evaluation_service:126] Quiz attempt 123 evaluated
2025-12-03 18:54:08 ERROR    [learning_progress_service:278] Quiz attempt not found: 456
```

## Log Levels

The application uses Python's standard logging levels:

| Level | When Used | Appears In |
|-------|-----------|------------|
| **DEBUG** | Detailed flow information (development only) | File always, Console in dev mode |
| **INFO** | Key operations and state changes | File + Console |
| **WARNING** | Degraded functionality or unexpected conditions | File + Console |
| **ERROR** | Errors that need attention | File + Console |

### Development vs Production

**Development Mode** (`debug=True`):
- Console shows: DEBUG and above
- File shows: DEBUG and above
- More verbose output for debugging

**Production Mode** (`debug=False`):
- Console shows: INFO and above
- File shows: DEBUG and above (for post-incident analysis)

## Viewing Logs

### Method 1: Watch Terminal (Real-time)
```bash
cd /Users/grace_scale/PycharmProjects/Minin/Minin
python app.py
```

All logs appear in your terminal as they happen.

### Method 2: View Log File
```bash
# View entire log file
cat logs/minin.log

# View last 50 lines
tail -50 logs/minin.log

# Follow log in real-time (like tail -f)
tail -f logs/minin.log

# View with timestamps and colors
tail -f logs/minin.log | grep --color -E "ERROR|WARNING|$"
```

### Method 3: Search Logs
```bash
# Find all errors
grep "ERROR" logs/minin.log

# Find errors from specific service
grep "answer_evaluation_service.*ERROR" logs/minin.log

# Find logs for specific quiz attempt
grep "Quiz attempt 123" logs/minin.log

# Find logs from specific time range
grep "2025-12-03 18:5" logs/minin.log
```

### Method 4: Multi-pane Terminal (Recommended)
Use `tmux` or split terminal windows:

**Window 1**: Run Flask app
```bash
python app.py
```

**Window 2**: Watch logs with highlighting
```bash
tail -f logs/minin.log | grep --color -E "ERROR|WARNING|$"
```

**Window 3**: Search logs as needed
```bash
grep "quiz_attempt" logs/minin.log
```

## Service-Specific Logs

Each service logs different events:

### AnswerEvaluationService
```
ERROR    Invalid quiz_attempt_id: abc
ERROR    Empty user_answer for quiz_attempt_id=123
ERROR    Quiz attempt not found: 456
WARNING  Quiz attempt 789 has malformed prompt_json
INFO     Quiz attempt 123 evaluated: user_answer='cat', was_correct=True
```

### LearningProgressService
```
ERROR    Invalid quiz_attempt_id: -1
ERROR    Quiz attempt 123 missing user_id
ERROR    No learning progress found for quiz attempt 456
ERROR    Invalid learning stage: 'invalid'
DEBUG    Stage advanced: basic -> intermediate
INFO     Updated learning progress: user_id=1, phrase_id=42, was_correct=True
```

### QuizTriggerService
```
DEBUG    Quiz mode disabled for user_id=1
INFO     No phrases due for review for user_id=2
WARNING  User 3 missing quiz_frequency, defaulting to disabled
ERROR    Unexpected error in should_trigger_quiz for user_id=4: ...
```

### QuestionGenerationService
```
DEBUG    API call attempt 1/3
INFO     Generated question for quiz_attempt 123: phrase='Katze'
WARNING  LLM generation failed: RateLimitError. Using fallback question generation.
ERROR    Failed to parse LLM response as JSON: ...
```

## Common Log Analysis Tasks

### Find Quiz Errors
```bash
grep -E "(quiz|Quiz)" logs/minin.log | grep ERROR
```

### Track User Quiz Session
```bash
# Replace with actual user_id
grep "user_id=1" logs/minin.log
```

### Monitor LLM API Issues
```bash
grep "LLM\|OpenAI\|API" logs/minin.log
```

### Check Database Rollbacks
```bash
grep "rollback" logs/minin.log
```

### Find Validation Failures
```bash
grep "ValueError\|Invalid\|missing" logs/minin.log
```

## Log Rotation Details

**Automatic Rotation:**
- Happens when `logs/minin.log` reaches 10MB
- Old file renamed to `minin.log.1`
- Previous `.1` becomes `.2`, etc.
- Oldest file (`.10`) is deleted
- No manual intervention needed

**Manual Rotation (if needed):**
```bash
# Archive old logs
mv logs/minin.log logs/minin_backup_$(date +%Y%m%d).log

# Flask will create new minin.log automatically
```

## Troubleshooting

### Issue: No logs appearing
**Solution:** Check that logging is configured:
```python
# In app.py, should see:
configure_logging(app)  # Line 99
```

### Issue: Logs directory doesn't exist
**Solution:** It's created automatically, but you can create it:
```bash
mkdir -p logs
```

### Issue: Log file too large
**Solution:** Rotation happens automatically at 10MB. To change:
```python
# In app.py, line 45:
maxBytes=10 * 1024 * 1024,  # Change 10 to desired MB
```

### Issue: Too much output in console
**Solution:** Filter to specific levels:
```bash
# Show only errors and warnings
tail -f logs/minin.log | grep -E "ERROR|WARNING"
```

## Best Practices

1. **Keep Terminal Visible**: Always have your Flask terminal visible during development
2. **Check Logs After Errors**: When something fails, immediately check logs
3. **Search Before Debugging**: Search logs for error messages before diving into code
4. **Use grep Liberally**: Filter logs to find exactly what you need
5. **Don't Commit Logs**: The `logs/` directory is in `.gitignore` - keep it that way

## Integration with Browser

**Important:** Backend logs do NOT appear in browser console!

- **Backend logs**: Terminal + `logs/minin.log`
- **Frontend logs**: Browser DevTools Console
- **API errors**: Network tab Response body (includes error messages from backend)

To see backend errors from browser:
1. Open DevTools → Network tab
2. Click on failed request
3. Check Response tab for error message (this comes from backend logs)

## Example Workflow

### Debugging a Quiz Error

1. **Reproduce the issue** in browser
2. **Check terminal** for immediate error output
3. **Search log file** for more context:
   ```bash
   grep "ERROR" logs/minin.log | tail -20
   ```
4. **Find related logs** using quiz_attempt_id or user_id:
   ```bash
   grep "quiz_attempt 123" logs/minin.log
   ```
5. **Review full context** around the error:
   ```bash
   grep -B 5 -A 5 "Quiz attempt not found" logs/minin.log
   ```

---

**Log File Location**: `/Users/grace_scale/PycharmProjects/Minin/Minin/logs/minin.log`

**Last Updated**: 2025-12-03