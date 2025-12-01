# Quiz System Implementation Guide - Technical Flow

## Overview

This document describes the complete technical flow of the quiz system, broken down into discrete services that can be implemented step by step.

---

## High-Level Flow

```
1. User searches word
   ↓
2. Quiz trigger check (counter reaches threshold)
   ↓
3. Select phrase for quiz (due for review)
   ↓
4. Create quiz attempt record
   ↓
5. Generate question via LLM
   ↓
6. Show quiz to user
   ↓
7. User answers
   ↓
8. Evaluate answer
   ↓
9. Update learning progress
   ↓
10. Repeat cycle
```

---

## Step-by-Step Implementation

### Step 1: User Searches for a Word

**Triggered by:** `POST /api/translate` endpoint

**Actions:**
1. Create or get `Phrase` record (unique on text + language_code)
2. Create or get `PhraseTranslation` records (one per target language)
3. Create `UserSearch` record
4. Create `UserLearningProgress` record (if first time user sees this phrase)
5. Increment `user.searches_since_last_quiz`

**Database Changes:**
```python
# In routes/translation.py

# 1. Get or create phrase
phrase = Phrase.query.filter_by(
    text=text,
    language_code=source_language_code
).first()

if not phrase:
    phrase = Phrase(
        text=text,
        language_code=source_language_code,
        type=determine_phrase_type(text)  # word, phrase, etc.
    )
    db.session.add(phrase)
    db.session.flush()  # Get phrase.id

# 2. Get or create translations (for each target language)
for target_code in target_language_codes:
    translation = PhraseTranslation.query.filter_by(
        phrase_id=phrase.id,
        target_language_code=target_code
    ).first()
    
    if not translation:
        # Call LLM to get translation
        llm_response = llm_service.translate(
            text=text,
            source_language=source_language,
            target_language=target_language,
            context=context_sentence
        )
        
        translation = PhraseTranslation(
            phrase_id=phrase.id,
            target_language_code=target_code,
            translations_json=llm_response,
            model_name='gpt-4.1-mini',
            model_version='2024-11-01'
        )
        db.session.add(translation)

# 3. Create user search record
user_search = UserSearch(
    user_id=current_user.id,
    phrase_id=phrase.id,
    session_id=current_session_id,
    context_sentence=context_sentence,
    llm_translations_json=all_translations  # All target languages
)
db.session.add(user_search)

# 4. Create learning progress (if doesn't exist)
progress = UserLearningProgress.query.filter_by(
    user_id=current_user.id,
    phrase_id=phrase.id
).first()

if not progress:
    progress = UserLearningProgress(
        user_id=current_user.id,
        phrase_id=phrase.id,
        stage='basic',
        next_review_date=date.today()  # Available for quiz immediately
    )
    db.session.add(progress)

# 5. Increment search counter
current_user.searches_since_last_quiz += 1

db.session.commit()
```

---

### Step 2: Quiz Trigger Check Service

**Service:** `QuizTriggerService`  
**Location:** `services/quiz_trigger_service.py`

**Responsibility:** Watch search counter and trigger quiz when threshold is reached

