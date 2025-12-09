# Translate Page: Dynamic Language Columns Refactoring

## Problem Statement

**Current behavior**: Translate page displays exactly 3 languages (primary + first 2 learning languages)

**Desired behavior**: Display ALL user-configured languages (2-6 columns: 1 primary + up to 5 learning languages)

**Example issue**: User adds Afrikaans as 3rd learning language in Profile → It saves successfully but doesn't appear on Translate page

## Root Cause Analysis

The Translate page (`/frontend/src/pages/Translate.tsx`) is hardcoded for exactly 3 languages:

```typescript
// 15+ individual state variables
const [lang1, setLang1] = useState("ru");
const [lang2, setLang2] = useState("en");
const [lang3, setLang3] = useState("de");
const [text1, setText1] = useState("");
const [text2, setText2] = useState("");
const [text3, setText3] = useState("");
const [translations1, setTranslations1] = useState<...>(null);
const [translations2, setTranslations2] = useState<...>(null);
const [translations3, setTranslations3] = useState<...>(null);
// ... and more
```

All handler functions use hardcoded field numbers:
```typescript
const handleTextChange = (fieldNumber: 1 | 2 | 3, value: string) => {
  if (fieldNumber === 1) {
    setText1(value);
    // ...
  } else if (fieldNumber === 2) {
    setText2(value);
    // ...
  } else {
    setText3(value);
    // ...
  }
}
```

UI rendering is hardcoded:
```tsx
<LanguageInput languageName={getLanguageName(lang1)} ... />
<LanguageInput languageName={getLanguageName(lang2)} ... />
<LanguageInput languageName={getLanguageName(lang3)} ... />
```

## Solution Architecture

### New State Structure

Replace 15+ individual states with array-based architecture:

```typescript
interface LanguageField {
  id: string;                  // Unique identifier for React keys
  languageCode: string;         // e.g., "en", "zh-CN"
  text: string;                 // User input text
  translations: [string, string, string][] | null;  // Translation data
  spellingSuggestion: string | null;  // Spelling correction if needed
}

// Single array state
const [fields, setFields] = useState<LanguageField[]>([]);

// Field tracking
const [sourceFieldId, setSourceFieldId] = useState<string | null>(null);
const [copiedFieldId, setCopiedFieldId] = useState<string | null>(null);
```

**Benefits**:
- Scales from 3 to 6 languages without code changes
- Cleaner state management (3 states vs 15+)
- More maintainable (centralized logic)

### Initialization Logic

**Current** (lines 98-123):
```typescript
// Hardcoded to set exactly 3 languages
if (user) {
  setLang1(user.primary_language_code);
  setLang2(user.translator_languages[0] || "en");
  setLang3(user.translator_languages[1] || "de");
}
```

**New**:
```typescript
useEffect(() => {
  if (languages.length === 0) return;

  if (user && user.primary_language_code && user.translator_languages) {
    // Build fields array: primary + ALL translator languages
    const allLangCodes = [
      user.primary_language_code,
      ...user.translator_languages  // Gets ALL languages, not just first 2
    ];

    const initialFields = allLangCodes.map((code, index) => ({
      id: `field-${index}`,
      languageCode: code,
      text: "",
      translations: null,
      spellingSuggestion: null
    }));

    setFields(initialFields);
  } else {
    // Guest users: 3 default languages
    const browserLangCode = getBrowserLanguage();
    const popularLanguages = ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"];
    const otherLangs = popularLanguages.filter(
      lang => lang !== browserLangCode && languages.some(l => l.code === lang)
    );

    const guestLangs = [browserLangCode, otherLangs[0] || "es", otherLangs[1] || "de"];
    const guestFields = guestLangs.map((code, index) => ({
      id: `field-${index}`,
      languageCode: code,
      text: "",
      translations: null,
      spellingSuggestion: null
    }));

    setFields(guestFields);
  }
}, [languages, user]);
```

## Implementation Plan

### Step 1: Add Interface
**File**: `/frontend/src/pages/Translate.tsx`
**Location**: After existing interfaces (after line 27)

