# Quiz System Manual Testing Guide

This guide provides step-by-step instructions for manually testing the quiz system features, including database verification steps.

## Prerequisites
- Application is running (Flask + Vite)
- Access to database (via PyCharm Database tool or SQL client)
- User account created and logged in
- `quiz_mode_enabled` is set to true for the user
- `quiz_frequency` is set to a low number (e.g., 3) for easier testing

## Database Verification Queries
Keep these queries handy for verification steps. Replace `:user_id` and `:phrase_id` with actual values.

```sql
-- Check User Search Counter & Settings
SELECT id, username, quiz_mode_enabled, quiz_frequency, searches_since_last_quiz, primary_language_code 
FROM users 
WHERE username = 'your_username';

-- Check Learning Progress for a Phrase
SELECT p.text, ulp.* 
FROM user_learning_progress ulp
JOIN phrases p ON ulp.phrase_id = p.id
WHERE ulp.user_id = :user_id 
ORDER BY ulp.last_reviewed_at DESC;

-- Check Quiz Attempts
SELECT qa.id, qa.question_type, qa.was_correct, qa.created_at, p.text
FROM quiz_attempts qa
JOIN phrases p ON qa.phrase_id = p.id
WHERE qa.user_id = :user_id
ORDER BY qa.created_at DESC;

-- Check Due Phrases (Next Review Date)
SELECT p.text, ulp.stage, ulp.next_review_date
FROM user_learning_progress ulp
JOIN phrases p ON ulp.phrase_id = p.id
WHERE ulp.user_id = :user_id
AND ulp.next_review_date <= DATE('now')
AND ulp.stage != 'mastered';
```

---

## Test Cases

### 1. Translation Triggers Quiz
**Objective:** Verify that the quiz appears automatically after N searches.

**Preconditions:**
- User `quiz_frequency` = 3
- `searches_since_last_quiz` = 2
- At least one phrase is due for review (or new phrase will be added)