**Implementation:**
```python
class QuizTriggerService:
    """Service to check if quiz should be triggered"""
    
    @staticmethod
    def should_trigger_quiz(user):
        """
        Check if quiz should be triggered for this user
        
        Returns:
            dict: {
                'should_trigger': bool,
                'reason': str,
                'eligible_phrase': UserLearningProgress or None
            }
        """
        # Check if quiz mode is enabled
        if not user.quiz_mode_enabled:
            return {
                'should_trigger': False,
                'reason': 'quiz_mode_disabled',
                'eligible_phrase': None
            }
        
        # Check if search counter reached threshold
        if user.searches_since_last_quiz < user.quiz_frequency:
            return {
                'should_trigger': False,
                'reason': 'threshold_not_reached',
                'searches_remaining': user.quiz_frequency - user.searches_since_last_quiz,
                'eligible_phrase': None
            }
        
        # Find phrase that needs review
        eligible_phrase = QuizTriggerService.get_phrase_for_quiz(user)
        
        if not eligible_phrase:
            return {
                'should_trigger': False,
                'reason': 'no_phrases_due_for_review',
                'eligible_phrase': None
            }
        
        return {
            'should_trigger': True,
            'reason': 'quiz_triggered',
            'eligible_phrase': eligible_phrase
        }
    
    @staticmethod
    def get_phrase_for_quiz(user):
        """
        Select a phrase that's due for review
        
        Priority:
        1. Exclude mastered phrases
        2. Only phrases in user's current active languages
        3. Where next_review_date <= today (include overdue)
        4. Order by next_review_date ASC (oldest first)
        """
        # Get user's active language codes
        active_languages = user.translator_languages  # ['en', 'de', 'ru']
        
        eligible_phrase = UserLearningProgress.query.join(
            Phrase, UserLearningProgress.phrase_id == Phrase.id
        ).filter(
            UserLearningProgress.user_id == user.id,
            UserLearningProgress.stage != 'mastered',  # CRITICAL: exclude mastered
            UserLearningProgress.next_review_date <= date.today(),  # Due or overdue
            Phrase.language_code.in_(active_languages)  # Only active languages
        ).order_by(
            UserLearningProgress.next_review_date.asc()  # Oldest first
        ).first()
        
        return eligible_phrase
```

**Usage in Translation Endpoint:**
```python
# In routes/translation.py - after incrementing search counter

from services.quiz_trigger_service import QuizTriggerService

# Check if quiz should be triggered
quiz_check = QuizTriggerService.should_trigger_quiz(current_user)

response = {
    'phrase_id': phrase.id,
    'translations': translations_dict,
    'should_show_quiz': quiz_check['should_trigger'],
    'searches_until_next_quiz': current_user.quiz_frequency - current_user.searches_since_last_quiz
}

if quiz_check['should_trigger']:
    response['quiz_phrase_id'] = quiz_check['eligible_phrase'].phrase_id
    # Frontend will call GET /api/quiz/next with this phrase_id

return jsonify(response)
```

---

### Step 3: Quiz Attempt Creation Service

**Service:** `QuizAttemptService`  
**Location:** `services/quiz_attempt_service.py`

**Responsibility:** Create quiz attempt record with appropriate question type based on learning stage

**Implementation:**
```python
class QuizAttemptService:
    """Service to create quiz attempt records"""
    
    @staticmethod
    def create_quiz_attempt(user_id, phrase_id):
        """
        Create a new quiz attempt record
        
        Returns:
            QuizAttempt object with question_type set
        """
        # Get learning progress
        progress = UserLearningProgress.query.filter_by(
            user_id=user_id,
            phrase_id=phrase_id
        ).first()
        
        if not progress:
            raise ValueError(f"No learning progress found for user {user_id}, phrase {phrase_id}")
        
        # Determine question type based on stage
        question_type = QuizAttemptService.select_question_type(progress.stage)
        
        # Create quiz attempt (without prompt_json yet - that's for question generation)
        quiz_attempt = QuizAttempt(
            user_id=user_id,
            phrase_id=phrase_id,
            question_type=question_type,
            # prompt_json will be filled by QuestionGenerationService
            # correct_answer will be filled by QuestionGenerationService
            # user_answer will be filled when user submits answer
            # was_correct will be filled by AnswerEvaluationService
        )
        
        db.session.add(quiz_attempt)
        db.session.flush()  # Get quiz_attempt.id
        
        return quiz_attempt
    
    @staticmethod
    def select_question_type(stage):
        """
        Select appropriate question type based on learning stage
        
        Args:
            stage (str): 'basic', 'intermediate', 'advanced', 'mastered'
        
        Returns:
            str: Question type
        """
        import random
        
        question_types = {
            'basic': ['multiple_choice_target', 'multiple_choice_source'],
            'intermediate': ['text_input_target', 'text_input_source'],
            'advanced': ['contextual', 'definition', 'synonym'],
            'mastered': []  # Should never reach here
        }
        
        types = question_types.get(stage, [])
        if not types:
            raise ValueError(f"Invalid stage: {stage}")
        
        return random.choice(types)
```

