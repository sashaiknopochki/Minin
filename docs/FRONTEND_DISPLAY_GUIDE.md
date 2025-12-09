# Frontend Display Guide for Translation Results

## API Response Structure

When you call the translation endpoint, you get this response:

```json
{
  "success": true,
  "phrase_id": 42,
  "original_text": "geben",
  "source_language": "German",
  "source_info": ["geben", "verb, infinitive", "to give something"],
  "translations": {
    "English": [
      ["give", "verb, infinitive", "to give something to someone"],
      ["to give", "verb phrase", "transfer possession"],
      ["grant", "verb", "to grant permission"]
    ],
    "French": [
      ["donner", "verbe, infinitif", "donner quelque chose à quelqu'un"]
    ]
  },
  "cache_status": {
    "English": "cached",
    "French": "fresh"
  }
}
```

## How to Display This Data

### 1. Source Word Info (Top Section)

```javascript
const sourceInfo = response.source_info;
// sourceInfo = ["geben", "verb, infinitive", "to give something"]

// Display:
// Word: sourceInfo[0]           → "geben"
// Grammar: sourceInfo[1]        → "verb, infinitive"
// Context: sourceInfo[2]        → "to give something"
```

**HTML Example:**
```html
<div class="source-word">
  <h2>{sourceInfo[0]}</h2>
  <span class="grammar">{sourceInfo[1]}</span>
  <p class="context">{sourceInfo[2]}</p>
</div>
```

### 2. Primary Translation (Text Area)

**IMPORTANT:** Show only the FIRST translation in each language's text area.

```javascript
// For each target language
Object.entries(response.translations).forEach(([language, translations]) => {

  // TEXT AREA - FIRST TRANSLATION ONLY
  const primaryTranslation = translations[0][0];

  // Set the text area value
  document.querySelector(`#translation-${language}`).value = primaryTranslation;

  // Example:
  // English text area → "give"
  // French text area → "donner"
});
```

### 3. Translation Details (Cards Below)

**Show ALL translations with full details** in expandable cards or a list.

```javascript
Object.entries(response.translations).forEach(([language, translations]) => {

  const detailsContainer = document.querySelector(`#details-${language}`);

  // LOOP THROUGH ALL TRANSLATIONS
  translations.forEach(([word, grammar, context], index) => {

    const card = createTranslationCard({
      word: word,           // "give", "to give", "grant"
      grammar: grammar,     // "verb, infinitive"
      context: context,     // "to give something to someone"
      isPrimary: index === 0  // Mark first one as primary
    });

    detailsContainer.appendChild(card);
  });
});
```

**HTML Template Example:**
```html
<div class="translation-details">
  <h3>English Translations</h3>

  <!-- Primary translation (highlighted) -->
  <div class="translation-card primary">
    <div class="word">give</div>
    <div class="grammar">verb, infinitive</div>
    <div class="context">to give something to someone</div>
  </div>

  <!-- Alternative translations -->
  <div class="translation-card">
    <div class="word">to give</div>
    <div class="grammar">verb phrase</div>
    <div class="context">transfer possession</div>
  </div>

  <div class="translation-card">
    <div class="word">grant</div>
    <div class="grammar">verb</div>
    <div class="context">to grant permission</div>
  </div>
