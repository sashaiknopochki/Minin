-- Core Tables --

users
- id (PRIMARY KEY)
- email (from Google OAuth)
- name (from Google OAuth)
- google_id (unique identifier from Google)
- primary_language_id (FOREIGN KEY → languages.id, nullable)
- created_at
- last_login_at
- settings_json (quiz frequency, etc.)

languages
- id (PRIMARY KEY)
- code (e.g., 'en', 'de', 'ru')
- name (e.g., 'English', 'German', 'Russian')
- flag_emoji (🇬🇧, 🇩🇪, 🇷🇺)

phrases  -- renamed from 'words' to handle both words and phrases
- id (PRIMARY KEY)
- text (the word or phrase)
- language_id (FOREIGN KEY → languages.id)
- type ('word', 'phrase', 'phrasal_verb')
- created_at
- UNIQUE(text, language_id)

user_searches
- id (PRIMARY KEY)
- user_id (FOREIGN KEY → users.id)
- phrase_id (FOREIGN KEY → phrases.id)
- searched_at
- session_id (UUID to group searches in same session)
- llm_translations_json (cache the LLM response with all translations)

user_learning_progress
- id (PRIMARY KEY)
- user_id (FOREIGN KEY → users.id)
- phrase_id (FOREIGN KEY → phrases.id)
- learning_stage ('new', 'recognition', 'production', 'mastered')
- repetition_count (how many times reviewed)
- ease_factor (2.5 default, adjusts based on difficulty)
- interval_days (current interval for spaced repetition)
- next_review_date
- last_reviewed_at
- created_at
- UNIQUE(user_id, phrase_id)

quiz_attempts
- id (PRIMARY KEY)
- user_id (FOREIGN KEY → users.id)
- phrase_id (FOREIGN KEY → phrases.id)
- quiz_language_id (FOREIGN KEY → languages.id, the language they answered in)
- quiz_type ('multiple_choice', 'text_input')
- prompt_json (what was shown to user)
- correct_answer (what LLM considered correct)
- user_answer
- was_correct (boolean)
- llm_evaluation_json (store LLM's evaluation for debugging)
- attempted_at

user_sessions
- id (PRIMARY KEY)
- user_id (FOREIGN KEY → users.id)
- session_id (UUID)
- languages_json (array of language codes used in session)
- started_at
- ended_at