---

### Step 4: Question Generation Service

**Service:** `QuestionGenerationService`  
**Location:** `services/question_generation_service.py`

**Responsibility:** Generate quiz question via LLM based on question type

**Implementation:**
```python
class QuestionGenerationService:
    """Service to generate quiz questions using LLM"""
    
    @staticmethod
    def generate_question(quiz_attempt):
        """
        Generate quiz question via LLM
        
        Updates quiz_attempt with:
        - prompt_json: Complete question data
        - correct_answer: What system considers correct
        
        Returns:
            dict: Question data to show to user
        """
        # Get phrase and translations
        phrase = Phrase.query.get(quiz_attempt.phrase_id)
        user = User.query.get(quiz_attempt.user_id)
        
        # Get all translations for this phrase
        translations = PhraseTranslation.query.filter_by(
            phrase_id=phrase.id
        ).all()
        
        # Get context sentence if available
        context = UserSearch.query.filter_by(
            user_id=user.id,
            phrase_id=phrase.id
        ).order_by(UserSearch.searched_at.desc()).first()
        
        context_sentence = context.context_sentence if context else None
        
        # Build translation data for LLM
        translations_data = {}
        for trans in translations:
            lang = Language.query.get(trans.target_language_code)
            translations_data[lang.en_name] = trans.translations_json
        
        # Generate question based on type
        question_data = QuestionGenerationService._call_llm_for_question(
            question_type=quiz_attempt.question_type,
            phrase_text=phrase.text,
            phrase_language=phrase.language_code,
            translations=translations_data,
            native_language=user.primary_language_code,
            context_sentence=context_sentence
        )
        
        # Update quiz attempt
        quiz_attempt.prompt_json = question_data['prompt']
        quiz_attempt.correct_answer = question_data['correct_answer']
        
        db.session.commit()
        
        return question_data['prompt']
    
    @staticmethod
    def _call_llm_for_question(question_type, phrase_text, phrase_language, 
                               translations, native_language, context_sentence):
        """
        Call LLM to generate question
        
        Returns:
            dict: {
                'prompt': {
                    'question': str,
                    'options': list (for multiple choice) or None,
                    'question_language': str,
                    'answer_language': str
                },
                'correct_answer': str or list (multiple meanings)
            }
        """
        # Example for multiple_choice_target
        if question_type == 'multiple_choice_target':
            prompt = f"""
Generate a multiple choice question to test translation recognition.

Source phrase: "{phrase_text}"
Source language: {phrase_language}
Target language (native): {native_language}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Question: "What is the {native_language} translation of '{phrase_text}'?"
2. Generate 4 options: 1 correct + 3 distractors
3. If the word has multiple meanings, any should be correct
4. Distractors should be plausible but clearly wrong
5. Return JSON only

Return format:
{{
  "question": "What is the English translation of 'Katze'?",
  "options": ["cat", "dog", "house", "tree"],
  "correct_answer": "cat",  // or ["cat", "feline"] if multiple meanings
  "question_language": "en",
  "answer_language": "en"
}}
"""
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a language learning quiz generator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                'prompt': {
                    'question': result['question'],
                    'options': result['options'],
                    'question_language': result['question_language'],
                    'answer_language': result['answer_language']
                },
                'correct_answer': result['correct_answer']
            }
        
        # Example for contextual
        elif question_type == 'contextual':
            if not context_sentence:
                # Fall back to text_input if no context available
                question_type = 'text_input_target'
                # Recursively call with fallback type
                return QuestionGenerationService._call_llm_for_question(
                    question_type, phrase_text, phrase_language,
                    translations, native_language, None
                )
            
            prompt = f"""
Generate a contextual translation question.

Context sentence: "{context_sentence}"
Word to test: "{phrase_text}"
Source language: {phrase_language}
Target language (native): {native_language}

Available translations: {json.dumps(translations, ensure_ascii=False)}

Requirements:
1. Ask question in SOURCE language ({phrase_language})
2. User answers in their NATIVE language ({native_language})
3. Question format: "In the sentence '{context_sentence}', what does '{phrase_text}' mean?"
4. The correct answer must match the context of the sentence
5. If word has multiple meanings, only the contextually appropriate one is correct
6. Return JSON only

Return format:
{{
  "question": "In the sentence 'Die Katze schläft', what does 'Katze' mean?",
  "correct_answer": "cat",  // Must match context
  "contextual_meaning": "cat (animal)",
  "question_language": "de",
  "answer_language": "en"
}}
"""
            response = openai.ChatCompletion.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a language learning quiz generator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                'prompt': {
                    'question': result['question'],
                    'options': None,  # Text input
                    'question_language': result['question_language'],
                    'answer_language': result['answer_language'],
                    'context_sentence': context_sentence
                },
                'correct_answer': result['correct_answer']
            }
        
        # Implement similar logic for:
        # - multiple_choice_source
        # - text_input_target
        # - text_input_source
        # - definition
        # - synonym
```

