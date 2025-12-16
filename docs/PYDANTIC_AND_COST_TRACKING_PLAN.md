# Implementation Plan: Pydantic Structured Outputs + Cost Tracking

## Executive Summary

Migrate all LLM calls to use Pydantic BaseModel structured outputs and implement comprehensive cost tracking across the application. This plan covers 3 major LLM services (translation, question generation, answer evaluation) and establishes infrastructure for detailed operation-level and aggregated session-level cost tracking.

## Key Requirements

1. **Pydantic Structured Outputs**: Replace manual JSON parsing with modern `.parse()` methods for both OpenAI and Mistral
2. **Backward Compatibility**: Graceful fallback to manual JSON parsing if structured outputs fail
3. **Cost Tracking**: Calculate and store costs per operation + aggregate per session for monthly queries
4. **Pricing**: gpt-4o-mini ($0.15 input, $0.60 output per 1M tokens), mistral-small-latest ($0.10 input, $0.30 output per 1M tokens)

---

## Phase 1: Foundation Infrastructure (2-3 days)

### 1.1 Create LLM Pricing Database Table

**New migration file**: `migrations/versions/[timestamp]_create_llm_pricing_table.py`

```sql
CREATE TABLE llm_pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider VARCHAR(20) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    input_cost_per_1m DECIMAL(10, 4) NOT NULL,
    output_cost_per_1m DECIMAL(10, 4) NOT NULL,
    cached_input_cost_per_1m DECIMAL(10, 4),
    effective_date DATETIME NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, model_name, effective_date)
);

-- Seed pricing data
INSERT INTO llm_pricing (provider, model_name, input_cost_per_1m, output_cost_per_1m, cached_input_cost_per_1m, effective_date) VALUES
('openai', 'gpt-4o-mini', 0.1500, 0.6000, 0.0750, '2025-01-01'),
('mistral', 'mistral-small-latest', 0.1000, 0.3000, NULL, '2025-01-01');
```

### 1.2 Create Cost Calculation Service

**New file**: `services/cost_service.py`

Core functions:
- `calculate_cost(provider, model, prompt_tokens, completion_tokens, cached_tokens=0) -> Decimal`
- `_get_pricing(provider, model) -> Dict` (with 1-hour cache)
- `get_monthly_cost(user_id, year, month) -> Dict` (queries session aggregates)

### 1.3 Create Pydantic Model Files

**New directory**: `services/llm_models/`

Three new files:
1. `translation_models.py`: TranslationEntry, TranslationResponse (move from llm_translation_service.py)
2. `question_models.py`: MultipleChoiceQuestion, TextInputQuestion, ContextualQuestion, DefinitionQuestion, SynonymQuestion
3. `evaluation_models.py`: AnswerEvaluation (is_correct, explanation, matched_answer, confidence)

### 1.4 Update LLM Provider Interface

**Update file**: `services/llm_provider_factory.py`

Add new abstract method to LLMProvider:
```python
@abstractmethod
def create_structured_completion(
    self,
    messages: List[Dict[str, str]],
    response_model: Type[BaseModel],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
    timeout: float = 30.0,
    **kwargs
) -> Dict[str, Any]:
    """Returns: {parsed_object, raw_content, model, usage{prompt_tokens, completion_tokens, total_tokens, cached_tokens}, raw_response}"""
    pass

@abstractmethod
def get_provider_name(self) -> str:
    """Return 'openai' or 'mistral' for cost lookup"""
    pass
```

Implement for both OpenAIProvider and MistralProvider:
- OpenAI: Use `self.client.beta.chat.completions.parse()` with fallback
- Mistral: Use `self.client.chat.parse()` with fallback
- Both: Extract cached_tokens (OpenAI only, 0 for Mistral)

---

## Phase 2: Database Schema for Cost Tracking (1 day)

### 2.1 Add Cost Fields to phrase_translations

**Migration file**: `migrations/versions/[timestamp]_add_cost_to_phrase_translations.py`

```sql
ALTER TABLE phrase_translations ADD COLUMN prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE phrase_translations ADD COLUMN completion_tokens INTEGER DEFAULT 0;
ALTER TABLE phrase_translations ADD COLUMN total_tokens INTEGER DEFAULT 0;
ALTER TABLE phrase_translations ADD COLUMN cached_tokens INTEGER DEFAULT 0;
ALTER TABLE phrase_translations ADD COLUMN estimated_cost_usd DECIMAL(10, 6) DEFAULT 0.0;
ALTER TABLE phrase_translations ADD COLUMN cost_calculated_at DATETIME;
```

