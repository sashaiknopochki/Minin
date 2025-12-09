# Spell-Checking Frontend Specification

## Overview
When a user searches for a misspelled word, the backend returns a spelling suggestion. The frontend should display this suggestion below the textarea with a clickable link that auto-corrects and re-submits.

## Backend Response Format

### Valid Word Response
```json
{
  "success": true,
  "spelling_issue": false,
  "original_text": "collection",
  "source_language": "English",
  "target_languages": ["German", "Russian"],
  "translations": {
    "German": [["Sammlung", "noun, feminine", "a group of things"]],
    "Russian": [["коллекция", "noun", "собрание предметов"]]
  },
  "source_info": ["collection", "noun", "a group of things collected"],
  "model": "gpt-4.1-mini",
  "usage": {...}
}
```

### Misspelled Word Response
```json
{
  "success": true,
  "spelling_issue": true,
  "sent_word": "colection",
  "correct_word": "collection",
  "source_language": "English"
}
```

## Frontend Implementation

### 1. Check for Spelling Issue
After receiving the translation response, check for `spelling_issue: true`:

```javascript
fetch('/translation/translate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    text: userInput,
    source_language: sourceLanguage,
    target_languages: targetLanguages
  })
})
.then(res => res.json())
.then(data => {
  if (data.spelling_issue) {
    // Show spelling suggestion
    showSpellingSuggestion(data.sent_word, data.correct_word);
  } else {
    // Show translations normally
    displayTranslations(data);
  }
});
```

### 2. Display Spelling Suggestion

**Location**: Directly below the search textarea

**HTML Structure**:
```html
<div class="spelling-suggestion">
  <span class="suggestion-text">Did you mean </span>
  <a href="#" class="suggestion-link" data-correction="collection">collection</a>
  <span class="suggestion-text">?</span>
</div>
```

**Visual Design**:
- Small, non-intrusive text (e.g., 14px)
- Grey color for "Did you mean" text
- Blue/underlined link for the correction
- Positioned with 8-10px margin below the textarea
- Should appear smoothly (fade-in animation optional)

**CSS Example**:
```css
.spelling-suggestion {
  margin-top: 8px;
  font-size: 14px;
  color: #666;
}

.suggestion-link {
  color: #007bff;
  text-decoration: underline;
  cursor: pointer;
  font-weight: 500;
}

.suggestion-link:hover {
  color: #0056b3;
  text-decoration: none;
}
```

### 3. Handle Click on Suggestion

When user clicks the correction link:
1. **Populate the textarea** with the correct word
2. **Automatically re-submit** the translation request
3. **Remove the spelling suggestion** message
4. **Show loading state** during re-submission

**JavaScript Example**:
```javascript
function showSpellingSuggestion(sentWord, correctWord) {
  // Hide translations area
  hideTranslations();

  // Show suggestion below textarea
  const suggestionHTML = `
    <div class="spelling-suggestion">
      <span class="suggestion-text">Did you mean </span>
      <a href="#" class="suggestion-link" data-correction="${correctWord}">${correctWord}</a>
      <span class="suggestion-text">?</span>
    </div>
  `;

  // Insert below textarea
  const textarea = document.getElementById('search-textarea');
  textarea.insertAdjacentHTML('afterend', suggestionHTML);

  // Attach click handler
  document.querySelector('.suggestion-link').addEventListener('click', (e) => {
    e.preventDefault();
    const correction = e.target.dataset.correction;

    // Populate textarea with correct word
    textarea.value = correction;

    // Remove suggestion
    document.querySelector('.spelling-suggestion').remove();

    // Re-submit translation
    submitTranslation(correction);
  });
}

function submitTranslation(text) {
  // Show loading state
  showLoadingSpinner();

  // Make translation request
  fetch('/translation/translate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      text: text,
      source_language: document.getElementById('source-lang').value,
      target_languages: getSelectedTargetLanguages()
    })
  })
  .then(res => res.json())
  .then(data => {
    hideLoadingSpinner();

    if (data.spelling_issue) {
      // Still misspelled (rare case)
      showSpellingSuggestion(data.sent_word, data.correct_word);
    } else {
      // Display translations
      displayTranslations(data);
    }
  })
  .catch(err => {
    hideLoadingSpinner();
    showError('Translation failed. Please try again.');
  });
}
```

### 4. Edge Cases to Handle

#### Case 1: User manually corrects before clicking
- If user edits the textarea before clicking the suggestion link, remove the suggestion
- Attach `input` event listener to textarea to detect changes

```javascript
textarea.addEventListener('input', () => {
  const suggestion = document.querySelector('.spelling-suggestion');
  if (suggestion) {
    suggestion.remove();
  }
});
```

#### Case 2: Second spelling mistake
- If the corrected word is still misspelled (rare), show new suggestion
- The flow repeats: show new "Did you mean X?" message

#### Case 3: No suggestion provided
- If `correct_word` is empty, show generic message:
  ```
  Word not found. Please check your spelling.
  ```

#### Case 4: Multiple target languages
- Spelling check happens once for the source word, regardless of target languages
- The correction link re-submits with the same target languages

### 5. User Flow Example

**Step 1**: User types "colection" and searches
```
┌─────────────────────────────────┐
│  colection                      │  ← Textarea
└─────────────────────────────────┘
    Did you mean collection?         ← Suggestion appears
                  ^^^^^^^
                  clickable
```

**Step 2**: User clicks "collection"
```
┌─────────────────────────────────┐
│  collection                     │  ← Auto-populated
└─────────────────────────────────┘
    [Loading spinner...]             ← Shows loading
```

**Step 3**: Translations appear
```
┌─────────────────────────────────┐
│  collection                     │
└─────────────────────────────────┘

📚 Translations:
  German: Sammlung, Kollektion
  Russian: коллекция
```

## Testing Checklist

- [ ] Spelling suggestion appears below textarea when `spelling_issue: true`
- [ ] Link is clickable and has hover effect
- [ ] Clicking link populates textarea with correct word
- [ ] Clicking link automatically re-submits translation
- [ ] Suggestion disappears after clicking
- [ ] Manual textarea edits remove the suggestion
- [ ] Works with all source languages (English, German, Russian, etc.)
- [ ] Works with multiple target languages
- [ ] Loading state shows during re-submission
- [ ] Error handling if re-submission fails
- [ ] Responsive design (works on mobile)

## API Endpoints

### POST /translation/translate
**Request**:
```json
{
  "text": "colection",
  "source_language": "English",
  "target_languages": ["German", "Russian"],
  "native_language": "English",  // optional, defaults to "English"
  "model": "gpt-4.1-mini"        // optional
}
```

**Response with spelling issue**:
```json
{
  "success": true,
  "spelling_issue": true,
  "sent_word": "colection",
  "correct_word": "collection",
  "source_language": "English"
}
```

**Response with valid word**:
```json
{
  "success": true,
  "spelling_issue": false,
  "original_text": "collection",
  "translations": {...},
  "source_info": [...],
  ...
}
```

## Notes

- The spell-checking happens on the backend in a single LLM call (efficient)
- Misspelled words are **never cached** to the database
- The frontend should handle the suggestion purely as a UX enhancement
- The corrected word goes through the full translation pipeline (with caching)
- Keep the suggestion message simple and unobtrusive
- Consider adding analytics to track how often users click suggestions