**Note on `prompt_json` field:**

The `quiz_attempts.prompt_json` field stores the complete question data shown to the user:

```json
{
  "question": "What is the English translation of 'Katze'?",
  "options": ["cat", "dog", "house", "tree"],  // null for text input
  "question_language": "en",
  "answer_language": "en",
  "context_sentence": "Die Katze schläft"  // only for contextual
}
```

This allows us to:
1. **Reproduce the exact question** for debugging
2. **Show question history** to users
3. **Analyze question quality** and patterns
4. **A/B test different question formats**

---

### Step 5: Show Quiz to User

**Frontend:** Quiz popup/modal/drawer appears

**API Endpoint:** `GET /api/quiz/next`

```python
# In routes/quiz.py

@quiz_bp.route('/next', methods=['GET'])
@login_required
def get_next_quiz():
    """
    Get next quiz question
    
    Optional query param:
    - phrase_id: If provided, quiz this specific phrase (from auto-trigger)
    - Otherwise, select phrase due for review
    """
    phrase_id = request.args.get('phrase_id', type=int)
    
    if phrase_id:
        # Auto-triggered quiz for specific phrase
        progress = UserLearningProgress.query.filter_by(
            user_id=current_user.id,
            phrase_id=phrase_id
        ).first()
    else:
        # Manual practice mode - select phrase
        quiz_check = QuizTriggerService.get_phrase_for_quiz(current_user)
        progress = quiz_check
    
    if not progress:
        return jsonify({'error': 'No phrases due for review'}), 404
    
    # Create quiz attempt
    quiz_attempt = QuizAttemptService.create_quiz_attempt(
        user_id=current_user.id,
        phrase_id=progress.phrase_id
    )
    
    # Generate question
    question_data = QuestionGenerationService.generate_question(quiz_attempt)
    
    # Reset search counter
    current_user.searches_since_last_quiz = 0
    db.session.commit()
    
    return jsonify({
        'quiz_attempt_id': quiz_attempt.id,
        'question': question_data['question'],
        'options': question_data.get('options'),  # null for text input
        'question_type': quiz_attempt.question_type,
        'phrase_id': progress.phrase_id
    })
```

---

### Step 6: User Answers Quiz

**Frontend:** User selects option or types answer

**Action:** POST to `/api/quiz/answer`

---

### Step 7: Answer Evaluation Service

**Service:** `AnswerEvaluationService`  
**Location:** `services/answer_evaluation_service.py`

**Responsibility:** Evaluate user's answer with flexibility