**Critical file**: `models/phrase_translation.py` - Add new columns to model class

### 2.2 Add Cost Fields to quiz_attempts

**Migration file**: `migrations/versions/[timestamp]_add_cost_to_quiz_attempts.py`

```sql
-- Question generation cost
ALTER TABLE quiz_attempts ADD COLUMN question_gen_prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE quiz_attempts ADD COLUMN question_gen_completion_tokens INTEGER DEFAULT 0;
ALTER TABLE quiz_attempts ADD COLUMN question_gen_total_tokens INTEGER DEFAULT 0;
ALTER TABLE quiz_attempts ADD COLUMN question_gen_cost_usd DECIMAL(10, 6) DEFAULT 0.0;
ALTER TABLE quiz_attempts ADD COLUMN question_gen_model VARCHAR(50);

-- Answer evaluation cost (for LLM-based evaluation)
ALTER TABLE quiz_attempts ADD COLUMN eval_prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE quiz_attempts ADD COLUMN eval_completion_tokens INTEGER DEFAULT 0;
ALTER TABLE quiz_attempts ADD COLUMN eval_total_tokens INTEGER DEFAULT 0;
ALTER TABLE quiz_attempts ADD COLUMN eval_cost_usd DECIMAL(10, 6) DEFAULT 0.0;
ALTER TABLE quiz_attempts ADD COLUMN eval_model VARCHAR(50);
```

**Critical file**: `models/quiz_attempt.py` - Add new columns to model class

### 2.3 Add Cost Aggregation to sessions

**Migration file**: `migrations/versions/[timestamp]_add_cost_aggregation_to_sessions.py`

```sql
ALTER TABLE sessions ADD COLUMN total_translation_cost_usd DECIMAL(10, 4) DEFAULT 0.0;
ALTER TABLE sessions ADD COLUMN total_quiz_cost_usd DECIMAL(10, 4) DEFAULT 0.0;
ALTER TABLE sessions ADD COLUMN total_cost_usd DECIMAL(10, 4) DEFAULT 0.0;
ALTER TABLE sessions ADD COLUMN operations_count INTEGER DEFAULT 0;

-- Index for efficient monthly queries
CREATE INDEX ix_sessions_user_started ON sessions(user_id, started_at);
```

**Critical file**: `models/session.py` - Add new columns to model class

### 2.4 Session Cost Aggregator Helper

**New file**: `services/session_cost_aggregator.py`

Functions:
- `add_translation_cost(session_id, cost_usd)` - Updates session.total_translation_cost_usd
- `add_quiz_cost(session_id, cost_usd)` - Updates session.total_quiz_cost_usd

---

## Phase 3: Migrate Translation Service (2 days)

### 3.1 Update llm_translation_service.py

**Critical file**: `services/llm_translation_service.py`

**Current state**: Lines 216-296 use `provider.create_chat_completion()` with manual JSON schema building

**Changes**:
1. Import new Pydantic models from `services.llm_models.translation_models`
2. Import `CostCalculationService` and `SessionCostAggregator`
3. Replace manual schema building (lines 244-282) with:
   ```python
   response = provider.create_structured_completion(
       messages=messages,
       response_model=TranslationResponse,
       model=model,
       temperature=0.2,
       max_tokens=1000
   )
   parsed_response = response["parsed_object"]
   ```
4. Calculate cost immediately after LLM call:
   ```python
   cost_usd = CostCalculationService.calculate_cost(
       provider=provider.get_provider_name(),
       model=response["model"],
       prompt_tokens=response["usage"]["prompt_tokens"],
       completion_tokens=response["usage"]["completion_tokens"],
       cached_tokens=response["usage"]["cached_tokens"]
   )
   ```
5. Return cost in response dict: `"cost_usd": float(cost_usd)`

### 3.2 Update phrase_translation_service.py

**Critical file**: `services/phrase_translation_service.py`

**Changes**:
1. When creating/updating PhraseTranslation objects, store token counts and cost:
   ```python
   phrase_translation.prompt_tokens = usage["prompt_tokens"]
   phrase_translation.completion_tokens = usage["completion_tokens"]
   phrase_translation.total_tokens = usage["total_tokens"]
   phrase_translation.cached_tokens = usage["cached_tokens"]
   phrase_translation.estimated_cost_usd = float(cost_usd)
   phrase_translation.cost_calculated_at = datetime.utcnow()
   ```
2. Aggregate to session if session_id available:
   ```python
   if session_id:
       SessionCostAggregator.add_translation_cost(session_id, cost_usd)
   ```

---

## Phase 4: Migrate Question Generation Service (3-4 days)

