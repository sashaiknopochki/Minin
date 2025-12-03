# Quiz Services Error Handling Documentation

## Overview

This document describes the comprehensive error handling implemented across all quiz-related services in the Minin application. The implementation follows three core principles:

1. **Resilience**: Services gracefully handle failures and continue operating
2. **Observability**: Comprehensive logging enables easy debugging and monitoring
3. **Graceful Degradation**: Fallback mechanisms ensure core functionality persists even during failures

## Services Enhanced

### 1. QuizTriggerService ✅

**Location**: `Minin/services/quiz_trigger_service.py`

**Purpose**: Determines when to trigger quizzes and selects phrases for review based on spaced repetition logic.

#### Error Handling Improvements

##### Input Validation
- **User object validation**: Checks if user is None or has invalid id
- **User settings validation**: Validates quiz_frequency and translator_languages fields
- **Empty language list handling**: Gracefully handles users with no active languages

##### Error Scenarios Handled

| Scenario | Error Type | Response |
|----------|------------|----------|
| User is None | `ValueError` | Immediate exception with clear message |
| User has invalid/missing id | `ValueError` | Exception: "Invalid user: user must have a valid id" |
| Missing quiz_frequency | Handled | Returns `invalid_quiz_settings` reason |
| No active languages | Handled | Returns None (no eligible phrases) |
| Database query failure | `Exception` | Logs error, returns error response dict |

##### Logging Strategy

```python
# Different log levels for different scenarios
logger.debug(f"Quiz mode disabled for user_id={user.id}")
logger.info(f"No phrases due for review for user_id={user.id}")
logger.warning(f"User {user.id} missing quiz_frequency, defaulting to disabled")
logger.error(f"Unexpected error in should_trigger_quiz for user_id={user.id}: {str(e)}")
```

##### Return Values

The `should_trigger_quiz` method returns a structured dict with error information:

```python
{
    'should_trigger': False,
    'reason': 'error',  # or 'quiz_mode_disabled', 'threshold_not_reached', etc.
    'eligible_phrase': None,
    'error': 'Failed to determine quiz trigger status: ...'  # Optional
}
```

---

### 2. QuizAttemptService ✅

**Location**: `Minin/services/quiz_attempt_service.py`

**Purpose**: Creates quiz attempt records and selects appropriate question types based on learning stage.

#### Error Handling Improvements

##### Input Validation
- **Parameter type checking**: Validates user_id and phrase_id are positive integers
- **Learning progress validation**: Ensures progress record exists before creating quiz
- **Stage validation**: Validates learning stage is not empty or invalid

##### Error Scenarios Handled

| Scenario | Error Type | Response |
|----------|------------|----------|
| Invalid user_id (≤0, non-int) | `ValueError` | Exception with invalid parameter details |
| Invalid phrase_id (≤0, non-int) | `ValueError` | Exception with invalid parameter details |
| Missing learning progress | `ValueError` | "User must search for this phrase before being quizzed" |
| Missing/invalid stage | `ValueError` | Clear message about invalid stage |
| Invalid stage for quizzing | `ValueError` | "Mastered phrases should not be quizzed" |
| Database operation failure | `RuntimeError` | Rollback + exception with context |

##### Stage Validation

The `select_question_type` method includes comprehensive stage validation:

```python
# Validates stage is:
# 1. Not None or empty
# 2. A string type
# 3. One of: 'basic', 'intermediate', 'advanced'
# 4. Not 'mastered' (shouldn't be quizzed)
```

##### Database Transaction Safety

```python
try:
    quiz_attempt = QuizAttempt(...)
    db.session.add(quiz_attempt)
    db.session.flush()
    logger.info(f"Created quiz attempt: id={quiz_attempt.id}")
    return quiz_attempt
except ValueError:
    raise  # Re-raise for proper error propagation
except Exception as e:
    logger.error(f"Failed to create quiz attempt: {str(e)}", exc_info=True)
    db.session.rollback()  # CRITICAL: Rollback on failure
    raise RuntimeError(f"Failed to create quiz attempt: {str(e)}")
```