```typescript
interface LanguageField {
  id: string;
  languageCode: string;
  text: string;
  translations: [string, string, string][] | null;
  spellingSuggestion: string | null;
}
```

### Step 2: Replace State Variables
**Lines to replace**: 35-62

```typescript
// Replace all individual states with:
const [fields, setFields] = useState<LanguageField[]>([]);
const [sourceFieldId, setSourceFieldId] = useState<string | null>(null);
const [copiedFieldId, setCopiedFieldId] = useState<string | null>(null);
```

### Step 3: Update Initialization Logic
**Lines to replace**: 98-123

Implement the useEffect shown in "Initialization Logic" section above.

### Step 4: Refactor handleTextChange
**Lines to replace**: 261-383

**Key changes**:
- Parameter: `fieldId: string` instead of `fieldNumber: 1 | 2 | 3`
- Update specific field using `.map()` and field ID matching
- Get target languages dynamically (all fields except source)
- Distribute translations to all target fields

```typescript
const handleTextChange = (fieldId: string, value: string) => {
  // Update the specific field and clear all spelling suggestions
  setFields(prev => prev.map(f =>
    f.id === fieldId
      ? { ...f, text: value, translations: null, spellingSuggestion: null }
      : { ...f, spellingSuggestion: null }
  ));

  setSourceFieldId(fieldId);

  if (debounceTimerRef.current) {
    clearTimeout(debounceTimerRef.current);
  }

  if (!value.trim()) {
    // Clear all other fields
    setFields(prev => prev.map(f => ({ ...f, text: "" })));
    return;
  }

  debounceTimerRef.current = setTimeout(async () => {
    const sourceField = fields.find(f => f.id === fieldId);
    if (!sourceField) return;

    // Get all other languages as targets (dynamic!)
    const targetLangs = fields
      .filter(f => f.id !== fieldId)
      .map(f => f.languageCode);

    const result = await translateText(value, sourceField.languageCode, targetLangs);

    if (result) {
      // Handle spelling issue
      if (result.spellingIssue) {
        setFields(prev => prev.map(f =>
          f.id === fieldId
            ? { ...f, spellingSuggestion: result.correctWord }
            : { ...f, spellingSuggestion: null }
        ));
        return;
      }

      const { translations, source_info, shouldShowQuiz, quizPhraseId } = result;

      // Distribute translations to all fields dynamically
      const otherFields = fields.filter(f => f.id !== fieldId);
      const targetLangNames = targetLangs.map(getLanguageName);

      const translatedTexts = targetLangNames.map((langName) => {
        const translation = translations[langName];
        if (!translation || !Array.isArray(translation) || translation.length === 0) return "";
        return translation[0][0];
      });

      const structuredTranslations = targetLangNames.map((langName) => {
        return translations[langName] || [];
      });

      const sourceInfoArray = source_info ? [source_info] : null;

      setFields(prev => prev.map(f => {
        if (f.id === fieldId) {
          return { ...f, translations: sourceInfoArray };
        } else {
          const index = otherFields.findIndex(of => of.id === f.id);
          return {
            ...f,
            text: translatedTexts[index] || "",
            translations: structuredTranslations[index] || null
          };
        }
      }));

      // Trigger quiz if needed
      if (user && shouldShowQuiz && quizPhraseId) {
        setTimeout(() => {
          fetchAndShowQuiz(quizPhraseId);
        }, 2500);
      }
    }
  }, 1000);
};
```

### Step 5: Refactor handleSpellingSuggestionClick
**Lines to replace**: 191-259