**Implementation:**
```python
class AnswerEvaluationService:
    """Service to evaluate quiz answers"""
    
    @staticmethod
    def evaluate_answer(quiz_attempt_id, user_answer):
        """
        Evaluate user's answer
        
        Returns:
            dict: {
                'was_correct': bool,
                'correct_answer': str or list,
                'user_answer': str,
                'explanation': str,
                'llm_evaluation': dict (optional)
            }
        """
        quiz_attempt = QuizAttempt.query.get(quiz_attempt_id)
        if not quiz_attempt:
            raise ValueError(f"Quiz attempt {quiz_attempt_id} not found")
        
        # Get phrase and translations
        phrase = Phrase.query.get(quiz_attempt.phrase_id)
        translations = PhraseTranslation.query.filter_by(
            phrase_id=phrase.id
        ).all()
        
        # Build all valid answers from translations_json
        valid_answers = AnswerEvaluationService._extract_valid_answers(
            translations=translations,
            question_type=quiz_attempt.question_type,
            prompt_json=quiz_attempt.prompt_json
        )
        
        # Evaluate based on question type
        if quiz_attempt.question_type in ['multiple_choice_target', 'multiple_choice_source']:
            # Simple comparison for multiple choice
            is_correct = AnswerEvaluationService._evaluate_multiple_choice(
                user_answer=user_answer,
                correct_answer=quiz_attempt.correct_answer,
                valid_answers=valid_answers
            )
            explanation = "Correct!" if is_correct else f"The correct answer is: {quiz_attempt.correct_answer}"
            llm_evaluation = None
        
        else:
            # Use LLM for flexible text input evaluation
            evaluation = AnswerEvaluationService._evaluate_with_llm(
                user_answer=user_answer,
                valid_answers=valid_answers,
                question_type=quiz_attempt.question_type,
                context=quiz_attempt.prompt_json.get('context_sentence')
            )
            is_correct = evaluation['is_correct']
            explanation = evaluation['explanation']
            llm_evaluation = evaluation
        
        # Update quiz attempt
        quiz_attempt.user_answer = user_answer
        quiz_attempt.was_correct = is_correct
        quiz_attempt.llm_evaluation_json = llm_evaluation
        
        db.session.commit()
        
        return {
            'was_correct': is_correct,
            'correct_answer': quiz_attempt.correct_answer,
            'user_answer': user_answer,
            'explanation': explanation,
            'llm_evaluation': llm_evaluation
        }
    
    @staticmethod
    def _extract_valid_answers(translations, question_type, prompt_json):
        """
        Extract all valid answers from phrase_translations.translations_json
        
        Returns:
            list: All acceptable answers
        """
        valid_answers = []
        
        for translation in translations:
            trans_json = translation.translations_json
            
            # translations_json format:
            # {
            #   "English": [
            #     ["cat", "noun", "a small domesticated carnivorous mammal"],
            #     ["feline", "noun", "relating to cats"]
            #   ]
            # }
            
            for lang, meanings in trans_json.items():
                for meaning in meanings:
                    word = meaning[0]  # First element is the word
                    valid_answers.append(word)
        
        return valid_answers
    
    @staticmethod
    def _evaluate_multiple_choice(user_answer, correct_answer, valid_answers):
        """Simple exact match for multiple choice"""
        return user_answer.strip().lower() == str(correct_answer).strip().lower()
    
    @staticmethod
    def _evaluate_with_llm(user_answer, valid_answers, question_type, context=None):
        """
        Use LLM to evaluate text input with flexibility
        
        Accepts:
        - With or without articles (cat / the cat / a cat)
        - Lowercase or uppercase (cat / Cat / CAT)
        - Minor typos (caat → cat)
        - Synonyms if they match meaning
        - For contextual: must match context
        """
        prompt = f"""
Evaluate if the user's answer is correct for this language learning quiz.

Question type: {question_type}
Valid answers (any of these is correct): {json.dumps(valid_answers, ensure_ascii=False)}
User's answer: "{user_answer}"
{f'Context sentence: "{context}"' if context else ''}

Evaluation criteria:
1. Accept with or without articles (cat = the cat = a cat)
2. Accept any capitalization (cat = Cat = CAT)
3. Accept minor typos (1-2 character mistakes)
4. For multiple meanings, any valid answer is correct
5. {"For contextual questions: answer MUST match the context of the sentence" if question_type == 'contextual' else ""}

Return JSON only:
{{
  "is_correct": true/false,
  "explanation": "Brief explanation why correct or incorrect",
  "matched_answer": "Which valid answer it matched" or null
}}
"""
        response = openai.ChatCompletion.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a fair language learning quiz evaluator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for consistency
        )
        
        return json.loads(response.choices[0].message.content)
```

