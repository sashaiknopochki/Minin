# Learning Progress System Documentation

## Overview

The **Learning Progress System** is a core feature of the Minin application that automatically tracks user vocabulary learning through a 4-stage spaced repetition progression. When users search for new phrases, the system intelligently creates learning progress entries that will be used by the quiz system to help users master vocabulary.

## Table of Contents

1. [Architecture](#architecture)
2. [4-Stage Learning Progression](#4-stage-learning-progression)
3. [Automatic Progress Initialization](#automatic-progress-initialization)
4. [Database Schema](#database-schema)
5. [API Integration](#api-integration)
6. [Quiz Type Mapping](#quiz-type-mapping)
7. [Testing](#testing)
8. [Future Enhancements](#future-enhancements)

---

## Architecture

### Components

1. **Service Layer**: `services/learning_progress_service.py`
   - Core business logic for learning progress management
   - Stateless functions operating on model instances
   - Handles progress creation, querying, and validation

2. **Model Layer**: `models/user_learning_progress.py`
   - SQLAlchemy ORM model for database representation
   - Unique constraint on (user_id, phrase_id)
   - Computed properties for analytics (accuracy_percentage, days_to_learn)

3. **Integration Layer**: `routes/translation.py`
   - Hooks into translation search flow
   - Automatically initializes progress on first search
   - Error-resilient (never fails the translation request)

4. **Migration Layer**: `migrations/versions/cec3e9020bc3_*.py`
   - Database schema updates
   - Stage value migration (backward compatibility)
   - Index creation for performance

---

## 4-Stage Learning Progression

The learning system uses a **4-stage progression** model that mirrors how humans naturally acquire vocabulary:

### Stage 1: **BASIC** (Recognition)
- **Initial stage** when user first searches for a phrase
- **Goal**: Can the user recognize the translation when shown multiple choice options?
- **Quiz Types**:
  - `multiple_choice_target`: Given source word, choose correct translation
  - `multiple_choice_source`: Given translation, choose correct source word
- **Progression Criteria**: 1-2 correct multiple choice answers
- **Next Stage**: INTERMEDIATE

### Stage 2: **INTERMEDIATE** (Active Recall)
- User can successfully **recognize** the word/phrase with multiple choice
- **Goal**: Can the user recall and type the translation from memory?
- **Quiz Types**:
  - `text_input_target`: Type the translation of the source word
  - `text_input_source`: Type the source word for the given translation
- **Progression Criteria**: 2+ correct text input answers
- **Next Stage**: ADVANCED

### Stage 3: **ADVANCED** (Contextual Mastery)
- User can actively **produce/recall** translations without hints
- **Goal**: Can the user use the word in context, understand definitions, work with synonyms?
- **Quiz Types**:
  - `contextual`: Fill in the blank with the correct word in a sentence
  - `definition`: Match the word to its definition
  - `synonym`: Identify synonyms or related words
- **Progression Criteria**: Consistent correct advanced answers
- **Next Stage**: MASTERED

### Stage 4: **MASTERED** (Permanent Completion)
- User has **fully learned** this phrase - **FINAL STATE**
- **Quiz Behavior**: ⚠️ **NEVER appears in any quizzes again**
- This phrase is permanently "graduated" from the learning system
- **No regression**: Cannot move backward from this stage

### Regression Rules

If a user answers incorrectly at any stage (except MASTERED), they move **back one stage**:

- `ADVANCED` → `INTERMEDIATE` (after wrong answer)
- `INTERMEDIATE` → `BASIC` (after wrong answer)
- `BASIC` → stays at `BASIC` (cannot regress lower)
- `MASTERED` → stays at `MASTERED` (permanent state)

---

## Automatic Progress Initialization

### Trigger Conditions

Learning progress is automatically created when **ALL** of the following conditions are met:

1. ✅ **User is authenticated**
2. ✅ **Translation request succeeds**
3. ✅ **This is the user's FIRST search** for this phrase
   - Checked by querying `user_searches` table
   - If `search_count > 1` for this user+phrase, progress is NOT created
4. ✅ **The phrase is quizzable**
   - `phrase.is_quizzable = True`
   - Phrases longer than 48 characters are non-quizzable

### Implementation Flow

```
User submits translation request
  ↓
Translation service processes request
  ↓
[IF user authenticated AND translation successful]
  ↓
log_user_search() → Creates UserSearch entry
  ↓
initialize_learning_progress_on_search()
  ↓
[Check: is_quizzable AND first_search?]
  ↓
create_initial_progress()
  ↓
UserLearningProgress created with:
  - stage: 'basic'
  - times_reviewed: 0
  - times_correct: 0
  - times_incorrect: 0
  - next_review_date: NULL
  - first_seen_at: CURRENT_TIMESTAMP
```

### Code Location

**File**: `routes/translation.py` (lines 141-153)

```python
# Initialize learning progress if this is the user's first search for this phrase
if user_search:
    try:
        # Get the phrase from the user_search to check if it's quizzable
        phrase = user_search.phrase
        initialize_learning_progress_on_search(
            user_id=current_user.id,
            phrase_id=user_search.phrase_id,
            is_quizzable=phrase.is_quizzable
        )
    except Exception as progress_error:
        # Log error but don't fail the request
        print(f"Failed to initialize learning progress: {str(progress_error)}")
```

### Error Handling

- **Non-blocking**: Errors in progress creation **never fail** the translation request
- **Graceful degradation**: If progress creation fails, translation still succeeds
- **Logging**: Errors are logged for debugging but hidden from users
- **Duplicate prevention**: `has_learning_progress()` check prevents duplicate entries

---

## Database Schema

### Table: `user_learning_progress`

| Column              | Type     | Constraints           | Description                                    |
|---------------------|----------|-----------------------|------------------------------------------------|
| `id`                | Integer  | Primary Key           | Auto-incrementing unique ID                    |
| `user_id`           | Integer  | Foreign Key, NOT NULL | References `users.id`                          |
| `phrase_id`         | Integer  | Foreign Key, NOT NULL | References `phrases.id`                        |
| `stage`             | String   | NOT NULL, Default: 'basic' | One of: basic, intermediate, advanced, mastered |
| `times_reviewed`    | Integer  | Default: 0            | Total quiz attempts for this phrase            |
| `times_correct`     | Integer  | Default: 0            | Number of correct quiz attempts                |
| `times_incorrect`   | Integer  | Default: 0            | Number of incorrect quiz attempts              |
| `next_review_date`  | Date     | Nullable              | When phrase should appear in quiz (NULL until first quiz) |
| `last_reviewed_at`  | DateTime | Nullable              | Timestamp of last quiz attempt                 |
| `created_at`        | DateTime | Default: NOW          | When progress entry was created                |
| `first_seen_at`     | DateTime | Default: NOW          | When user first encountered this phrase        |

### Constraints

```sql
-- Unique constraint: one progress record per user-phrase pair
UNIQUE (user_id, phrase_id) AS uq_user_phrase

-- Index for spaced repetition queries
INDEX (user_id, next_review_date) AS idx_user_next_review

-- Index for stage filtering (quiz generation)
INDEX (user_id, stage) AS idx_user_stage
```

### Stage Validation

**Application-level enforcement** (SQLite limitation):
- Valid values: `'basic'`, `'intermediate'`, `'advanced'`, `'mastered'`
- Enforced in `services/learning_progress_service.py`
- See `VALID_STAGES` constant

**Note**: SQLite doesn't support `ALTER TABLE ADD CHECK CONSTRAINT` on existing tables. For production with PostgreSQL/MySQL, add:

```sql
ALTER TABLE user_learning_progress
ADD CONSTRAINT check_stage_values
CHECK (stage IN ('basic', 'intermediate', 'advanced', 'mastered'));
```

### Computed Properties

Defined in `models/user_learning_progress.py`:

```python
@property
def accuracy_percentage(self):
    """Calculate accuracy as percentage of correct answers"""
    if self.times_reviewed == 0:
        return 0.0
    return (self.times_correct / self.times_reviewed) * 100

@property
def days_to_learn(self):
    """Calculate days from first seen to current stage (velocity metric)"""
    if not self.first_seen_at:
        return None
    delta = datetime.utcnow() - self.first_seen_at
    return delta.days
```

---

## API Integration

### Translation Endpoint

**Endpoint**: `POST /translation/translate`

**Request Body**:
```json
{
  "text": "geben",
  "source_language": "German",
  "target_languages": ["English"],
  "native_language": "English",
  "model": "gpt-4.1-mini"
}
```

**Response** (unchanged - progress creation is transparent):
```json
{
  "success": true,
  "original_text": "geben",
  "translations": {
    "English": [["to give", "verb", "hand over, present"]]
  },
  "model": "gpt-4.1-mini",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

**Side Effects** (if user is authenticated and first search):
1. Creates entry in `user_searches` table
2. Creates entry in `user_learning_progress` table (if quizzable)
3. Updates `phrases.search_count`

---

## Quiz Type Mapping

### Basic Stage Quiz Types

#### `multiple_choice_target`
- **Question**: "What is the translation of **[source phrase]**?"
- **Options**: 4 choices (1 correct + 3 distractors)
- **Example**:
  ```
  What is the translation of "geben"?
  A) to give ✓
  B) to take
  C) to have
  D) to want
  ```

#### `multiple_choice_source`
- **Question**: "Which word means **[translation]**?"
- **Options**: 4 choices in source language
- **Example**:
  ```
  Which German word means "to give"?
  A) geben ✓
  B) nehmen
  C) haben
  D) wollen
  ```

### Intermediate Stage Quiz Types

#### `text_input_target`
- **Question**: "Translate: **[source phrase]**"
- **Answer**: User types the translation
- **Example**:
  ```
  Translate: geben
  Answer: [to give] ✓
  ```

#### `text_input_source`
- **Question**: "What is the [source language] word for **[translation]**?"
- **Answer**: User types the source word
- **Example**:
  ```
  What is the German word for "to give"?
  Answer: [geben] ✓
  ```

### Advanced Stage Quiz Types

#### `contextual`
- **Question**: Fill in the blank with the correct word
- **Context**: Sentence with word removed
- **Example**:
  ```
  Fill in the blank: "Ich ____ dir das Buch."
  (I give you the book)
  Answer: [gebe] ✓
  ```

#### `definition`
- **Question**: Match the word to its definition
- **Example**:
  ```
  Match "geben" to its definition:
  A) to hand over, to present ✓
  B) to receive
  C) to keep
  ```

#### `synonym`
- **Question**: Identify synonyms or related words
- **Example**:
  ```
  Which word is a synonym of "geben"?
  A) schenken (to gift) ✓
  B) nehmen (to take)
  C) behalten (to keep)
  ```

### Mastered Stage

⚠️ **No quiz types** - phrases at this stage are **excluded from all quizzes**

**Query to get quizzable phrases**:
```sql
SELECT * FROM user_learning_progress
WHERE user_id = ? AND stage != 'mastered'
ORDER BY next_review_date ASC;
```

---

## Testing

### Unit Tests

**File**: `tests/test_learning_progress_service.py`

**Coverage**:
- ✅ `has_learning_progress()` - checking if progress exists
- ✅ `is_first_search()` - detecting first vs. repeated searches
- ✅ `create_initial_progress()` - progress creation with correct defaults
- ✅ `initialize_learning_progress_on_search()` - full initialization flow
- ✅ `get_learning_progress()` - progress retrieval
- ✅ Duplicate prevention via unique constraint
- ✅ Non-quizzable phrase handling
- ✅ Concurrent request handling

**Run Tests**:
```bash
pytest tests/test_learning_progress_service.py -v
```

**Expected Output**:
```
14 passed in 1.10s
```

### Integration Tests

**File**: `tests/test_translation_with_learning_progress.py`

**Coverage**:
- ✅ First search creates learning progress (authenticated user)
- ✅ Repeated search does NOT create duplicate progress
- ✅ Non-quizzable phrases do NOT create progress
- ✅ Unauthenticated users do NOT create progress

**Run Tests**:
```bash
pytest tests/test_translation_with_learning_progress.py -v
```

**Expected Output**:
```
4 passed in 0.87s
```

### Test Database

All tests use **in-memory SQLite databases** for isolation:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
```

