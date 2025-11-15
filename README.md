# Minin

**Translation & Vocabulary Learning App**

A smart language learning web application that combines multi-language translation with intelligent spaced repetition quizzes to help you build active vocabulary.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
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

**Backend**
- Python 3.x
- Flask (Web framework)
- SQLite (Database)
- SQLAlchemy (ORM)
- Flask-Dance or Authlib (Google OAuth)

**Frontend**
- Tailwind CSS (Styling)
- Vanilla JavaScript or lightweight framework (TBD)

**AI/LLM Integration**
- OpenAI API (translations, quiz generation, answer validation)
- Alternative: OpenRouter for free/cheaper models
- Model tracking for reproducibility and cost analysis

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
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. **Run the application**
   ```bash
   flask run
   ```

The app will be available at `http://localhost:5000`

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

For detailed schema, see [schema.sql](./schema.sql)

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

For detailed endpoint specifications, see [api_endpoints.md](./api_endpoints.md)

---

## Development Roadmap

### Phase 1: Core Foundation (MVP)
- [x] Database schema design
- [x] API endpoints planning
- [x] Quiz logic and question types planning
- [ ] Google OAuth authentication
- [ ] Basic Flask app structure
- [ ] SQLAlchemy models
- [ ] Basic UI with Tailwind CSS

### Phase 2: Translation Feature
- [ ] Multi-language translator interface
- [ ] LLM integration for translations
- [ ] Dynamic language addition/removal
- [ ] Search history storage
- [ ] Translation caching with model tracking

### Phase 3: Learning System
- [ ] Practice mode page with mode selection
- [ ] Multiple choice quiz generation
- [ ] Text input quiz generation
- [ ] Contextual and definition-based questions
- [ ] LLM-powered answer validation with flexibility
- [ ] Basic progress tracking
- [ ] Quiz trigger after N searches
- [ ] Learning stage progression

### Phase 4: Spaced Repetition
- [ ] Implement spaced repetition algorithm
- [ ] Review scheduling (1, 3, 7, 14, 30 days)
- [ ] Learning stage progression (new → recognition → production → mastered)
- [ ] Statistics dashboard
- [ ] Language preference-aware quiz filtering

### Phase 5: Polish
- [ ] Responsive design
- [ ] Settings page with all customizations
- [ ] User feedback and error handling
- [ ] Performance optimization
- [ ] Cost optimization for LLM API calls
- [ ] Analytics dashboard

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
├── app.py                  # Flask application entry point
├── models.py               # SQLAlchemy database models
├── routes/
│   ├── auth.py            # Authentication routes
│   ├── translation.py     # Translation endpoints
│   ├── quiz.py            # Quiz endpoints
│   ├── progress.py        # Learning progress endpoints
│   └── settings.py        # Settings endpoints
├── services/
│   ├── llm_service.py     # LLM integration (OpenAI/OpenRouter)
│   ├── quiz_service.py    # Quiz generation and question types
│   ├── answer_validation.py  # Answer evaluation and flexibility
│   └── spaced_repetition.py  # Spaced repetition algorithm
├── static/
│   ├── css/               # Tailwind CSS files
│   └── js/                # Frontend JavaScript
├── templates/             # HTML templates
├── migrations/            # Database migrations
├── .env                   # Environment variables (not in git)
├── .gitignore
├── requirements.txt       # Python dependencies
├── schema.sql            # Database schema documentation
├── api_endpoints.md      # API documentation
└── README.md             # This file
```

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

## License

This is a student project. License TBD.

---

## Acknowledgments

- Built as a learning project
- Translation and quiz generation powered by OpenAI/OpenRouter
- UI styling with Tailwind CSS
- Database design with DBML (Database Markup Language)

---

**Happy Learning!** 🌍📚