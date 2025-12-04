Overview

 This plan implements text input questions (text_input_target and text_input_source) for intermediate-stage quizzes with LLM-powered flexible answer evaluation.

 Architecture Summary

 Backend Changes

 1. QuestionGenerationService - Add 2 new generator methods for text input questions
 2. AnswerEvaluationService - Add LLM-based flexible evaluation with fallbacks

 Frontend Changes

 1. Install shadcn Input component - Add text input UI component
 2. QuizDialog - Conditional rendering for text input vs multiple choice

 Key Decisions

 - No API changes needed - Existing endpoints already support options: null and string answers
 - Cost-optimized evaluation - Multi-tier evaluation (exact match → article-insensitive → LLM)
 - Robust fallbacks - Graceful degradation if LLM fails at any stage

 ---
 Phase 1: Backend - Question Generation

 Files to Modify

 - /Users/grace_scale/PycharmProjects/Minin/Minin/services/question_generation_service.py

 Changes Required

 1. Update _call_llm_for_question() routing (Lines 273-278)

 Current code:
 else:
     # For MVP, only multiple choice is supported
     raise ValueError(
         f"Question type '{question_type}' not supported in MVP. "
         f"Supported types: multiple_choice_target, multiple_choice_source"
     )

 Replace with:
 elif question_type == 'text_input_target':
     return QuestionGenerationService._generate_text_input_target(
         client=client,
         phrase_text=phrase_text,
         phrase_language=phrase_language,
         translations=translations,
         native_language=native_language
     )

 elif question_type == 'text_input_source':
     return QuestionGenerationService._generate_text_input_source(
         client=client,
         phrase_text=phrase_text,
         phrase_language=phrase_language,
         translations=translations,
         native_language=native_language
     )

 else:
     # Unsupported question type
     raise ValueError(
         f"Question type '{question_type}' not supported. "
         f"Supported types: multiple_choice_target, multiple_choice_source, "
         f"text_input_target, text_input_source"
     )

 2. Add _generate_text_input_target() method (After line 506)

 @staticmethod
 def _generate_text_input_target(
     client: OpenAI,
     phrase_text: str,
     phrase_language: str,
     translations: Dict[str, Any],
     native_language: str
 ) -> Dict[str, Any]:
     """
     Generate text input question: "Type the [native language] translation of '[phrase]'"

     User sees phrase in source language and types translation in their native language.

     Args:
         client: OpenAI client instance
         phrase_text: The word/phrase to quiz on (e.g., "Katze")
         phrase_language: Language code of the phrase (e.g., "de")
         translations: Dict of translations by language name
         native_language: User's native language code (e.g., "en")

     Returns:
         dict: {
             'prompt': {
                 'question': str,
                 'options': None,  # No options for text input
                 'question_language': str,
                 'answer_language': str
             },
             'correct_answer': str or list
         }
     """
     # Get native language name for the prompt
     native_lang = Language.query.get(native_language)
     native_lang_name = native_lang.en_name if native_lang else "English"

     # Get source language name
     source_lang = Language.query.get(phrase_language)
     source_lang_name = source_lang.en_name if source_lang else phrase_language

     prompt = f"""Generate a text input question to test translation recall (production).

 Source phrase: "{phrase_text}"
 Source language: {source_lang_name}
 Target language (native): {native_lang_name}

 Available translations: {json.dumps(translations, ensure_ascii=False)}

 Requirements:
 1. Question: "Type the {native_lang_name} translation of '{phrase_text}'"
 2. No multiple choice options - user types the answer
 3. If the word has multiple valid meanings, list ALL in correct_answer as an array
 4. Return ONLY valid JSON, no other text

 Return format:
 {{
   "question": "Type the {native_lang_name} translation of '{phrase_text}'",
   "options": null,
   "correct_answer": "cat",
   "question_language": "{native_language}",
   "answer_language": "{native_language}"
 }}

 If multiple meanings exist, use this format:
 {{
   "question": "Type the {native_lang_name} translation of '{phrase_text}'",
   "options": null,
   "correct_answer": ["cat", "feline"],
   "question_language": "{native_language}",
   "answer_language": "{native_language}"
 }}
 """

     system_message = "You are a language learning quiz generator. Return only valid JSON with no additional text."

     # Call LLM with retry logic
     try:
         result = QuestionGenerationService._call_openai_with_retry(
             client=client,
             system_message=system_message,
             user_prompt=prompt
         )

         # Validate response has required fields
         if 'question' not in result or 'correct_answer' not in result:
             logger.warning(f"LLM returned incomplete response for text_input_target: {result}")
             raise ValueError("Incomplete LLM response")

         # Force options to null for text input
         result['options'] = None

         # Return structured response
         return {
             'prompt': {
                 'question': result['question'],
                 'options': None,
                 'question_language': result.get('question_language', native_language),
                 'answer_language': result.get('answer_language', native_language)
             },
             'correct_answer': result['correct_answer']
         }

     except Exception as e:
         logger.error(f"Failed to generate text_input_target question: {str(e)}")
         # Fallback to simple hardcoded question
         return QuestionGenerationService._generate_fallback_question(
             question_type='text_input_target',
             phrase_text=phrase_text,
             phrase_language=phrase_language,
             translations=translations,
             native_language=native_language
         )

 3. Add _generate_text_input_source() method (After _generate_text_input_target)

 @staticmethod
 def _generate_text_input_source(
     client: OpenAI,
     phrase_text: str,
     phrase_language: str,
     translations: Dict[str, Any],
     native_language: str
 ) -> Dict[str, Any]:
     """
     Generate text input question: "Type the [source language] translation of '[native phrase]'"

     User sees phrase in native language and types translation in source language.
     This is more challenging as user must produce the foreign language word.

     Args:
         client: OpenAI client instance
         phrase_text: The word/phrase in source language (e.g., "Katze")
         phrase_language: Language code of the phrase (e.g., "de")
         translations: Dict of translations by language name
         native_language: User's native language code (e.g., "en")

     Returns:
         dict: {
             'prompt': {
                 'question': str,
                 'options': None,
                 'question_language': str,
                 'answer_language': str
             },
             'correct_answer': str
         }
     """
     # Get native language name
     native_lang = Language.query.get(native_language)
     native_lang_name = native_lang.en_name if native_lang else "English"

     # Get source language name
     source_lang = Language.query.get(phrase_language)
     source_lang_name = source_lang.en_name if source_lang else phrase_language

     # Extract a native translation to show in question
     native_translation = None
     for lang_name, trans_data in translations.items():
         if isinstance(trans_data, list) and len(trans_data) > 0:
             if isinstance(trans_data[0], list) and len(trans_data[0]) > 0:
                 native_translation = trans_data[0][0]  # First word of first meaning
                 break

     if not native_translation:
         logger.warning(f"No native translation found for {phrase_text}, using phrase itself")
         native_translation = phrase_text

     prompt = f"""Generate a reverse text input question to test production in the target language.

 Native word: "{native_translation}"
 Native language: {native_lang_name}
 Target language (to type): {source_lang_name}
 Correct answer in {source_lang_name}: "{phrase_text}"

 Available translations: {json.dumps(translations, ensure_ascii=False)}

 Requirements:
 1. Question: "Type the {source_lang_name} word for '{native_translation}'"
 2. No multiple choice options - user types the answer
 3. The correct answer is the original phrase: "{phrase_text}"
 4. Return ONLY valid JSON, no other text

 Return format:
 {{
   "question": "Type the {source_lang_name} word for '{native_translation}'",
   "options": null,
   "correct_answer": "{phrase_text}",
   "question_language": "{native_language}",
   "answer_language": "{phrase_language}"
 }}
 """

     system_message = "You are a language learning quiz generator. Return only valid JSON with no additional text."

     # Call LLM with retry logic
     try:
         result = QuestionGenerationService._call_openai_with_retry(
             client=client,
             system_message=system_message,
             user_prompt=prompt
         )

         # Validate response
         if 'question' not in result or 'correct_answer' not in result:
             logger.warning(f"LLM returned incomplete response for text_input_source: {result}")
             raise ValueError("Incomplete LLM response")

         # Force options to null
         result['options'] = None

         # Return structured response
         return {
             'prompt': {
                 'question': result['question'],
                 'options': None,
                 'question_language': result.get('question_language', native_language),
                 'answer_language': result.get('answer_language', phrase_language)
             },
             'correct_answer': result['correct_answer']
         }

     except Exception as e:
         logger.error(f"Failed to generate text_input_source question: {str(e)}")
         # Fallback to simple hardcoded question
         return QuestionGenerationService._generate_fallback_question(
             question_type='text_input_source',
             phrase_text=phrase_text,
             phrase_language=phrase_language,
             translations=translations,
             native_language=native_language
         )

 4. Update _generate_fallback_question() to support text input (Lines 509-601)

 Add these cases after the existing multiple choice fallback logic:

 # After the multiple_choice_source case, add:

 elif question_type == 'text_input_target':
     # Simple text input: "Type the English translation of 'Katze'"
     native_lang = Language.query.get(native_language)
     native_lang_name = native_lang.en_name if native_lang else "English"

     source_lang = Language.query.get(phrase_language)
     source_lang_name = source_lang.en_name if source_lang else phrase_language

     # Extract first translation as correct answer
     correct = first_translation

     return {
         'prompt': {
             'question': f"Type the {native_lang_name} translation of '{phrase_text}'",
             'options': None,
             'question_language': native_language,
             'answer_language': native_language
         },
         'correct_answer': correct
     }

 elif question_type == 'text_input_source':
     # Reverse text input: "Type the German word for 'cat'"
     native_lang = Language.query.get(native_language)
     native_lang_name = native_lang.en_name if native_lang else "English"

     source_lang = Language.query.get(phrase_language)
     source_lang_name = source_lang.en_name if source_lang else phrase_language

     # Use first translation as the prompt
     native_word = first_translation

     return {
         'prompt': {
             'question': f"Type the {source_lang_name} word for '{native_word}'",
             'options': None,
             'question_language': native_language,
             'answer_language': phrase_language
         },
         'correct_answer': phrase_text
     }

 ---
 Phase 2: Backend - Answer Evaluation

 Files to Modify

 - /Users/grace_scale/PycharmProjects/Minin/Minin/services/answer_evaluation_service.py

 Changes Required

 1. Remove question type restriction (Lines 116-122)

 Current code:
 # Validate question type (MVP: multiple choice only)
 supported_types = ['multiple_choice_target', 'multiple_choice_source']
 if quiz_attempt.question_type not in supported_types:
     raise ValueError(
         f"Question type '{quiz_attempt.question_type}' not supported in MVP. "
         f"Supported types: {', '.join(supported_types)}"
     )

 Replace with:
 # Validate question type
 supported_types = [
     'multiple_choice_target',
     'multiple_choice_source',
     'text_input_target',
     'text_input_source'
 ]
 if quiz_attempt.question_type not in supported_types:
     raise ValueError(
         f"Question type '{quiz_attempt.question_type}' not supported. "
         f"Supported types: {', '.join(supported_types)}"
     )

 2. Add conditional evaluation logic (Lines 124-133)

 Current code:
 # Extract valid answers
 valid_answers = AnswerEvaluationService._extract_valid_answers(
     quiz_attempt.correct_answer
 )

 # Evaluate answer
 was_correct = AnswerEvaluationService._evaluate_multiple_choice(
     user_answer=user_answer,
     valid_answers=valid_answers
 )

 Replace with:
 # Extract valid answers
 valid_answers = AnswerEvaluationService._extract_valid_answers(
     quiz_attempt.correct_answer
 )

 # Evaluate answer based on question type
 if quiz_attempt.question_type in ['multiple_choice_target', 'multiple_choice_source']:
     # Simple exact match for multiple choice
     was_correct = AnswerEvaluationService._evaluate_multiple_choice(
         user_answer=user_answer,
         valid_answers=valid_answers
     )
 else:
     # Text input: use flexible evaluation with LLM
     # Get translations_json for context
     phrase = Phrase.query.get(quiz_attempt.phrase_id)
     translations = PhraseTranslation.query.filter_by(phrase_id=phrase.id).all()

     # Build translations dict for LLM context
     translations_dict = {}
     for trans in translations:
         try:
             lang = Language.query.get(trans.target_language_code)
             if lang and trans.translations_json:
                 translations_dict[lang.en_name] = trans.translations_json
         except Exception as e:
             logger.warning(f"Failed to process translation {trans.id}: {str(e)}")

     was_correct = AnswerEvaluationService._evaluate_with_llm(
         user_answer=user_answer,
         valid_answers=valid_answers,
         question_type=quiz_attempt.question_type,
         translations_dict=translations_dict,
         phrase_text=phrase.text
     )

 3. Add imports at top of file (After line 18)

 from models.phrase import Phrase
 from models.phrase_translation import PhraseTranslation
 from models.language import Language
 from openai import OpenAI
 from dotenv import load_dotenv
 import os

 4. Add _evaluate_with_llm() method (After line 292)

 @staticmethod
 def _evaluate_with_llm(
     user_answer: str,
     valid_answers: List[str],
     question_type: str,
     translations_dict: Dict[str, Any],
     phrase_text: str
 ) -> bool:
     """
     Use multi-tier evaluation strategy for text input answers.

     Evaluation tiers (in order):
     1. Exact match (fast path, no LLM call)
     2. Article-insensitive match ("cat" == "the cat")
     3. LLM-based flexible evaluation (typos, synonyms, capitalization)
     4. Fallback to strict matching if LLM fails

     Args:
         user_answer: User's submitted answer
         valid_answers: List of acceptable answers
         question_type: Type of question being evaluated
         translations_dict: Full translations_json for context
         phrase_text: Original phrase being quizzed

     Returns:
         bool: True if answer is correct, False otherwise
     """
     # Normalize user answer
     user_normalized = user_answer.strip().lower()

     # Tier 1: Exact match (fast path)
     for valid in valid_answers:
         if user_normalized == valid.strip().lower():
             logger.info(f"Answer '{user_answer}' matched exactly: {valid}")
             return True

     # Tier 2: Article-insensitive match
     # Remove common articles: a, an, the
     user_no_article = user_normalized
     for article in ['the ', 'a ', 'an ']:
         if user_no_article.startswith(article):
             user_no_article = user_no_article[len(article):]
             break

     for valid in valid_answers:
         valid_no_article = valid.strip().lower()
         for article in ['the ', 'a ', 'an ']:
             if valid_no_article.startswith(article):
                 valid_no_article = valid_no_article[len(article):]
                 break

         if user_no_article == valid_no_article:
             logger.info(f"Answer '{user_answer}' matched without article: {valid}")
             return True

     # Tier 3: LLM-based flexible evaluation
     try:
         load_dotenv()
         api_key = os.getenv("OPENAI_API_KEY")
         if not api_key:
             logger.warning("OPENAI_API_KEY not found, skipping LLM evaluation")
             return False

         client = OpenAI(api_key=api_key)

         # Build evaluation prompt
         prompt = f"""Evaluate if the user's answer is correct for this language learning quiz.

 Question type: {question_type}
 Phrase being quizzed: "{phrase_text}"
 Valid answers (any of these is correct): {json.dumps(valid_answers, ensure_ascii=False)}
 Full translation data: {json.dumps(translations_dict, ensure_ascii=False)}
 User's answer: "{user_answer}"

 Evaluation criteria:
 1. Accept with or without articles (cat = the cat = a cat)
 2. Accept any capitalization (cat = Cat = CAT)
 3. Accept minor typos (1-2 character mistakes, e.g., "caat" for "cat")
 4. Accept any synonym that appears in the translation data
 5. Accept any valid meaning from the translations_json
 6. Reject if the answer is clearly a different word or concept

 Return ONLY valid JSON, no other text:
 {{
   "is_correct": true or false,
   "explanation": "Brief explanation why correct or incorrect",
   "matched_answer": "Which valid answer it matched (or null if incorrect)"
 }}
 """

         system_message = "You are a fair language learning quiz evaluator. Be lenient with minor errors but strict about meaning. Return only valid JSON."

         response = client.chat.completions.create(
             model=DEFAULT_MODEL,
             messages=[
                 {"role": "system", "content": system_message},
                 {"role": "user", "content": prompt}
             ],
             temperature=0.3,  # Lower temperature for consistency
             max_tokens=200,
             timeout=10.0
         )

         result_text = response.choices[0].message.content.strip()
         result = json.loads(result_text)

         is_correct = result.get('is_correct', False)
         explanation = result.get('explanation', 'No explanation provided')

         logger.info(
             f"LLM evaluation: user_answer='{user_answer}', "
             f"is_correct={is_correct}, explanation='{explanation}'"
         )

         return is_correct

     except json.JSONDecodeError as e:
         logger.error(f"LLM returned invalid JSON: {str(e)}")
         return False

     except Exception as e:
         logger.error(f"LLM evaluation failed: {str(e)}")
         # Tier 4: Fallback to strict matching
         logger.info("Falling back to strict matching")
         return False

 5. Add DEFAULT_MODEL constant (After line 21)

 # OpenAI model for answer evaluation
 DEFAULT_MODEL = "gpt-4o-mini"  # Cost-effective model for evaluation

 ---
 Phase 3: Frontend - Install shadcn Input Component

 Command to Run

 cd /Users/grace_scale/PycharmProjects/Minin/Minin/frontend
 npx shadcn@latest add input

 Expected Files Created

 - /Users/grace_scale/PycharmProjects/Minin/Minin/frontend/src/components/ui/input.tsx

 No Vite Proxy Changes Needed

 The Vite config at /Users/grace_scale/PycharmProjects/Minin/Minin/frontend/vite.config.ts already has all necessary proxies configured (lines 14-32).

 ---
 Phase 4: Frontend - Update QuizDialog Component

 Files to Modify

 - /Users/grace_scale/PycharmProjects/Minin/Minin/frontend/src/components/QuizDialog.tsx

 Changes Required

 1. Add Input import (Line 10)

 import { Input } from "@/components/ui/input"

 2. Update QuizData interface (Lines 13-19)

 Current:
 export interface QuizData {
   quiz_attempt_id: number
   question: string
   options: string[]
   question_type: string
   phrase_id: number
 }

 Replace with:
 export interface QuizData {
   quiz_attempt_id: number
   question: string
   options: string[] | null  // null for text input questions
   question_type: string
   phrase_id: number
 }

 3. Add state for text input (After line 47)

 const [textAnswer, setTextAnswer] = React.useState("")

 // Reset text answer when quiz changes
 React.useEffect(() => {
   setTextAnswer("")
 }, [quizData.quiz_attempt_id])

 4. Add text input submit handler (After line 52)

 const handleTextSubmit = () => {
   if (!result && textAnswer.trim()) {
     onSubmit(textAnswer.trim())
   }
 }

 const handleKeyDown = (e: React.KeyboardEvent) => {
   if (e.key === "Enter" && !result && textAnswer.trim()) {
     handleTextSubmit()
   }
 }

 5. Update answer display section (Lines 145-169)

 Replace the entire section:

 <div className="py-6 space-y-4">
   <h3 className="text-2xl font-semibold mb-6 text-foreground leading-relaxed">
     {quizData.question}
   </h3>

   {quizData.options === null ? (
     // Text input question
     <div className="space-y-4">
       <Input
         type="text"
         placeholder="Type your answer..."
         value={textAnswer}
         onChange={(e) => setTextAnswer(e.target.value)}
         onKeyDown={handleKeyDown}
         disabled={!!result}
         className="text-lg py-6"
         autoFocus
       />

       {!result && (
         <Button
           onClick={handleTextSubmit}
           disabled={!textAnswer.trim()}
           className="w-full py-6 text-lg"
         >
           Submit Answer
         </Button>
       )}

       {result && (
         <div className={`p-4 rounded-lg ${result.was_correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
           <div className="flex items-center gap-2 mb-2">
             {result.was_correct ? (
               <>
                 <Check className="h-5 w-5 text-green-600" />
                 <span className="font-semibold text-green-900">Correct!</span>
               </>
             ) : (
               <>
                 <X className="h-5 w-5 text-red-600" />
                 <span className="font-semibold text-red-900">Incorrect</span>
               </>
             )}
           </div>
           <p className="text-sm">
             Your answer: <strong className={result.was_correct ? '' : 'line-through'}>{result.user_answer}</strong>
           </p>
           {!result.was_correct && (
             <p className="text-sm mt-1">
               Correct answer: <strong>{result.correct_answer}</strong>
             </p>
           )}
         </div>
       )}
     </div>
   ) : (
     // Multiple choice question
     <div className="flex flex-col gap-3">
       {quizData.options.map((option, index) => (
         <Button
           key={index}
           variant="outline"
           onClick={() => handleAnswerClick(option)}
           disabled={!!result}
           className={getButtonClassName(option)}
         >
           <span className={getButtonTextClassName(option)}>
             {option}
           </span>
           {getButtonIcon(option)}
         </Button>
       ))}

       {getFeedbackMessage()}
     </div>
   )}
 </div>

 ---
 Testing Plan

 Backend Testing

 1. Test Question Generation

 # Test text_input_target generation
 python -c "
 from services.question_generation_service import QuestionGenerationService
 from models import db
 from app import create_app

 app = create_app('development')
 with app.app_context():
     # Get a test quiz attempt for intermediate stage
     from models.quiz_attempt import QuizAttempt
     attempt = QuizAttempt.query.filter_by(question_type='text_input_target').first()

     if attempt:
         result = QuestionGenerationService.generate_question(attempt)
         print('Generated question:', result)
     else:
         print('No text_input_target quiz attempts found')
 "

 2. Test Answer Evaluation

 # Test flexible evaluation
 python -c "
 from services.answer_evaluation_service import AnswerEvaluationService
 from app import create_app

 app = create_app('development')
 with app.app_context():
     # Test various answer formats
     test_cases = [
         ('cat', ['cat']),          # Exact match
         ('Cat', ['cat']),          # Capitalization
         ('the cat', ['cat']),      # With article
         ('caat', ['cat']),         # Minor typo
     ]

     for user_answer, valid_answers in test_cases:
         result = AnswerEvaluationService._evaluate_with_llm(
             user_answer=user_answer,
             valid_answers=valid_answers,
             question_type='text_input_target',
             translations_dict={},
             phrase_text='Katze'
         )
         print(f'{user_answer} -> {result}')
 "

 Frontend Testing

 1. Manual UI Testing

 1. Start development servers
 2. Navigate to quiz page
 3. Trigger intermediate quiz (after stage advancement)
 4. Verify text input appears
 5. Test Enter key submission
 6. Test Submit button
 7. Test feedback display
 8. Test answer validation

 2. Test Edge Cases

 - Empty input (submit button should be disabled)
 - Special characters (å, ü, ñ)
 - Very long answers (200+ characters)
 - Rapid Enter key presses
 - Network errors during submission

 Integration Testing

 Full Flow Test

 1. User at intermediate stage
 2. Search counter reaches threshold
 3. GET /quiz/next returns text input question
 4. User types answer and submits
 5. POST /quiz/answer evaluates with LLM
 6. Learning progress updates correctly
 7. Next review date calculated

 ---
 Rollback Plan

 If issues arise during implementation:

 Backend Rollback

 1. Revert changes to question_generation_service.py
 2. Revert changes to answer_evaluation_service.py
 3. Database schema unchanged (no rollback needed)

 Frontend Rollback

 1. Revert changes to QuizDialog.tsx
 2. Remove shadcn Input component (optional)

 Quick Rollback Command

 git checkout HEAD -- \
   Minin/services/question_generation_service.py \
   Minin/services/answer_evaluation_service.py \
   Minin/frontend/src/components/QuizDialog.tsx

 ---
 Cost Estimates

 Based on 1000 active users, assuming 50% reach intermediate stage:

 Monthly Estimates

 - Text input questions generated: ~1,250/day (500 users × 2.5 quizzes/day)
 - Question generation cost: $0.0004/question = $15/month
 - Answer evaluations with LLM: ~40% require LLM (others use exact/article match)
 - Evaluation cost: $0.0003/evaluation × 500/day = $4.50/month

 Total additional cost: ~$19.50/month

 Optimization Opportunities

 1. Cache common typos and their evaluations
 2. Use cheaper model (gpt-4o-mini vs gpt-4o)
 3. Batch evaluations when possible
 4. Increase article-matching coverage

 ---
 Critical Files Summary

 Files to Modify

 1. /Users/grace_scale/PycharmProjects/Minin/Minin/services/question_generation_service.py (3 methods + routing)
 2. /Users/grace_scale/PycharmProjects/Minin/Minin/services/answer_evaluation_service.py (1 method + evaluation logic)
 3. /Users/grace_scale/PycharmProjects/Minin/Minin/frontend/src/components/QuizDialog.tsx (conditional rendering)

 Files to Create

 1. /Users/grace_scale/PycharmProjects/Minin/Minin/frontend/src/components/ui/input.tsx (via shadcn CLI)

 No Changes Needed

 - API routes (/quiz/next, /quiz/answer)
 - Database schema
 - Models
 - Vite configuration

 ---
 Implementation Order

 Step 1: Backend Question Generation (30 min)

 1. Update _call_llm_for_question() routing
 2. Add _generate_text_input_target()
 3. Add _generate_text_input_source()
 4. Update _generate_fallback_question()
 5. Test with Python script

 Step 2: Backend Answer Evaluation (45 min)

 1. Add imports
 2. Remove question type restriction
 3. Add conditional evaluation logic
 4. Add _evaluate_with_llm()
 5. Add DEFAULT_MODEL constant
 6. Test with Python script

 Step 3: Frontend Setup (5 min)

 1. Install shadcn Input component
 2. Verify installation

 Step 4: Frontend QuizDialog (30 min)

 1. Add Input import
 2. Update QuizData interface
 3. Add text input state
 4. Add submit handlers
 5. Update render logic with conditional
 6. Test in browser

 Step 5: Integration Testing (30 min)

 1. Test full flow end-to-end
 2. Verify LLM evaluation works
 3. Test edge cases
 4. Verify learning progress updates

 Total estimated time: 2-2.5 hours

 ---
 Success Criteria

 ✅ Backend generates text input questions correctly
 ✅ LLM evaluation accepts valid variations (articles, capitalization, minor typos)
 ✅ Frontend shows text input field for text_input_* questions
 ✅ Frontend shows multiple choice buttons for multiple_choice_* questions
 ✅ Submit button works and validates input
 ✅ Enter key submission works
 ✅ Feedback displays correctly for text input
 ✅ Learning progress updates correctly
 ✅ Cost per evaluation < $0.001
 ✅ Evaluation latency < 2 seconds

 ---
 Questions for User

 Before implementation, please confirm:

 1. LLM Model Choice: Use gpt-4o-mini for cost ($0.150/1M input tokens) vs gpt-4o for quality?
 2. Evaluation Strictness: Should we accept minor typos (1-2 chars) or be stricter?
 3. Article Handling: Accept all articles (a/an/the) or just specific ones?
 4. Feedback Detail: Show LLM explanation for why answer was correct/incorrect?
 5. Timeout: 10 seconds for LLM evaluation is reasonable?

 ---
 Next Steps

 After plan approval:
 1. Review plan with user
 2. Address any questions or concerns
 3. Begin implementation following the step-by-step order
 4. Test each phase before moving to next
 5. Deploy to production after full testing