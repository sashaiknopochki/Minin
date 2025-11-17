# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Please use the bd tool for all work tracking. Run bd quickstart if needed.
**Note**: This project uses [bd (beads)](https://github.com/steveyegge/beads)
   for issue tracking. Use `bd` commands instead of markdown TODOs.
   See AGENTS.md for workflow details.


## Project Overview

**Minin** is a multi-language translation and vocabulary learning web application that combines LLM-powered translations with intelligent spaced repetition quizzes. The app caches translations per target language and uses a learning progression system (new → recognition → production → mastered) to help users build active vocabulary.

## Key Architecture Concepts

### Multi-Target-Language Translation Caching

The translation caching system is designed to support the same phrase translated into multiple target languages:

- **Phrase Table**: Stores unique (text, language_code) combinations (e.g., "geben" in German)
- **PhraseTranslation Table**: Caches LLM responses with composite unique key (phrase_id, target_language_code)
  - Same phrase can have multiple cached translations (e.g., "geben" → English, "geben" → French)
  - Avoids redundant LLM API calls for previously translated phrase-target pairs
  - Each translation tracks model_name and model_version for cost analysis

**Example Flow:**
1. User searches "geben" (German → English) → Creates phrase + translation cache with target='en'
2. Same user searches "geben" (German → French) → Reuses phrase, creates new translation cache with target='fr'
3. Another user searches "geben" (German → English) → Instant cache hit, no LLM call

### Application Factory Pattern

The Flask app uses the factory pattern in `app.py`:
- `create_app(config_name)` function initializes the app with environment-based configuration
- SQLAlchemy `db` object initialized separately in `models/__init__.py` and bound via `db.init_app(app)`
- All models imported after db initialization to ensure proper registration
- Blueprint registration happens inside the factory function

### Database Model Relationships

Key bidirectional relationships to understand:

- **User ↔ UserSearch/QuizAttempt/UserLearningProgress**: One user has many searches, attempts, and progress records
- **Phrase ↔ PhraseTranslation**: One phrase has many translations (one per target language)
- **Phrase ↔ UserLearningProgress**: Same phrase tracked separately per user
- **Session ↔ UserSearch**: Groups searches by UUID-based session for history tracking

### Learning Progress System

The `user_learning_progress` table tracks spaced repetition state:
- **stage**: Progression through learning stages (new, recognition, production, mastered)
- **next_review_date**: When the phrase should appear in a quiz again
- **times_reviewed/correct/incorrect**: Metrics for the spaced repetition algorithm
- Composite unique constraint on (user_id, phrase_id) ensures one progress record per user-phrase pair

### JSON Column Usage

Several models use JSON columns for flexible data storage:
- **User.translator_languages**: Array of language codes (e.g., ["en", "de", "ru"])
- **PhraseTranslation.translations_json**: Complete LLM response with definitions, examples, synonyms
- **UserSearch.llm_translations_json**: Cached translations for all target languages in the search
- **QuizAttempt.prompt_json**: The generated question with options/context

SQLAlchemy auto-serializes Python dicts to JSON - always pass dict objects, not JSON strings.

## Development Commands

### Setup and Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Database Management

```bash
# Initialize Flask-Migrate (first time only)
flask db init

# Create a new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations to database
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Running the Application

```bash
# Development server
python app.py
# or
flask run

# The app will be available at http://localhost:5000
```

### Testing

```bash
# Run all model tests
python test_models.py

# Expected output: 12 tests covering all 8 models with assertions
# - Creates test database (test_database.db)
# - Tests multi-target-language caching
# - Verifies all relationships and constraints
# - Cleans up test database automatically
```

## Project Structure

```
Minin/
├── app.py                          # Flask application factory
├── config.py                       # Environment-based configuration
├── test_models.py                  # Model integration tests
├── models/
│   ├── __init__.py                # SQLAlchemy db initialization
│   ├── user.py                    # User model with OAuth fields
│   ├── language.py                # Language definitions (ISO 639-1)
│   ├── phrase.py                  # Words/phrases with unique constraint
│   ├── phrase_translation.py      # LLM translation cache (multi-target)
│   ├── user_searches.py           # Search history
│   ├── user_learning_progress.py # Spaced repetition tracking
│   ├── quiz_attempt.py            # Quiz history
│   └── session.py                 # Search session grouping
├── routes/
│   ├── __init__.py
│   ├── auth.py                    # Authentication endpoints
│   ├── translation.py             # Translation endpoints
│   ├── quiz.py                    # Quiz endpoints
│   ├── progress.py                # Learning progress endpoints
│   └── settings.py                # User settings endpoints
├── schema.sql                     # DBML schema documentation
├── endpoints.md                   # API endpoint specifications
└── README.md                      # Full project documentation
```

## Important Implementation Notes

### When Adding New Models or Changing Relationships

1. Update the model file in `models/`
2. Import the model in `app.py` create_app() function (after db.init_app)
3. Create migration: `flask db migrate -m "description"`
4. Review the generated migration in `migrations/versions/`
5. Apply migration: `flask db upgrade`
6. Add test coverage in `test_models.py`

### When Working with JSON Columns

Always pass Python objects (dict/list), never JSON strings:

```python
# ✅ Correct
user = User(translator_languages=["en", "de", "ru"])
translation = PhraseTranslation(translations_json={'translation': 'cat', 'examples': [...]})

# ❌ Wrong
user = User(translator_languages='["en", "de", "ru"]')
translation = PhraseTranslation(translations_json=json.dumps({...}))
```

### Blueprint Route Prefixes

All blueprints have URL prefixes defined:
- `/auth` - Authentication routes
- `/translation` - Translation endpoints
- `/quiz` - Quiz endpoints
- `/progress` - Learning progress endpoints
- `/settings` - User settings endpoints

### Configuration Management

- `config.py` contains DevelopmentConfig and ProductionConfig classes
- Environment variables loaded via python-dotenv from `.env` file
- Database URI defaults to `sqlite:///database.db` but configurable via DATABASE_URI env var
- Switch environments using FLASK_ENV=development or FLASK_ENV=production

## Planned Services (Not Yet Implemented)

The following service modules are planned but not yet created:
- `services/llm_service.py` - OpenAI/OpenRouter integration for translations
- `services/quiz_service.py` - Quiz generation with 7 question types
- `services/answer_validation.py` - Flexible answer evaluation
- `services/spaced_repetition.py` - Learning algorithm and review scheduling

When implementing these, follow the service pattern: stateless functions that operate on model instances.

## Cost Optimization Strategy

Since the app uses LLM APIs, the caching strategy is critical:
- All translations cached in `phrase_translations` table by (phrase_id, target_language_code)
- Model name/version tracked for cost analysis and debugging
- Check cache before calling LLM API
- Consider using cheaper models (gpt-3.5-turbo) vs premium (gpt-4) based on use case