### 4.1 Create Question Type Pydantic Models

**File**: `services/llm_models/question_models.py` (created in Phase 1)

5 models for 7 question types:
- `MultipleChoiceQuestion` (for multiple_choice_target, multiple_choice_source)
- `TextInputQuestion` (for text_input_target, text_input_source)
- `ContextualQuestion` (extends TextInputQuestion with context_sentence)
- `DefinitionQuestion` (for definition type)
- `SynonymQuestion` (for synonym type)

### 4.2 Update Question Generation Methods

**Critical file**: `services/question_generation_service.py`

**Current state**: 7 question generation methods use manual JSON parsing with `_strip_markdown_code_fences()`

**Changes for each method** (lines 381-1231):
1. `_generate_multiple_choice_target()` - Use `MultipleChoiceQuestion` model
2. `_generate_multiple_choice_source()` - Use `MultipleChoiceQuestion` model
3. `_generate_text_input_target()` - Use `TextInputQuestion` model
4. `_generate_text_input_source()` - Use `TextInputQuestion` model
5. `_generate_contextual()` - Use `ContextualQuestion` model
6. `_generate_definition()` - Use `DefinitionQuestion` model
7. `_generate_synonym()` - Use `SynonymQuestion` model

**Pattern for each method**:
```python
response = provider.create_structured_completion(
    messages=messages,
    response_model=MultipleChoiceQuestion,  # Or appropriate model
    model=DEFAULT_MODEL,
    temperature=0.7,
    max_tokens=500
)

question_obj = response["parsed_object"]

cost_usd = CostCalculationService.calculate_cost(
    provider=provider.get_provider_name(),
    model=response["model"],
    prompt_tokens=response["usage"]["prompt_tokens"],
    completion_tokens=response["usage"]["completion_tokens"],
    cached_tokens=response["usage"]["cached_tokens"]
)

return {
    'prompt': question_obj.dict(),
    'correct_answer': question_obj.correct_answer,
    'generation_cost': {
        'tokens': response["usage"],
        'cost_usd': cost_usd,
        'model': response["model"]
    }
}
```

### 4.3 Store Cost in QuizAttempt

**Update in**: `question_generation_service.py` - `generate_question()` method

After question generation, store cost data:
```python
if 'generation_cost' in question_data:
    gen_cost = question_data['generation_cost']
    quiz_attempt.question_gen_prompt_tokens = gen_cost['tokens']['prompt_tokens']
    quiz_attempt.question_gen_completion_tokens = gen_cost['tokens']['completion_tokens']
    quiz_attempt.question_gen_total_tokens = gen_cost['tokens']['total_tokens']
    quiz_attempt.question_gen_cost_usd = float(gen_cost['cost_usd'])
    quiz_attempt.question_gen_model = gen_cost['model']
```

Need to pass `session_id` to this method for session aggregation:
```python
if session_id:
    SessionCostAggregator.add_quiz_cost(session_id, gen_cost['cost_usd'])
```

---

## Phase 5: Migrate Answer Evaluation Service (2 days)

### 5.1 Create Evaluation Pydantic Model

**File**: `services/llm_models/evaluation_models.py` (created in Phase 1)

```python
class AnswerEvaluation(BaseModel):
    is_correct: bool
    explanation: str
    matched_answer: Optional[str] = None
    confidence: Optional[float] = None
```

### 5.2 Update Answer Evaluation Method

**Critical file**: `services/answer_evaluation_service.py`

**Current state**: Lines 398-456 use manual JSON parsing for LLM evaluation (Tier 3)

**Changes**:
1. Import `AnswerEvaluation` model and `CostCalculationService`
2. Update `_evaluate_with_llm()` to use structured outputs:
   ```python
   response = provider.create_structured_completion(
       messages=messages,
       response_model=AnswerEvaluation,
       model=DEFAULT_MODEL,
       temperature=0.3,
       max_tokens=200
   )

   eval_obj = response["parsed_object"]

   cost_usd = CostCalculationService.calculate_cost(...)
   ```
3. Store evaluation cost in quiz_attempt:
   ```python
   quiz_attempt.eval_prompt_tokens = response["usage"]["prompt_tokens"]
   quiz_attempt.eval_completion_tokens = response["usage"]["completion_tokens"]
   quiz_attempt.eval_total_tokens = response["usage"]["total_tokens"]
   quiz_attempt.eval_cost_usd = float(cost_usd)
   quiz_attempt.eval_model = response["model"]
   quiz_attempt.llm_evaluation_json = eval_obj.dict()
   ```
4. Aggregate to session:
   ```python
   if session_id:
       SessionCostAggregator.add_quiz_cost(session_id, cost_usd)
   ```