**Steps:**
1. Perform a translation search (Search #3).
2. Observe the response.

**Expected Result:**
- The translation result appears.
- A quiz modal/popup appears immediately or after a short delay.
- Database: `searches_since_last_quiz` should be reset to 0 (or remain high if reset happens on quiz fetch - check implementation). *Note: Implementation resets on quiz fetch.*

**Verify in Database:**
```sql
SELECT searches_since_last_quiz FROM users WHERE id = :user_id;
-- Should be incremented, then reset when quiz is fetched
```

### 2. Quiz Shows Correct Question Type for Stage
**Objective:** Verify that 'basic' stage words get multiple choice questions.

**Preconditions:**
- A phrase exists in `user_learning_progress` with `stage = 'basic'`.
- `next_review_date` is today or in the past.

**Steps:**
1. Trigger a quiz (by searching until threshold).
2. Ensure the quiz targets the 'basic' phrase.

**Expected Result:**
- The quiz question is Multiple Choice (4 options).
- Database: `quiz_attempts` record created with `question_type = 'multiple_choice_target'` or `'multiple_choice_source'`.

**Verify in Database:**
```sql
SELECT question_type FROM quiz_attempts WHERE id = (SELECT MAX(id) FROM quiz_attempts);
-- Should be 'multiple_choice_target' or 'multiple_choice_source'
```

### 3. Multiple Choice Quiz Works Correctly
**Objective:** Verify that options are displayed and one is correct.

**Preconditions:**
- Quiz modal is open with a multiple choice question.

**Steps:**
1. Read the question and options.
2. Identify the correct answer (based on your knowledge or DB check).
3. Select the correct option.
4. Click Submit.

**Expected Result:**
- Success message appears ("Correct!").
- Modal closes or "Next" button appears.

**Verify in Database:**
```sql
SELECT was_correct, user_answer, correct_answer 
FROM quiz_attempts 
ORDER BY created_at DESC LIMIT 1;
-- was_correct should be 1 (true)
```

### 4. Answer Evaluation Accepts Correct Answers
**Objective:** Verify that the system correctly identifies the right answer.

**Preconditions:**
- Quiz modal is open.

**Steps:**
1. Select/Enter the correct answer.
2. Submit.

**Expected Result:**
- Feedback indicates the answer is correct.

**Verify in Database:**
```sql
SELECT was_correct FROM quiz_attempts ORDER BY created_at DESC LIMIT 1;
-- Should be 1
```

### 5. Wrong Answers Show Correct Answer
**Objective:** Verify that feedback is provided for incorrect answers.

**Preconditions:**
- Quiz modal is open.

**Steps:**
1. Select/Enter a clearly wrong answer.
2. Submit.

**Expected Result:**
- Error/Info message appears.
- The correct answer is displayed to the user.

**Verify in Database:**
```sql
SELECT was_correct, correct_answer FROM quiz_attempts ORDER BY created_at DESC LIMIT 1;
-- was_correct should be 0
```

### 6. Stage Advancement (Basic → Intermediate)
**Objective:** Verify that a phrase moves to the next stage after sufficient correct answers.

**Preconditions:**
- Phrase is at `stage = 'basic'`.
- `times_correct` is 1 (assuming requirement is 2 correct answers to advance).

**Steps:**
1. Trigger quiz for this phrase.
2. Answer correctly.

**Expected Result:**
- Feedback might indicate stage advancement (optional UI).
- Database: `stage` changes from 'basic' to 'intermediate'.
- Database: `times_correct` resets to 0.

**Verify in Database:**
```sql
SELECT stage, times_correct, times_reviewed 
FROM user_learning_progress 
WHERE phrase_id = :phrase_id AND user_id = :user_id;
-- stage should be 'intermediate'
```

### 7. Spaced Repetition Dates Calculation
**Objective:** Verify `next_review_date` is set correctly based on stage and result.

**Preconditions:**
- Answering a quiz for a 'basic' phrase.

**Steps:**
1. Answer correctly.
2. Check `next_review_date`.

**Expected Result:**
- If 'basic' and correct: `next_review_date` should be tomorrow (+1 day).
- If 'basic' and incorrect: `next_review_date` should be today (+0 days).

**Verify in Database:**
```sql
SELECT stage, last_reviewed_at, next_review_date 
FROM user_learning_progress 
WHERE phrase_id = :phrase_id;
-- Calculate difference between last_reviewed_at and next_review_date
```

### 8. Skip Quiz Preserves Counter
**Objective:** Verify that closing the quiz without answering does not count as a review and preserves the "due" status (or re-queues it).

**Preconditions:**
- Quiz triggered and modal open.
- `searches_since_last_quiz` was reset to 0 upon fetch.

**Steps:**
1. Close the modal (X button or click outside) without submitting an answer.
2. Perform another search.

**Expected Result:**
- The quiz should likely appear again immediately or very soon (depending on implementation logic for "skipped").
- *Note: If the implementation resets the counter on fetch, "skipping" might just mean you lost that chance until the counter fills up again. Verify if there is a specific "skip" endpoint that restores the counter.*
- **Verification:** Check if `quiz_attempts` has a record. If not, was the progress updated? It should NOT be updated.

**Verify in Database:**
```sql
-- Ensure no completed attempt was logged for this specific interaction if skipped
SELECT * FROM quiz_attempts ORDER BY created_at DESC LIMIT 1;
```

### 9. Mastered Phrases Never Appear
**Objective:** Verify that phrases with `stage = 'mastered'` are excluded from quizzes.

**Preconditions:**
- Set a phrase to `stage = 'mastered'` manually in DB.
- Set `next_review_date` to yesterday (overdue).

**Steps:**
1. Trigger quizzes repeatedly.

**Expected Result:**
- The mastered phrase never appears.
- Other eligible phrases appear instead.

**Verify in Database:**
```sql
UPDATE user_learning_progress SET stage = 'mastered', next_review_date = '2020-01-01' WHERE phrase_id = :id;
-- Then verify it is not selected by the quiz trigger query
```

### 10. Language Filtering
**Objective:** Verify only phrases in active languages appear.

**Preconditions:**
- User has active languages: English, German.
- Phrase A is German (active).
- Phrase B is Spanish (inactive).
- Both are due for review.

**Steps:**
1. Trigger quizzes.

**Expected Result:**
- Only Phrase A (German) appears.
- Phrase B (Spanish) does not appear even if overdue.

**Verify in Database:**
```sql
-- Check user's active languages
SELECT translator_languages FROM users WHERE id = :user_id;
```