```typescript
const handleSpellingSuggestionClick = (fieldId: string, correctWord: string) => {
  // Clear all spelling suggestions and update text
  setFields(prev => prev.map(f =>
    f.id === fieldId
      ? { ...f, text: correctWord, spellingSuggestion: null }
      : { ...f, spellingSuggestion: null }
  ));

  setSourceFieldId(fieldId);

  // Trigger translation with the correct word
  const sourceField = fields.find(f => f.id === fieldId);
  if (!sourceField) return;

  const targetLangs = fields
    .filter(f => f.id !== fieldId)
    .map(f => f.languageCode);

  translateText(correctWord, sourceField.languageCode, targetLangs).then(result => {
    if (result && !result.spellingIssue) {
      // Same distribution logic as handleTextChange
      const { translations, source_info } = result;
      const otherFields = fields.filter(f => f.id !== fieldId);
      const targetLangNames = targetLangs.map(getLanguageName);

      const translatedTexts = targetLangNames.map((langName) => {
        const translation = translations[langName];
        if (!translation || !Array.isArray(translation) || translation.length === 0) return "";
        return translation[0][0];
      });

      const structuredTranslations = targetLangNames.map((langName) => {
        return translations[langName] || [];
      });

      const sourceInfoArray = source_info ? [source_info] : null;

      setFields(prev => prev.map(f => {
        if (f.id === fieldId) {
          return { ...f, translations: sourceInfoArray };
        } else {
          const index = otherFields.findIndex(of => of.id === f.id);
          return {
            ...f,
            text: translatedTexts[index] || "",
            translations: structuredTranslations[index] || null
          };
        }
      }));
    }
  });
};
```

### Step 6: Refactor clearField
**Lines to replace**: 386-400

```typescript
const clearField = () => {
  // Clear ALL fields
  setFields(prev => prev.map(f => ({
    ...f,
    text: "",
    translations: null,
    spellingSuggestion: null
  })));
  setSourceFieldId(null);
  setTranslationError(null);
};
```

**Note**: Current behavior clears all fields when any clear button is clicked. This is maintained.

### Step 7: Refactor copyField
**Lines to replace**: 403-418

```typescript
const copyField = async (fieldId: string) => {
  const field = fields.find(f => f.id === fieldId);
  if (!field?.text) return;

  try {
    await navigator.clipboard.writeText(field.text);
    setCopiedFieldId(fieldId);

    setTimeout(() => {
      setCopiedFieldId(null);
    }, 2000);
  } catch (err) {
    console.error("Failed to copy text:", err);
  }
};
```

### Step 8: Add handleLanguageChange (Guest Users)
**Add new function** after copyField

```typescript
const handleLanguageChange = (fieldId: string, newLanguageCode: string) => {
  setFields(prev => prev.map(f =>
    f.id === fieldId
      ? { ...f, languageCode: newLanguageCode }
      : f
  ));
};
```

### Step 9: Update Language Selectors (Guest Users)
**Lines to replace**: 604-657

```tsx
{!user && (
  <div className={cn(
    "grid gap-6 md:gap-8",
    fields.length <= 3 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" :
    fields.length === 4 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-4" :
    fields.length === 5 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" :
    "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
  )}>
    {fields.map((field) => (
      <Select
        key={field.id}
        value={field.languageCode}
        onValueChange={(value) => handleLanguageChange(field.id, value)}
        disabled={languagesLoading}
      >
        <SelectTrigger className="h-9 bg-background">
          <SelectValue placeholder={languagesLoading ? "Loading languages..." : "Select language"} />
        </SelectTrigger>
        <SelectContent>
          {languagesError ? (
            <SelectItem value="error" disabled>Error loading languages</SelectItem>
          ) : (
            languages.map((lang) => (
              <SelectItem key={lang.code} value={lang.code}>
                {lang.en_name} ({lang.original_name})
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
    ))}
  </div>
)}
```

### Step 10: Update LanguageInput Components
**Lines to replace**: 660-710

```tsx
<div className={cn(
  "grid gap-6 md:gap-8 mt-6",
  fields.length <= 3 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" :
  fields.length === 4 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-4" :
  fields.length === 5 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" :
  "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
)}>
  {fields.map((field) => (
    <LanguageInput
      key={field.id}
      languageName={getLanguageName(field.languageCode)}
      value={field.text}
      onChange={(value) => handleTextChange(field.id, value)}
      onClear={clearField}
      onCopy={() => copyField(field.id)}
      isSource={sourceFieldId === field.id}
      isTranslating={translating}
      isCopied={copiedFieldId === field.id}
      placeholder={`Enter text in ${getLanguageName(field.languageCode)}`}
      spellingSuggestion={field.spellingSuggestion}
      onSpellingSuggestionClick={(correction) =>
        handleSpellingSuggestionClick(field.id, correction)
      }
      translations={field.translations}
    />
  ))}
</div>
```