---

### Step 8: Update Learning Progress Service

**Service:** `LearningProgressService`  
**Location:** `services/learning_progress_service.py`

**Responsibility:** Update user_learning_progress after quiz

**Implementation:**
```python
class LearningProgressService:
    """Service to update learning progress"""
    
    @staticmethod
    def update_after_quiz(quiz_attempt_id):
        """
        Update learning progress after quiz attempt
        
        Updates:
        - times_reviewed
        - times_correct / times_incorrect
        - stage (if advancement criteria met)
        - next_review_date (spaced repetition)
        - last_reviewed_at
        """
        quiz_attempt = QuizAttempt.query.get(quiz_attempt_id)
        if not quiz_attempt:
            raise ValueError(f"Quiz attempt {quiz_attempt_id} not found")
        
        progress = UserLearningProgress.query.filter_by(
            user_id=quiz_attempt.user_id,
            phrase_id=quiz_attempt.phrase_id
        ).first()
        
        if not progress:
            raise ValueError(f"No progress found for quiz attempt {quiz_attempt_id}")
        
        # Update metrics
        progress.times_reviewed += 1
        if quiz_attempt.was_correct:
            progress.times_correct += 1
        else:
            progress.times_incorrect += 1
        
        progress.last_reviewed_at = datetime.utcnow()
        
        # Check for stage advancement
        old_stage = progress.stage
        if LearningProgressService._should_advance_stage(progress):
            progress.stage = LearningProgressService._get_next_stage(progress.stage)
            
            # Reset counters when advancing to new stage
            progress.times_correct = 0
            progress.times_incorrect = 0
        
        # Calculate next review date
        progress.next_review_date = LearningProgressService._calculate_next_review(
            progress=progress,
            was_correct=quiz_attempt.was_correct
        )
        
        db.session.commit()
        
        return {
            'old_stage': old_stage,
            'new_stage': progress.stage,
            'stage_advanced': old_stage != progress.stage,
            'next_review_date': progress.next_review_date
        }
    
    @staticmethod
    def _should_advance_stage(progress):
        """Check if user should advance to next stage"""
        if progress.stage == 'basic':
            return progress.times_correct >= 2
        elif progress.stage == 'intermediate':
            return progress.times_correct >= 2
        elif progress.stage == 'advanced':
            return progress.times_correct >= 3
        elif progress.stage == 'mastered':
            return False
        return False
    
    @staticmethod
    def _get_next_stage(current_stage):
        """Get next stage in progression"""
        stages = {
            'basic': 'intermediate',
            'intermediate': 'advanced',
            'advanced': 'mastered',
            'mastered': 'mastered'
        }
        return stages.get(current_stage, 'basic')
    
    @staticmethod
    def _calculate_next_review(progress, was_correct):
        """
        Calculate next review date using spaced repetition
        
        Intervals:
        - basic: 1 day (if correct) / same day (if incorrect)
        - intermediate: 3 days (if correct) / 1 day (if incorrect)
        - advanced: 7-14 days (if correct) / 3 days (if incorrect)
        - mastered: None (never review)
        """
        from datetime import timedelta
        
        if progress.stage == 'mastered':
            return None  # Never review mastered words
        
        if was_correct:
            # Correct answer - increase interval
            intervals = {
                'basic': 1,
                'intermediate': 3,
                'advanced': 7 if progress.times_correct < 2 else 14
            }
            days = intervals.get(progress.stage, 1)
        else:
            # Incorrect answer - review soon
            intervals = {
                'basic': 0,  # Same day
                'intermediate': 1,
                'advanced': 3
            }
            days = intervals.get(progress.stage, 1)
        
        return date.today() + timedelta(days=days)
```