---

## Future Enhancements

### Phase 1: Quiz Service Implementation (NOT YET IMPLEMENTED)

Planned services in `services/` directory:

1. **`quiz_service.py`**
   - Generate quiz questions based on user's learning progress
   - Select appropriate quiz type for each phrase's stage
   - Implement spaced repetition algorithm (SM-2 or similar)

2. **`answer_validation.py`**
   - Flexible answer evaluation (exact match, fuzzy matching, synonym acceptance)
   - Handle common typos and accents
   - Score answers (binary or partial credit)

3. **`spaced_repetition.py`**
   - Calculate `next_review_date` based on performance
   - Implement SM-2 algorithm or Leitner system
   - Adjust intervals based on accuracy

### Phase 2: Stage Progression Logic

**Advancement Criteria** (to be implemented in quiz service):

```python
def check_advancement(progress: UserLearningProgress) -> bool:
    """Check if user should advance to next stage"""
    if progress.stage == STAGE_BASIC:
        # Advance to INTERMEDIATE after 2 consecutive correct answers
        recent_attempts = get_recent_quiz_attempts(progress, limit=2)
        return all(a.is_correct for a in recent_attempts)

    elif progress.stage == STAGE_INTERMEDIATE:
        # Advance to ADVANCED after 3 consecutive correct answers
        recent_attempts = get_recent_quiz_attempts(progress, limit=3)
        return all(a.is_correct for a in recent_attempts)

    elif progress.stage == STAGE_ADVANCED:
        # Advance to MASTERED after 5 consecutive correct answers
        # AND accuracy > 90% over last 10 attempts
        recent_attempts = get_recent_quiz_attempts(progress, limit=5)
        accuracy = progress.accuracy_percentage
        return all(a.is_correct for a in recent_attempts) and accuracy > 90

    return False
```