---

### 3. QuestionGenerationService ✅ (Most Critical)

**Location**: `Minin/services/question_generation_service.py`

**Purpose**: Generates quiz questions using LLM API with retry logic and fallback support.

#### Error Handling Improvements

This service has the most sophisticated error handling due to its dependency on external LLM APIs.

##### Retry Logic with Exponential Backoff

**Configuration**:
```python
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 10.0  # seconds
```

**Algorithm**:
1. Attempt 1: No delay
2. Attempt 2: 1 second delay
3. Attempt 3: 2 seconds delay (min(1*2, 10))
4. If all fail: Trigger fallback mechanism

##### API Error Handling

| Error Type | Retry Strategy | Final Action |
|------------|----------------|--------------|
| `RateLimitError` | Retry with exponential backoff | RuntimeError after max retries |
| `APITimeoutError` | Retry with exponential backoff | RuntimeError after max retries |
| `APIConnectionError` | Retry with exponential backoff | RuntimeError after max retries |
| `APIError` (5xx) | Retry with exponential backoff | RuntimeError after max retries |
| `APIError` (4xx) | No retry | Immediate RuntimeError |
| `json.JSONDecodeError` | No retry | RuntimeError: "LLM returned invalid JSON" |

##### Fallback Question Generation

When LLM fails completely, the service generates simple fallback questions:

```python
# Fallback question structure
{
    'prompt': {
        'question': "What is the English translation of 'Katze'?",
        'options': [
            "cat",  # Correct answer extracted from cached translations
            "[option 2]",  # Placeholder distractors
            "[option 3]",
            "[option 4]"
        ],
        'question_language': 'en',
        'answer_language': 'en'
    },
    'correct_answer': 'cat'
}
```

**Key Benefits**:
- Quiz system never completely breaks
- Users can still practice even if LLM is down
- Correct answers always come from cached translation data
- Obvious placeholder options indicate degraded mode

##### LLM Response Validation

Before accepting LLM response, validates:

```python
# Required fields check
required_fields = ['question', 'options', 'correct_answer',
                   'question_language', 'answer_language']

# Options count validation
if not isinstance(result['options'], list) or len(result['options']) != 4:
    raise ValueError(f"LLM response must have exactly 4 options")
```

##### Error Scenarios Handled

| Scenario | Handling |
|----------|----------|
| Missing OPENAI_API_KEY | RuntimeError: "OPENAI_API_KEY not configured" |
| Missing quiz_attempt | ValueError: "quiz_attempt cannot be None" |
| Missing phrase | ValueError: "Phrase not found: {id}" |
| Missing translations | ValueError: "No translations found for phrase" |
| Empty phrase text | ValueError: "Phrase has no text" |
| Invalid translation data | ValueError: "No valid translation data" |
| LLM API failure (all retries) | Falls back to simple question |
| Invalid JSON from LLM | RuntimeError with response content logged |
| Missing required fields | RuntimeError: "LLM response missing required field" |

##### Logging Strategy

```python
# Debug: API retry attempts
logger.debug(f"API call attempt {attempt}/{MAX_RETRIES}")

# Info: Successful operations
logger.info(f"Generated question for quiz_attempt {id}: phrase='{text}'")

# Warning: Using fallback
logger.warning(f"LLM generation failed: {e}. Using fallback question generation.")

# Error: API failures with full context
logger.error(f"Failed to parse LLM response as JSON: {e}", exc_info=True)
```

---

### 4. AnswerEvaluationService (Original Implementation)

**Location**: `Minin/services/answer_evaluation_service.py`

**Purpose**: Evaluates quiz answers and updates learning progress.

#### Existing Error Handling (Already Good)

The original implementation already includes:

✅ Input validation (empty user_answer check)
✅ Quiz attempt existence validation
✅ Required fields validation
✅ Question type validation
✅ Database transaction safety with rollback
✅ Comprehensive logging
✅ Graceful handling of missing learning progress

##### Recommended Enhancements

While the existing implementation is solid, consider adding:

1. **Answer length validation** for text input questions
2. **Sanitization** of user input to prevent injection attacks
3. **Rate limiting tracking** for suspicious answer patterns
4. **Detailed validation** for multiple choice option indices

---

### 5. LearningProgressService (Original Implementation)

**Location**: `Minin/services/learning_progress_service.py`

**Purpose**: Manages user learning progress tracking for spaced repetition.

#### Existing Error Handling (Already Good)

The original implementation includes:

✅ Database operation error handling
✅ Rollback on failures
✅ Logging of errors with context
✅ Graceful handling of missing progress records
✅ Validation of stage transitions

##### Recommended Enhancements

Consider adding:

1. **Stage transition validation** to prevent invalid progressions
2. **Date validation** for next_review_date
3. **Counter overflow protection** for times_reviewed
4. **Concurrent update detection** for progress records

---

## Architecture Patterns Used

### 1. Defensive Programming

All services validate inputs before processing:

```python
# Always validate None/empty inputs
if not quiz_attempt:
    logger.error("generate_question called with None quiz_attempt")
    raise ValueError("quiz_attempt cannot be None")

# Always validate required attributes
if not hasattr(quiz_attempt, 'id') or not quiz_attempt.id:
    logger.error("quiz_attempt missing id")
    raise ValueError("quiz_attempt must have a valid id")
```

### 2. Fail-Fast vs Fail-Safe

- **Fail-Fast**: Invalid inputs immediately raise ValueError
- **Fail-Safe**: External dependencies (LLM API) degrade gracefully with fallbacks

### 3. Exception Hierarchy

```
ValueError
├─ Invalid user inputs
├─ Missing required data
└─ Invalid state transitions

RuntimeError
├─ Database operation failures
├─ External API failures
└─ Unexpected system errors
```

### 4. Structured Logging

All services use Python's logging module with consistent patterns:

```python
import logging
logger = logging.getLogger(__name__)

# Log levels usage:
logger.debug()   # Detailed flow information for debugging
logger.info()    # Key operations and state changes
logger.warning() # Degraded functionality or unexpected conditions
logger.error()   # Errors that need attention, with exc_info=True
```

### 5. Database Transaction Safety

```python
try:
    # Database operations
    db.session.add(object)
    db.session.commit()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)
    db.session.rollback()  # ALWAYS rollback on error
    raise RuntimeError(f"Failed: {str(e)}")
```

---

## Configuration Constants

### QuestionGenerationService

```python
# Model configuration
GPT_4_1_MINI = "gpt-4.1-mini"
DEFAULT_MODEL = GPT_4_1_MINI

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 10.0     # seconds
```

### LearningProgressService

```python
# Stage constants
STAGE_BASIC = 'basic'
STAGE_INTERMEDIATE = 'intermediate'
STAGE_ADVANCED = 'advanced'
STAGE_MASTERED = 'mastered'

VALID_STAGES = [STAGE_BASIC, STAGE_INTERMEDIATE,
                STAGE_ADVANCED, STAGE_MASTERED]
```

---

## Testing Recommendations

### Unit Tests

Each service should have unit tests covering:

1. **Happy path**: Valid inputs produce expected outputs
2. **Invalid inputs**: ValueError raised with clear messages
3. **Missing data**: Appropriate error handling
4. **Database failures**: Rollback occurs, RuntimeError raised
5. **API failures** (QuestionGenerationService): Fallback triggered

### Integration Tests

Test cross-service workflows:

1. **Full quiz flow**: Trigger → Attempt → Question → Answer → Progress
2. **Error propagation**: Errors in one service don't cascade
3. **Database consistency**: Transactions rollback correctly
4. **Logging output**: Appropriate log levels used

