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
- Support for words, phrases, and phrasal verbs
- LLM-powered translations for accuracy and context

**Intelligent Quiz System**
- Spaced repetition learning algorithm
- Two quiz modes:
  - **Recognition Mode**: Multiple choice (5 options)
  - **Production Mode**: Type the translation
- Flexible answer validation (handles variations like articles, capitalization, typos)
- Progress tracking with learning stages: new → recognition → production → mastered
- Quiz prompts every 5 words (configurable in settings)
- Practice mode for reviewing previously learned words

**User Management**
- Google OAuth authentication
- Customizable primary/mother tongue language
- Personal learning progress tracking
- Search history and session management

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

# OpenAI API
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4

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
- Primary language preference
- Settings (quiz frequency, etc.)

**languages**
- Language definitions (code, name, flag emoji)
- Pre-populated with common languages

**phrases**
- Storage for words, phrases, and phrasal verbs
- Unique constraint on (text, language_id)

**user_searches**
- History of user translation searches
- Cached LLM translations for performance
- Session grouping

**user_learning_progress**
- Tracks learning stage for each phrase
- Spaced repetition intervals
- Next review date calculation

**quiz_attempts**
- Complete history of all quiz attempts
- Stores LLM evaluation for debugging
- Tracks both correct and incorrect answers

**user_sessions**
- Groups searches by session
- Tracks which languages were used

For detailed schema, see [schema.sql](./schema.sql)

---

## API Endpoints

### Authentication
- `POST /auth/google/login` - Initiate Google OAuth flow
- `POST /auth/logout` - Log out current user
- `GET /auth/user` - Get current user info

### Translation
- `POST /api/translate` - Translate word/phrase to multiple languages
- `GET /api/search-history` - Retrieve user's search history
- `DELETE /api/phrases/{id}` - Delete a phrase from history

### Learning
- `GET /api/quiz/next` - Get next quiz question
- `POST /api/quiz/answer` - Submit quiz answer for validation
- `GET /api/progress` - Get user's learning statistics
- `GET /api/learned-phrases` - List all learned phrases

### Settings
- `GET /api/languages` - Get available languages
- `PUT /api/user/settings` - Update user preferences
- `PUT /api/user/primary-language` - Change primary language

For detailed endpoint specifications, see [api_endpoints.md](./api_endpoints.md)

---

## Development Roadmap

### Phase 1: Core Foundation (MVP)
- [x] Database schema design
- [x] API endpoints planning
- [ ] Google OAuth authentication
- [ ] Basic Flask app structure
- [ ] SQLAlchemy models
- [ ] Basic UI with Tailwind CSS

### Phase 2: Translation Feature
- [ ] Multi-language translator interface
- [ ] LLM integration for translations
- [ ] Dynamic language addition/removal
- [ ] Search history storage
- [ ] Translation caching

### Phase 3: Learning System
- [ ] Practice mode page
- [ ] Recognition quizzes (multiple choice)
- [ ] Production quizzes (text input)
- [ ] LLM-powered answer validation
- [ ] Basic progress tracking
- [ ] Quiz trigger after N searches

### Phase 4: Spaced Repetition
- [ ] Implement spaced repetition algorithm
- [ ] Review scheduling (1, 3, 7, 14, 30 days)
- [ ] Learning stage progression
- [ ] Statistics dashboard

### Phase 5: Polish
- [ ] Responsive design
- [ ] Settings page
- [ ] User feedback and error handling
- [ ] Performance optimization
- [ ] Cost optimization for LLM API calls

---

## Usage

### Translating Words/Phrases

1. Log in with your Google account
2. Select 3 default languages (e.g., English, German, Russian)
3. Type a word or phrase in any language field
4. Translations appear automatically in other language fields
5. Add more languages using the "+" button

### Learning with Quizzes

**Automatic Quiz Mode:**
- After every 5 word searches, you'll be prompted with a quiz
- Answer correctly to continue searching
- Answer incorrectly to review the word

**Practice Mode:**
- Navigate to "Practice" section
- Review all "not perfectly known" words
- Choose between Recognition or Production mode

**Learning Progression:**
- **New word** → Recognition quiz (multiple choice)
- **Correct recognition** → Production quiz (type answer)
- **Correct production** → Spaced repetition schedule
- **Incorrect answer** → Reset to shorter interval

### Managing Your Vocabulary

- View all searched words in "History"
- Delete words you don't want to learn
- Change your primary language for quiz prompts
- Adjust quiz frequency in Settings

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
│   └── settings.py        # Settings endpoints
├── services/
│   ├── llm_service.py     # LLM integration (OpenAI)
│   ├── quiz_service.py    # Quiz logic and generation
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

Since the app uses LLM APIs, here are strategies to minimize costs:

1. **Aggressive caching**: All LLM responses stored in `llm_translations_json`
2. **Model selection**: Use GPT-3.5-turbo for simple tasks, GPT-4 only when needed
3. **Batch requests**: Group multiple translations when possible
4. **Rate limiting**: Prevent API abuse
5. **Local validation**: Simple checks before calling LLM for answer validation

---

## License

This is a student project. License TBD.

---

## Acknowledgments

- Built as a learning project
- Translation and quiz generation powered by OpenAI
- UI styling with Tailwind CSS

---

**Happy Learning!** 🌍📚