### Phase 3: Analytics & Insights

- **Learning velocity**: Track `days_to_learn` across all phrases
- **Difficulty scoring**: Identify hard-to-learn phrases
- **Retention curves**: Measure long-term retention
- **Language comparisons**: Compare learning speed across languages

### Phase 4: Gamification

- **Streak tracking**: Days with active learning
- **Achievement badges**: Milestones (10 mastered, 50 mastered, etc.)
- **Leaderboards**: Compare progress with other users
- **Daily goals**: Phrases reviewed per day

---

## Migration Notes

### Backward Compatibility

The database migration (`cec3e9020bc3`) handles backward compatibility for existing data:

**Old Stage Values** → **New Stage Values**:
- `'new'` → `'basic'`
- `'recognition'` → `'intermediate'`
- `'production'` → `'advanced'`
- `'mastered'` → `'mastered'` (unchanged)

**Migration SQL**:
```sql
UPDATE user_learning_progress
SET stage = CASE
    WHEN stage = 'new' THEN 'basic'
    WHEN stage = 'recognition' THEN 'intermediate'
    WHEN stage = 'production' THEN 'advanced'
    ELSE stage
END;
```

**Rollback Support**:
```sql
UPDATE user_learning_progress
SET stage = CASE
    WHEN stage = 'basic' THEN 'new'
    WHEN stage = 'intermediate' THEN 'recognition'
    WHEN stage = 'advanced' THEN 'production'
    ELSE stage
END;
```

---

## References

- **Spaced Repetition**: [SuperMemo Algorithm (SM-2)](https://www.supermemo.com/en/archives1990-2015/english/ol/sm2)
- **Leitner System**: [Wikipedia](https://en.wikipedia.org/wiki/Leitner_system)
- **SQLAlchemy ORM**: [Official Docs](https://docs.sqlalchemy.org/en/20/)
- **Flask-Migrate**: [Official Docs](https://flask-migrate.readthedocs.io/)

---

## Contact

For questions or contributions related to the Learning Progress System, please refer to the main project README or create an issue in the repository.