</div>
```

## Complete React Example

```jsx
function TranslationResult({ response }) {
  const { source_info, translations } = response;

  return (
    <div className="translation-result">

      {/* Source Word Section */}
      <div className="source-word">
        <h2>{source_info[0]}</h2>
        <span className="grammar">{source_info[1]}</span>
        <p className="context">{source_info[2]}</p>
      </div>

      {/* Translations for Each Language */}
      {Object.entries(translations).map(([language, translationList]) => (
        <div key={language} className="language-section">

          <h3>{language}</h3>

          {/* PRIMARY TRANSLATION - Text Area */}
          <input
            type="text"
            className="primary-translation"
            value={translationList[0][0]}  {/* FIRST WORD ONLY */}
            readOnly
          />

          {/* ALL TRANSLATIONS - Details Cards */}
          <div className="translation-details">
            {translationList.map(([word, grammar, context], index) => (
              <div
                key={index}
                className={`translation-card ${index === 0 ? 'primary' : ''}`}
              >
                <div className="word">{word}</div>
                <div className="grammar">{grammar}</div>
                <div className="context">{context}</div>
              </div>
            ))}
          </div>

        </div>
      ))}

    </div>
  );
}
```

## Complete Vanilla JS Example

```javascript
function displayTranslation(response) {
  const { source_info, translations } = response;

  // 1. Display Source Word
  document.querySelector('.source-word-text').textContent = source_info[0];
  document.querySelector('.source-word-grammar').textContent = source_info[1];
  document.querySelector('.source-word-context').textContent = source_info[2];

  // 2. Display Translations for Each Language
  Object.entries(translations).forEach(([language, translationList]) => {

    // PRIMARY TRANSLATION - Show in text area
    const textArea = document.querySelector(`#translation-${language.toLowerCase()}`);
    textArea.value = translationList[0][0]; // FIRST WORD ONLY

    // ALL TRANSLATIONS - Show in details
    const detailsContainer = document.querySelector(`#details-${language.toLowerCase()}`);
    detailsContainer.innerHTML = ''; // Clear previous

    translationList.forEach(([word, grammar, context], index) => {
      const card = document.createElement('div');
      card.className = `translation-card ${index === 0 ? 'primary' : ''}`;

      card.innerHTML = `
        <div class="word">${word}</div>
        <div class="grammar">${grammar}</div>
        <div class="context">${context}</div>
      `;

      detailsContainer.appendChild(card);
    });
  });
}

// Usage
fetch('/translation/translate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'geben',
    source_language: 'German',
    target_languages: ['English', 'French']
  })
})
.then(res => res.json())
.then(displayTranslation);
```

## CSS Example

```css
/* Source Word Section */
.source-word {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.source-word h2 {
  font-size: 32px;
  margin: 0;
}

.source-word .grammar {
  color: #666;
  font-style: italic;
  display: block;
  margin-top: 5px;
}

.source-word .context {
  margin-top: 10px;
  color: #333;
}

/* Primary Translation Text Area */
.primary-translation {
  width: 100%;
  padding: 12px;
  font-size: 18px;
  border: 2px solid #4CAF50;
  border-radius: 4px;
  margin-bottom: 15px;
}

/* Translation Details Cards */
.translation-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.translation-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 15px;
}

.translation-card.primary {
  border-color: #4CAF50;
  background: #f0f8f0;
  border-width: 2px;
}

.translation-card .word {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.translation-card .grammar {
  color: #666;
  font-style: italic;
  margin: 5px 0;
}

.translation-card .context {
  color: #555;
  margin-top: 8px;
}
```

## Key Points to Remember

✅ **Text Area**: `translations[language][0][0]` - First word only
✅ **Details Section**: Loop through ALL items in `translations[language]`
✅ **Source Info**: Always show `[word, grammar, context]` format
✅ **Primary Indicator**: Mark first translation as "primary" in UI
✅ **Cache Status**: Use `cache_status` to show if translation is cached (optional)

## Common Mistakes to Avoid

❌ **Wrong:** Putting all translations in text area
```javascript
// DON'T DO THIS
textArea.value = translations.English.map(t => t[0]).join(', ');
// Results in: "give, to give, grant" in text area ❌
```

✅ **Correct:** Only first translation in text area
```javascript
// DO THIS
textArea.value = translations.English[0][0];
// Results in: "give" in text area ✅
```

❌ **Wrong:** Only showing first translation in details
```javascript
// DON'T DO THIS
const card = createCard(translations.English[0]);
// Only shows "give" ❌
```

✅ **Correct:** Show all translations in details
```javascript
// DO THIS
translations.English.forEach(translation => {
  const card = createCard(translation);
  container.appendChild(card);
});
// Shows "give", "to give", "grant" ✅
```