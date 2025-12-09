# Translator Web App - API Endpoints

## Authentication

### `POST /auth/google`
Initiate Google OAuth login flow
- **Response**: Redirect to Google OAuth consent screen

### `GET /auth/google/callback`
Handle Google OAuth callback
- **Query params**: `code`, `state`
- **Response**: Set session cookie, redirect to dashboard

### `POST /auth/logout`
Log out current user
- **Response**: Clear session, redirect to home

---

## User Settings

### `GET /api/user/profile`
Get current user's profile and settings
- **Response**: User object with preferences

### `PATCH /api/user/settings`
Update user settings
- **Body**: 
  ```json
  {
    "primary_language_code": "en",
    "translator_languages": ["en", "de", "ru"],
    "quiz_frequency": 5,
    "quiz_mode_enabled": true
  }
  ```
- **Response**: Updated user object

---

## Translation

### `POST /api/translate`
Translate a phrase to all user's selected languages
- **Body**:
  ```json
  {
    "text": "Katze",
    "source_language_code": "de",
    "context_sentence": "Die Katze schläft auf dem Sofa"
  }
  ```
- **Response**:
  ```json
  {
    "phrase_id": 123,
    "translations": {
      "en": "cat",
      "de": "Katze",
      "ru": "кошка"
    },
    "should_show_quiz": false,
    "searches_until_next_quiz": 3
  }
  ```

### `GET /api/languages`
Get list of available languages
- **Query params**: `popular_only` (boolean, optional)
- **Response**: Array of language objects ordered by display_order

---

## Search History

### `GET /api/history`
Get user's search history
- **Query params**: 
  - `limit` (default: 50)
  - `offset` (default: 0)
  - `session_id` (optional: filter by session)
- **Response**: Array of search records with translations

### `GET /api/sessions`
Get user's recent sessions
- **Query params**: `limit` (default: 20)
- **Response**: Array of session objects with search counts

---

## Quiz System

### `GET /api/quiz/next`
Get next quiz question
- **Response**:
  ```json
  {
    "question_type": "multiple_choice_target",
    "prompt": {
      "question": "Translate: Katze",
      "options": ["cat", "dog", "house", "tree"]
    },
    "phrase_id": 123
  }
  ```

### `POST /api/quiz/answer`
Submit quiz answer
- **Body**:
  ```json
  {
    "phrase_id": 123,
    "question_type": "multiple_choice_target",
    "user_answer": "cat"
  }
  ```
- **Response**:
  ```json
  {
    "was_correct": true,
    "correct_answer": "cat",
    "explanation": "Katze means cat in English",
    "next_review_date": "2025-11-20"
  }
  ```

### `POST /api/quiz/start-practice`
Start a user-initiated practice session
- **Body**:
  ```json
  {
    "mode": "all" | "due_for_review" | "new_words",
    "max_questions": 10
  }
  ```
- **Response**: Session object with first question

---

## Learning Progress

### `GET /api/progress/overview`
Get overall learning statistics
- **Response**:
  ```json
  {
    "total_phrases": 245,
    "mastered": 89,
    "in_progress": 156,
    "due_for_review": 23,
    "accuracy_rate": 0.78
  }
  ```

### `GET /api/progress/phrases`
Get detailed progress for specific phrases
- **Query params**: 
  - `stage` (optional: filter by learning stage)
  - `due_today` (boolean, optional)
- **Response**: Array of phrase progress objects

### `GET /api/progress/phrase/:id`
Get progress for a specific phrase
- **Response**: Detailed learning progress including review history

---

## Admin/Debug Endpoints (Optional)

### `GET /api/admin/phrase-translations/:id`
View cached translation data for debugging
- **Response**: Phrase translation object with model info

### `POST /api/admin/refresh-translation/:id`
Force refresh translation cache for a phrase
- **Response**: Updated translation data