---

### Step 9: Complete Quiz Answer Endpoint

**API Endpoint:** `POST /api/quiz/answer`

```python
# In routes/quiz.py

@quiz_bp.route('/answer', methods=['POST'])
@login_required
def submit_quiz_answer():
    """
    Submit quiz answer and get evaluation
    
    Body:
    {
        "quiz_attempt_id": 123,
        "user_answer": "cat"
    }
    """
    data = request.get_json()
    quiz_attempt_id = data.get('quiz_attempt_id')
    user_answer = data.get('user_answer')
    
    if not quiz_attempt_id or user_answer is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Evaluate answer
    evaluation = AnswerEvaluationService.evaluate_answer(
        quiz_attempt_id=quiz_attempt_id,
        user_answer=user_answer
    )
    
    # Update learning progress
    progress_update = LearningProgressService.update_after_quiz(quiz_attempt_id)
    
    return jsonify({
        'was_correct': evaluation['was_correct'],
        'correct_answer': evaluation['correct_answer'],
        'explanation': evaluation['explanation'],
        'stage_advanced': progress_update['stage_advanced'],
        'new_stage': progress_update['new_stage'],
        'next_review_date': progress_update['next_review_date'].isoformat() if progress_update['next_review_date'] else None
    })
```

---

## Summary of Services

| Service | Responsibility | Location |
|---------|---------------|----------|
| `QuizTriggerService` | Check if quiz should trigger, select phrase | `services/quiz_trigger_service.py` |
| `QuizAttemptService` | Create quiz attempt with question type | `services/quiz_attempt_service.py` |
| `QuestionGenerationService` | Generate question via LLM | `services/question_generation_service.py` |
| `AnswerEvaluationService` | Evaluate user answer with flexibility | `services/answer_evaluation_service.py` |
| `LearningProgressService` | Update progress and calculate next review | `services/learning_progress_service.py` |

---

## Database Fields Clarification

### `quiz_attempts.prompt_json`

Stores the complete question data shown to the user:

```json
{
  "question": "What is the English translation of 'Katze'?",
  "options": ["cat", "dog", "house", "tree"],  // null for text input
  "question_language": "en",
  "answer_language": "en",
  "context_sentence": "Die Katze schläft"  // only for contextual questions
}
```

**Benefits:**
1. **Question History** - Users can review past quiz questions
2. **Debugging** - Reproduce exact question for troubleshooting
3. **Analytics** - Analyze which question formats work best
4. **A/B Testing** - Test different question phrasings

---

## Implementation Order

### Phase 1: Basic Quiz Flow (MVP)
1. ✅ Database schema (already done)
2. ✅ Translation endpoint creating user_search + learning_progress
3. QuizTriggerService - basic version (counter check only)
4. QuizAttemptService - create attempt with question type
5. QuestionGenerationService - multiple_choice_target only
6. Simple frontend quiz modal
7. AnswerEvaluationService - exact match for multiple choice
8. LearningProgressService - basic metrics update

### Phase 2: Advanced Question Types
1. Add text_input question generation
2. Add LLM-based flexible answer evaluation
3. Add contextual/definition/synonym questions
4. Improve answer evaluation with context matching

### Phase 3: Spaced Repetition
1. Implement next_review_date calculation
2. Add stage advancement logic
3. Filter mastered phrases from quizzes
4. Add practice mode with different filters

### Phase 4: Polish
1. Store and display question history
2. Analytics dashboard
3. LLM prompt optimization
4. Cost tracking and optimization

---

## Testing Strategy

### Unit Tests
- Test each service independently
- Mock LLM responses
- Test edge cases (no phrases, mastered only, etc.)

### Integration Tests
- Full flow from search → quiz → answer → progress update
- Test stage transitions
- Test spaced repetition intervals

### Manual Testing
- Test all 7 question types
- Test answer flexibility (articles, typos, etc.)
- Test multi-meaning words
- Test contextual matching

---

This completes the technical implementation guide! Each service is focused and testable, making it easy to build incrementally.