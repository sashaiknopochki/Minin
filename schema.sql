// Translator Web App Database Schema

// Reference: ISO 639-1 language codes, spaced repetition for vocabulary learning

Table users {
  id integer [primary key]
  google_id varchar [unique, not null, note: 'Google OAuth identifier']
  email varchar [not null]
  name varchar
  primary_language_code varchar(2) [ref: > languages.code, note: 'language for quiz responses']
  translator_languages json [note: 'array of language codes e.g. ["en", "de", "ru"]']
  quiz_frequency integer [default: 5, note: 'ask quiz every N words']
  quiz_mode_enabled boolean [default: true]
  searches_since_last_quiz integer [default: 0]
  created_at timestamp [default: 'CURRENT_TIMESTAMP']
  last_active_at timestamp
}

Table languages {
  code varchar(2) [primary key, note: 'ISO 639-1 codes: en, de, ru, etc.']
  original_name varchar [not null, note: 'Русский, Deutsch, English']
  en_name varchar [not null, note: 'Russian, German, English']
  display_order integer [note: 'NULL for most, 1,2,3 for popular languages']
}

Table phrases {
  id integer [primary key]
  text varchar [not null]
  language_code varchar(2) [not null, ref: > languages.code]
  created_at timestamp [default: 'CURRENT_TIMESTAMP']
  type varchar [note: 'word, phrase, phrasal_verb, example_sentence']
  is_quizzable boolean [default: true]

  indexes {
    (text, language_code) [unique]
  }
}

Table user_searches {
  id integer [primary key]
  user_id integer [not null, ref: > users.id]
  phrase_id integer [not null, ref: > phrases.id]
  searched_at timestamp [default: 'CURRENT_TIMESTAMP']
  session_id uuid [ref: > sessions.session_id, note: 'UUID for grouping searches in same session']
  context_sentence text [note: 'optional: where user saw the word']
  llm_translations_json json [note: 'cache of all translations e.g. {"en": "cat", "de": "Katze", "ru": "кошка"}']

  indexes {
    user_id
    phrase_id
    session_id
  }
}

Table user_learning_progress {
  id integer [primary key]
  user_id integer [not null, ref: > users.id]
  phrase_id integer [not null, ref: > phrases.id]
  stage varchar [note: 'new, recognition, production, mastered']
  times_reviewed integer [default: 0]
  times_correct integer [default: 0]
  times_incorrect integer [default: 0]
  next_review_date date
  last_reviewed_at timestamp
  created_at timestamp [default: 'CURRENT_TIMESTAMP']

  indexes {
    (user_id, phrase_id) [unique]
    (user_id, next_review_date)
  }
}

Table quiz_attempts {
  id integer [primary key]
  user_id integer [not null, ref: > users.id]
  phrase_id integer [not null, ref: > phrases.id]
  question_type varchar [note: 'multiple_choice_target, multiple_choice_source, text_input_target, text_input_source, contextual, definition, synonym']
  prompt_json json [note: 'what was shown to user e.g. {"question": "Translate: Katze", "options": [...]}']
  correct_answer varchar [note: 'what the system considered correct']
  user_answer varchar
  was_correct boolean [not null]
  llm_evaluation_json json [note: 'optional: store LLM evaluation for debugging']
  attempted_at timestamp [default: 'CURRENT_TIMESTAMP']

  indexes {
    user_id
  }
}

Table phrase_translations {
  id integer [primary key]
  phrase_id integer [not null, ref: > phrases.id]
  target_language_code varchar [not null, ref: > languages.code]
  translations_json json [note: 'LLM response: definitions, examples, synonyms']
  model_name varchar [note: 'e.g., gpt-4o, claude-3.5-sonnet, gemini-1.5-pro']
  model_version varchar [note: 'e.g., 2024-11-01, specific version identifier']
  prompt_hash varchar [note: 'optional: hash of the prompt used']
  created_at timestamp [default: 'CURRENT_TIMESTAMP']

  indexes {
    phrase_id [unique]
  }

}

Table sessions {
  session_id uuid [primary key]
  user_id integer [not null, ref: > users.id]
  started_at timestamp
  ended_at timestamp
}