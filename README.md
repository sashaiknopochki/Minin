# Minin

**LLM-Powered Language Learning Platform**

A full-stack web application that combines AI-powered multi-language translation with intelligent spaced repetition quizzes. Built with Flask, React, and SQLAlchemy, Minin helps users build active vocabulary across 58+ languages using adaptive learning algorithms.

🌍 **Live Demo**: [Coming Soon]
📚 **Status**: Production-Ready, Pre-Publication
🚀 **Version**: 1.0.0-beta

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Management](#database-management)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Development Roadmap](#development-roadmap)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

### Core Features

**Multi-Language Translator**
- Translate words and phrases across multiple languages simultaneously
- Default support for English, German, and Russian (expandable)
- Add or remove languages dynamically during your session
- Support for words, phrases, phrasal verbs, and example sentences
- LLM-powered translations for accuracy and context
- Optional context sentences to capture real-world usage examples
- Translation caching to avoid redundant API calls

**Intelligent Quiz System**
- Spaced repetition learning algorithm with intelligent scheduling
- Seven diverse question types for varied practice:
  - **Multiple Choice (Target)**: Recognize translation in your native language from source word
  - **Multiple Choice (Source)**: Recognize translation in source language from your native language
  - **Text Input (Target)**: Produce translation in your native language by typing
  - **Text Input (Source)**: Produce translation in source language by typing
  - **Contextual**: Translate using the sentence context you provided when searching
  - **Definition**: Translate based on word definition in your native language
  - **Synonym**: Match words by meaning or similar concept
- On-the-go question generation powered by LLM for adaptive, natural questions
- Flexible answer validation (handles variations like articles, capitalization, minor typos)
- Progress tracking with learning stages: new → recognition → production → mastered
- Automatic quiz prompts every N words (configurable in settings, default 5)
- User-initiated practice mode for reviewing previously learned words
- Quiz filtering by current language preferences (only quizzes on active languages)

**User Management**
- Google OAuth authentication
- Customizable primary/mother tongue language
- Personal learning progress tracking
- Search history and session management
- Configurable quiz frequency and modes

---

## Tech Stack

### Backend
- **Framework**: Flask 3.1 (Python 3.8+)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Dance (Google OAuth 2.0)
- **Migrations**: Flask-Migrate (Alembic)
- **Testing**: Pytest with 15+ test modules
- **API**: RESTful endpoints with JSON responses

### Frontend
- **Framework**: React 19.2 with TypeScript 5.9
- **Build Tool**: Vite 7.2
- **Routing**: React Router DOM 7.9
- **Styling**: Tailwind CSS 3.4
- **UI Components**: Radix UI (25+ shadcn/ui components)
- **State Management**: React Context API
- **HTTP Client**: Fetch API

### AI/LLM Integration
- **Primary Provider**: OpenAI API (GPT-4.1 mini, GPT-4o mini)
- **Alternative**: OpenRouter support for cost optimization
- **Use Cases**: Translation generation, quiz question creation, answer validation
- **Optimization**: Aggressive caching, model tracking, cost analysis

---

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Google Cloud Project with OAuth 2.0 credentials
- OpenAI API key or OpenRouter account

---

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Minin
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Initialize the database**
   ```bash
   # Initialize Flask-Migrate (first time only)
   flask db init

   # Create and apply migrations
   flask db migrate -m "Initial migration"
   flask db upgrade

   # ⚠️ CRITICAL: Populate the languages table with all 58 supported languages
   # ALWAYS use this script - DO NOT create custom seed scripts!
   python scripts/populate_languages.py
   ```

   **Important**: The `scripts/populate_languages.py` script is the **ONLY** correct way to populate the languages table. It contains **58 supported languages** with native script names (not 20). Never delete the database without backing it up, and never create custom seed scripts.

6. **Run the application**
   ```bash
   flask run
   ```

7. **Start the frontend** (in a separate terminal)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

The backend will be available at `http://localhost:5001`
The frontend will be available at `http://localhost:5173`

---

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# LLM API Configuration
LLM_PROVIDER=openai  # or openrouter
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4
# Alternative for OpenRouter:
# OPENROUTER_API_KEY=your-openrouter-key
# OPENROUTER_MODEL=openai/gpt-3.5-turbo

# Database
DATABASE_URL=sqlite:///minin.db

# Application Settings
DEFAULT_LANGUAGES=en,de,ru
QUIZ_FREQUENCY=5  # Show quiz after every N word searches
```

---

## Database Management

### ⚠️ CRITICAL: Language Population

The application supports **58 languages** with native script names. You **MUST** use the provided `populate_languages.py` script to populate the languages table.

**DO NOT:**
- ❌ Create custom seed scripts
- ❌ Delete the database without backing it up first
- ❌ Manually populate with a subset of languages
- ❌ Skip running `populate_languages.py` after database initialization

**Correct Usage:**

```bash
# After creating database and running migrations
python scripts/populate_languages.py
```

The script populates **58 languages** including:
- Afrikaans, Amharic, Arabic, Armenian, Azerbaijani
- Belarusian, Bengali
- Chinese (Simplified), Chinese (Traditional), Czech, Danish, Dutch
- English, Estonian
- Finnish, French
- Georgian, German, Greek, Gujarati
- Hausa, Hebrew, Hindi, Hungarian
- Indonesian, Italian
- Japanese
- Kannada, Kazakh, Korean, Kyrgyz
- Latvian, Lithuanian
- Malayalam
- Norwegian
- Persian, Polish, Portuguese
- Romanian, Russian
- Serbian, Somali, Spanish, Swahili, Swedish
- Tajik, Tamil, Telugu, Thai, Turkish, Turkmen
- Ukrainian, Urdu, Uzbek
- Vietnamese
- Xhosa
- Yoruba
- Zulu

### Database Migrations

When modifying models:

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Review the generated migration in migrations/versions/

# Apply the migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Database Location

- **Development**: `instance/database.db` (SQLite)
- **Production**: Configure `DATABASE_URL` in `.env`

### Backup and Restore

```bash
# Backup
cp instance/database.db instance/database.backup.db

# Restore
cp instance/database.backup.db instance/database.db
```

---

## Database Schema

### Core Tables

**users**
- User accounts with Google OAuth data
- Primary language preference (for quiz responses)
- Translator languages (JSON array of active language codes)
- Quiz settings (frequency, enabled/disabled)
- Search counter for quiz triggering

**languages**
- Language definitions (ISO 639-1 codes)
- Native name and English name
- Display order for UI sorting

**phrases**
- Storage for words, phrases, phrasal verbs, and example sentences
- Language association via ISO 639-1 code
- Quizzable flag to exclude certain phrases
- Unique constraint on (text, language_code)

**user_searches**
- History of user translation searches with timestamps
- Links to phrases and sessions
- Cached LLM translations for all target languages
- Optional context sentences for real-world usage

**phrase_translations**
- Cached LLM translation responses with all target languages
- Model name and version tracking for reproducibility
- Optional prompt hash for debugging
- One translation set per phrase

**user_learning_progress**
- Tracks learning stage for each phrase (new → recognition → production → mastered)
- Spaced repetition metrics (times reviewed, correct, incorrect)
- Next review date for scheduling
- Unique constraint on (user_id, phrase_id)

**quiz_attempts**
- Complete history of all quiz attempts
- Stores generated question prompt and user's answer
- Correct answer and LLM evaluation data
- Question type tracking for analytics

**sessions**
- Groups searches by session (UUID-based)
- Tracks session start and end times
- Links to user for session-based history

For detailed schema, see [docs/schema.sql](./docs/schema.sql)

---

## API Endpoints

### Authentication
- `POST /auth/google` - Initiate Google OAuth login flow
- `GET /auth/google/callback` - Handle Google OAuth callback
- `POST /auth/logout` - Log out current user

### User Settings
- `GET /api/user/profile` - Get current user's profile and settings
- `PATCH /api/user/settings` - Update user settings (languages, quiz frequency, etc.)

### Translation
- `POST /api/translate` - Translate a phrase to all user's selected languages
- `GET /api/languages` - Get list of available languages
- `GET /api/history` - Get user's search history with pagination and filtering
- `GET /api/sessions` - Get user's recent sessions

### Learning & Progress
- `GET /api/progress/overview` - Get overall learning statistics
- `GET /api/progress/phrases` - Get detailed progress for specific phrases with filtering
- `GET /api/progress/phrase/:id` - Get progress for a specific phrase

### Quiz System
- `GET /api/quiz/next` - Get next quiz question (auto-triggered or from practice)
- `POST /api/quiz/answer` - Submit quiz answer and get evaluation
- `POST /api/quiz/start-practice` - Start a user-initiated practice session

### Admin/Debug
- `GET /api/admin/phrase-translations/:id` - View cached translation data
- `POST /api/admin/refresh-translation/:id` - Force refresh translation cache

For detailed endpoint specifications, see [docs/API_ENDPOINTS.md](./docs/API_ENDPOINTS.md)

---

## Implementation Status

### ✅ Phase 1: Core Foundation (COMPLETED)
- [x] Database schema design (8 models)
- [x] API endpoints planning and implementation
- [x] Quiz logic and question types (7 types)
- [x] Google OAuth authentication
- [x] Flask application factory pattern
- [x] SQLAlchemy models with relationships
- [x] Modern React UI with Tailwind CSS

### ✅ Phase 2: Translation Feature (COMPLETED)
- [x] Multi-language translator interface
- [x] LLM integration for translations (OpenAI/OpenRouter)
- [x] Dynamic language addition/removal
- [x] Search history storage with sessions
- [x] Multi-target-language translation caching
- [x] Model name/version tracking

### ✅ Phase 3: Learning System (COMPLETED)
- [x] Practice mode page with filtering
- [x] Multiple choice quiz generation (2 types)
- [x] Text input quiz generation (2 types)
- [x] Contextual, definition, and synonym questions
- [x] LLM-powered answer validation with flexibility
- [x] Comprehensive progress tracking
- [x] Auto-quiz trigger after N searches
- [x] Learning stage progression system

### ✅ Phase 4: Spaced Repetition (COMPLETED)
- [x] Spaced repetition algorithm implemented
- [x] Adaptive review scheduling
- [x] Four-stage progression (new → recognition → production → mastered)
- [x] Progress overview dashboard
- [x] Language preference-aware quiz filtering
- [x] Quiz type preferences (customizable)

### ✅ Phase 5: Polish (COMPLETED)
- [x] Fully responsive design (mobile, tablet, desktop)
- [x] Complete settings page with all customizations
- [x] Comprehensive error handling and user feedback
- [x] Performance optimizations (caching, lazy loading)
- [x] LLM cost optimization strategies
- [x] Progress analytics and statistics

### 🚀 Ready for Publication
- [ ] Security audit
- [ ] Performance testing at scale
- [ ] Documentation review
- [ ] Code cleanup and organization
- [ ] Deployment configuration
- [ ] License selection

---

## Usage

### Setting Up Your Languages

1. Log in with your Google account
2. Choose your primary language (the language you'll answer quizzes in)
3. Select languages you want to translate between (e.g., English, German, Russian)
4. Set your preferred quiz frequency (default: every 5 words)

### Translating Words/Phrases

1. Type a word or phrase in any of your selected languages
2. Translations appear automatically in other language fields
3. Optionally add a context sentence showing how you saw the word used (e.g., "The cat sat on the mat")
4. Add more languages using the language selector

### Learning with Quizzes

**Automatic Quiz Mode:**
- After searching N words (configurable, default 5), you'll be prompted with a quiz
- The app picks an appropriate word based on spaced repetition scheduling
- Question types vary: multiple choice, text input, contextual, definition-based
- Answer to continue searching

**Practice Mode:**
- Navigate to "Practice" section anytime
- Choose practice mode: all words, due for review, or new words only
- Select maximum number of questions to practice
- Get detailed feedback on each answer

**Learning Progression:**
- **New word** → Starts in "new" stage with recognition quizzes (multiple choice)
- **Correct recognition** → Progress to "recognition" stage
- **Correct production** → Progress to "production" stage (text input questions)
- **Correct production multiple times** → Marked as "mastered"
- **Incorrect answer** → Review date moved closer to encourage re-learning

### Managing Your Vocabulary

- View all searched words in "History" with session grouping
- See progress for each word (stage, accuracy, next review date)
- Delete words you don't want to learn
- Change your primary language for quiz responses
- Adjust quiz frequency in Settings
- View comprehensive learning statistics

---

## Project Structure

```
Minin/
├── README.md                   # Project documentation (this file)
├── CLAUDE.md                   # Claude Code development guide
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
│
├── app.py                      # Flask application factory
├── config.py                   # Environment-based configuration
├── conftest.py                 # Pytest configuration
│
├── models/                     # SQLAlchemy models (8 models)
│   ├── user.py                # User accounts and OAuth
│   ├── language.py            # 58 supported languages
│   ├── phrase.py              # Words and phrases
│   ├── phrase_translation.py  # LLM translation cache
│   ├── user_searches.py       # Search history
│   ├── user_learning_progress.py  # Spaced repetition state
│   ├── quiz_attempt.py        # Quiz history
│   └── session.py             # Session grouping
│
├── routes/                     # Flask blueprints (5 modules)
│   ├── api.py                 # Core API endpoints
│   ├── translation.py         # Translation endpoints
│   ├── quiz.py                # Quiz endpoints
│   ├── progress.py            # Learning progress endpoints
│   └── settings.py            # User settings endpoints
│
├── services/                   # Business logic (10 services)
│   ├── llm_translation_service.py
│   ├── phrase_translation_service.py
│   ├── question_generation_service.py  # 7 question types
│   ├── answer_evaluation_service.py
│   ├── learning_progress_service.py
│   ├── quiz_attempt_service.py
│   ├── quiz_trigger_service.py
│   ├── user_search_service.py
│   ├── session_service.py
│   └── language_utils.py
│
├── auth/                       # Authentication
│   ├── oauth.py               # Google OAuth implementation
│   └── utils.py
│
├── tests/                      # Test suite (16 test files)
│   ├── test_models.py
│   ├── test_auth.py
│   ├── test_translation.py
│   ├── test_quiz_routes.py
│   ├── test_learning_progress_service.py
│   ├── test_spell_check.py
│   └── ... (10 more test files)
│
├── scripts/                    # Utility scripts
│   ├── README.md              # Script documentation
│   ├── populate_languages.py  # Language table setup
│   ├── backup_db.py           # Database backup
│   ├── check_db.py            # Database health check
│   ├── debug_quiz_data.py     # Quiz debugging
│   ├── demo_caching_workflow.py # Caching demo
│   └── watch_logs.sh          # Log monitoring
│
├── migrations/                 # Database version control
│   └── versions/              # Alembic migration scripts
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components (Login, Translate, Practice, etc.)
│   │   ├── contexts/          # Auth & Language contexts
│   │   ├── hooks/             # Custom React hooks
│   │   └── types/             # TypeScript types
│   ├── public/                # Static assets
│   ├── vite.config.ts         # Vite configuration
│   └── package.json           # Frontend dependencies
│
├── docs/                       # Documentation
│   ├── README.md              # Documentation index
│   ├── schema.sql             # Database schema (DBML)
│   ├── API_ENDPOINTS.md       # API documentation
│   ├── AGENTS.md              # Agent workflow
│   ├── CACHING_IMPLEMENTATION.md
│   └── ... (20+ implementation guides)
│
└── instance/                   # SQLite database (gitignored)
    └── database.db
```

For complete project structure and cleanup recommendations, see [docs/PROJECT_CLEANUP_RECOMMENDATIONS.md](./docs/PROJECT_CLEANUP_RECOMMENDATIONS.md)

---

## Cost Optimization

Since the app uses LLM APIs for translations and quiz generation, here are strategies to minimize costs:

1. **Aggressive caching**: All LLM translation responses stored in `phrase_translations` table once per phrase
2. **Model selection**: Use GPT-3.5-turbo or cheaper alternatives for routine translation, reserve GPT-4 for complex edge cases
3. **On-the-go generation**: Generate quiz questions dynamically only when needed, not pre-generated
4. **Model tracking**: Log which model/version generated each response for cost analysis
5. **OpenRouter integration**: Support cheaper LLM providers as alternative to OpenAI
6. **Answer validation**: Implement flexible client-side validation before calling LLM
7. **Session-based filtering**: Quiz only on user's current active languages to avoid wasted generations

---

## How It Works: The Quiz Flow

1. **User searches a word** → `user_searches` records the search with cached translation
2. **Search counter increments** → When it reaches `quiz_frequency`, a quiz is triggered
3. **Quiz selection** → App picks a phrase due for review using `user_learning_progress.next_review_date`
4. **Question generation** → LLM generates appropriate question type on-the-go using phrase + translations + optional context
5. **User answers** → Response stored in `quiz_attempts`
6. **Validation** → LLM evaluates answer with flexible grading
7. **Progress update** → `user_learning_progress` updated with review data and new `next_review_date` calculated
8. **Learning stage progression** → If all conditions met, word advances to next stage (new → recognition → production → mastered)

---

## Architecture Highlights

### Multi-Target-Language Translation Caching
One of Minin's key innovations is its intelligent caching system:
- Same phrase can be translated to **multiple target languages**
- Each translation is cached separately with composite key `(phrase_id, target_language_code)`
- Drastically reduces LLM API costs by avoiding redundant calls
- Tracks model name/version for cost analysis and reproducibility

**Example Flow:**
```
User 1: "geben" (German → English) → LLM call + cache creation
User 2: "geben" (German → English) → Instant cache hit! (No LLM call)
User 3: "geben" (German → French)  → Reuses phrase + fresh LLM call for French
User 4: "geben" (German → EN+FR)   → Both languages cached! (No LLM calls)
```

### Spaced Repetition Algorithm
Minin implements a four-stage learning progression:
1. **New** → First encounter, recognition-based quizzes
2. **Recognition** → Can recognize translation (multiple choice)
3. **Production** → Can actively produce translation (text input)
4. **Mastered** → Consistent correct production, longer review intervals

Review scheduling adapts based on performance:
- Correct answers → Increase interval (1 → 3 → 7 → 14 → 30 days)
- Incorrect answers → Reset to shorter interval for re-learning

### Service Layer Architecture
Business logic is completely separated from routes:
- **Stateless service functions** for testability
- **Dependency injection** through function parameters
- **No direct database access** in routes
- **Comprehensive test coverage** (15 test modules)

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

See [CLAUDE.md](./CLAUDE.md) for development guidelines.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

**Note**: This is an educational project built to demonstrate full-stack development with modern AI integration.

---

## Acknowledgments

- Built as a learning project
- Translation and quiz generation powered by OpenAI/OpenRouter
- Schadcn components
- UI styling with Tailwind CSS
- Database design with DBML (Database Markup Language)

---

**Happy Learning!** 🌍📚