### Step 11: Verify cn Utility Import
**Check imports** at top of file

Ensure this import exists:
```typescript
import { cn } from "@/lib/utils";
```

## Responsive Grid Strategy

The grid classes adapt based on the number of columns:

| Columns | Tailwind Classes | Behavior |
|---------|-----------------|----------|
| 3 | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | Mobile: 1, Tablet: 2, Desktop: 3 |
| 4 | `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` | Mobile: 1, Tablet: 2, Desktop: 4 |
| 5 | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5` | Mobile: 1, Tablet: 2, Desktop: 3, XL: 5 |
| 6 | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6` | Mobile: 1, Tablet: 2, Desktop: 3, XL: 6 |

**Rationale**: On smaller screens, showing 5-6 columns becomes unreadable. This strategy maintains usability.

## Testing Checklist

### Functional Tests
- [ ] 3 languages (primary + 2 learning) - default case
- [ ] 4 languages (primary + 3 learning)
- [ ] 5 languages (primary + 4 learning)
- [ ] 6 languages (primary + 5 learning) - max case

### Translation Flow
- [ ] Type in any field triggers translation to ALL other fields
- [ ] Source field shows source info (definitions, examples)
- [ ] Target fields show translations
- [ ] Spelling suggestions appear correctly
- [ ] Clear button clears all fields
- [ ] Copy button copies correct field text

### Quiz Integration
- [ ] Quiz triggers after translation (unchanged behavior)
- [ ] Quiz dialog appears correctly
- [ ] Quiz functionality works as before

### Guest Users
- [ ] Guest users see 3 default languages
- [ ] Guest users can change language selectors
- [ ] Translation works for guest users

### Responsive Design
- [ ] Mobile (375px): 1 column
- [ ] Tablet (768px): 2 columns
- [ ] Desktop (1024px): 3 columns (for 3-6 langs)
- [ ] Extra large (1280px+): 4-6 columns based on count

### Edge Cases
- [ ] User adds/removes languages in Profile → Translate page updates
- [ ] User with only 1 learning language (2 total columns)
- [ ] Network error during translation
- [ ] Empty translation result
- [ ] All spelling suggestions clear properly when new text typed

## Impact Analysis

### Files Modified
- **`/frontend/src/pages/Translate.tsx`**: ~250 lines changed out of 784 (32% of file)

### Files NOT Modified
- LanguageInput component: Already reusable ✅
- Translation API: Already supports N targets ✅
- Backend models: No changes needed ✅
- Profile page: Already working ✅

### Complexity
- **Medium-High**: Extensive refactoring of core translation logic
- **Well-isolated**: Changes confined to single file
- **Low risk**: Logic transformation is straightforward (array operations)

### Performance
- **State updates**: Array `.map()` for 3-6 items is negligible overhead
- **Translation API**: Single API call regardless of target count (no performance impact)
- **Rendering**: 3-6 LanguageInput components has no noticeable impact

## Migration Steps

1. **Create backup branch** (recommended)
2. **Test baseline**: Verify current 3-language functionality
3. **Implement Steps 1-11** sequentially
4. **Test after each major step**: Initialization → Handlers → UI
5. **Full test suite**: Run through all test cases
6. **Cross-browser test**: Chrome, Firefox, Safari
7. **Mobile device test**: iOS, Android

## Summary

This refactoring transforms the Translate page from a hardcoded 3-column layout to a dynamic 3-6 column layout that respects user's language configuration.

**Key Benefits**:
- ✅ Users see ALL their configured languages
- ✅ Cleaner code (array-based state vs 15+ individual variables)
- ✅ More maintainable (centralized logic vs scattered conditionals)
- ✅ Responsive design (adapts to screen size)
- ✅ Backward compatible (guests still get 3 languages)

**Estimated Time**: 2-3 hours including testing

**Risk Level**: Medium (extensive changes, but straightforward refactoring with clear test criteria)