**Note**: Requires passing `quiz_attempt` object to `_evaluate_with_llm()` for cost storage

---

## Phase 6: Cost Reporting API (1-2 days)

### 6.1 Create Cost Query Endpoint

**New route**: `routes/analytics.py` or add to `routes/settings.py`

```python
@bp.route('/api/user/costs/monthly', methods=['GET'])
@login_required
def get_monthly_costs():
    """Get user's monthly LLM usage costs"""
    year = request.args.get('year', type=int) or datetime.utcnow().year
    month = request.args.get('month', type=int) or datetime.utcnow().month

    costs = CostCalculationService.get_monthly_cost(current_user.id, year, month)

    return jsonify({
        'year': year,
        'month': month,
        'total_cost_usd': float(costs['total_cost_usd']),
        'translation_cost_usd': float(costs['translation_cost_usd']),
        'quiz_cost_usd': float(costs['quiz_cost_usd']),
        'operations_count': costs['operations_count'],
        'session_count': costs['session_count']
    })
```

### 6.2 Update Frontend (Optional)

Add cost display to user dashboard showing:
- Current month spending
- Cost breakdown (translations vs quizzes)
- Historical trends

---

## Critical Files Summary

### Files to Create (8 new files):
1. `services/cost_service.py` - Cost calculation and monthly query logic
2. `services/session_cost_aggregator.py` - Session aggregation helper
3. `services/llm_models/__init__.py` - Package init
4. `services/llm_models/translation_models.py` - Translation Pydantic models
5. `services/llm_models/question_models.py` - Question Pydantic models
6. `services/llm_models/evaluation_models.py` - Evaluation Pydantic model
7. `migrations/versions/[timestamp]_create_llm_pricing_table.py` - Pricing table
8. `migrations/versions/[timestamp]_add_comprehensive_cost_tracking.py` - Cost columns

### Files to Update (9 existing files):
1. **`services/llm_provider_factory.py`** - Add `create_structured_completion()` method
2. **`services/llm_translation_service.py`** - Use structured outputs, calculate costs
3. **`services/phrase_translation_service.py`** - Store cost data in PhraseTranslation
4. **`services/question_generation_service.py`** - Migrate 7 question types to Pydantic
5. **`services/answer_evaluation_service.py`** - Use structured outputs for evaluation
6. **`models/phrase_translation.py`** - Add cost tracking columns
7. **`models/quiz_attempt.py`** - Add cost tracking columns
8. **`models/session.py`** - Add cost aggregation columns
9. **`routes/settings.py` or new `routes/analytics.py`** - Cost query endpoint

---

## Implementation Sequence

**Week 1**: Foundation + Database
- Days 1-2: Create pricing infrastructure, Pydantic models, cost service
- Day 3: Update LLM provider interface with structured outputs
- Day 4: Create and run database migrations
- Day 5: Create session aggregator, write unit tests

**Week 2**: Service Migration
- Days 1-2: Migrate translation service (lowest risk)
- Days 3-5: Migrate question generation service (7 types, complex)

**Week 3**: Evaluation + Reporting
- Days 1-2: Migrate answer evaluation service
- Day 3: Create cost query API endpoint
- Days 4-5: Integration testing, documentation

---

## Testing Strategy

### Unit Tests:
- Cost calculation with different pricing scenarios
- Pydantic model validation
- Provider structured output fallback
- Session aggregation logic

### Integration Tests:
- End-to-end translation flow with cost tracking
- Quiz generation with cost storage
- Monthly cost query performance
- Migration rollback

### Manual Testing:
- Test all 7 question types generate correctly
- Verify cost calculations match expected values
- Confirm monthly queries return accurate totals

---

## Risk Mitigation

### Fallback Strategy:
- Every `create_structured_completion()` call wrapped in try/except
- Falls back to `create_chat_completion()` with manual JSON parsing
- Logs warnings for monitoring structured output success rate

### Database Safety:
- All new columns nullable with defaults
- No backfill required (existing data shows NULL/0)
- Test migrations on staging database first
- Verify rollback before production deployment

### Performance:
- Pricing cache (1-hour TTL) reduces DB queries
- Session aggregation eliminates per-operation monthly queries
- Indexes on (user_id, started_at) for efficient filtering

---

## Success Criteria

✅ All LLM calls use Pydantic structured outputs with fallback
✅ Cost calculated and stored for every LLM operation
✅ Session aggregates updated in real-time
✅ Monthly cost queries return in <100ms
✅ No regression in translation/quiz functionality
✅ Backward compatibility maintained for existing data