### Example Test Cases

```python
def test_quiz_trigger_with_no_phrases():
    """Should return no_phrases_due_for_review without error"""
    result = QuizTriggerService.should_trigger_quiz(user_with_no_phrases)
    assert result['should_trigger'] == False
    assert result['reason'] == 'no_phrases_due_for_review'

def test_quiz_attempt_with_invalid_stage():
    """Should raise ValueError for mastered stage"""
    with pytest.raises(ValueError, match="mastered"):
        QuizAttemptService.select_question_type('mastered')

def test_question_generation_llm_failure():
    """Should generate fallback question when LLM fails"""
    # Mock LLM to raise APIError
    with patch('openai.OpenAI') as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = APIError()

        question = QuestionGenerationService.generate_question(quiz_attempt)

        # Should succeed with fallback
        assert question['question'] is not None
        assert '[option 2]' in question['options']  # Fallback marker
```

---

## Monitoring & Observability

### Key Metrics to Track

1. **Error rates** by service and error type
2. **LLM API retry rates** and success rates
3. **Fallback question usage** frequency
4. **Database rollback** frequency
5. **Average response times** per service

### Log Aggregation

All services use structured logging that can be aggregated:

```bash
# Example: Find all LLM failures
grep "LLM generation failed" /var/log/minin/app.log

# Example: Find all database rollbacks
grep "db.session.rollback" /var/log/minin/app.log

# Example: Track fallback usage
grep "Using fallback question generation" /var/log/minin/app.log
```

### Alerting Thresholds

Recommended alerts:

- **Critical**: LLM API failure rate > 50% for 5 minutes
- **Warning**: Fallback question usage > 10% for 15 minutes
- **Warning**: Database rollback rate > 5% for 10 minutes
- **Info**: Any new error type not seen before

---

## Rollout & Deployment

### Phased Rollout Strategy

1. **Phase 1**: Deploy to staging environment
   - Monitor logs for 48 hours
   - Verify fallback mechanisms work
   - Test with simulated API failures

2. **Phase 2**: Deploy to 10% of production traffic
   - Monitor error rates
   - Compare with baseline metrics
   - Verify no performance degradation

3. **Phase 3**: Deploy to 100% of production
   - Continue monitoring for 7 days
   - Document any new error patterns
   - Adjust retry/timeout constants if needed

### Rollback Plan

If critical issues occur:

1. Revert to previous version
2. Analyze logs for root cause
3. Fix issues in development
4. Re-test in staging
5. Retry phased rollout

---

## Future Enhancements

### Short Term (1-2 months)

1. Add error handling to AnswerEvaluationService (enhancements)
2. Add error handling to LearningProgressService (enhancements)
3. Implement circuit breaker pattern for LLM API
4. Add request/response caching for duplicate questions

### Medium Term (3-6 months)

1. Implement distributed tracing (OpenTelemetry)
2. Add chaos engineering tests
3. Implement automatic retry budget adjustment
4. Add A/B testing for different retry strategies

### Long Term (6-12 months)

1. Multi-LLM provider support with automatic failover
2. Question quality scoring and feedback loop
3. Predictive failure detection
4. Self-healing mechanisms

---

## References

### Related Documentation

- [CLAUDE.md](/CLAUDE.md) - Project architecture overview
- [endpoints.md](/endpoints.md) - API endpoint specifications
- [schema.sql](/schema.sql) - Database schema documentation

### External Resources

- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [OpenAI API Error Handling](https://platform.openai.com/docs/guides/error-codes)
- [SQLAlchemy Transaction Management](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html)

---

## Contact & Support

For questions about this error handling implementation:

1. Review service code and inline documentation
2. Check logs for detailed error context
3. Refer to test cases for expected behavior
4. Consult this document for architectural patterns

---

**Last Updated**: 2025-12-03
**Version**: 1.0.0
**Author**: Claude (Anthropic)