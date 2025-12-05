# Language Service Refactoring

## Problem Statement

Currently, the Practice and History pages use hardcoded language name mappings in the frontend, which creates several issues:

1. **Data Duplication**: Language names are defined in multiple places:
   - Database: `Language` table with full language data
   - Backend: `language_utils.py` service with database queries
   - Frontend: Hardcoded dictionaries in `Practice.tsx` and `History.tsx`

2. **Maintenance Burden**: Adding a new language requires updates in multiple files

3. **Inconsistency Risk**: Frontend mappings can drift from database truth
   - Example: Frontend has `zh: "Chinese"` but database has `zh-CN` and `zh-TW` as separate entries

4. **Limited Scalability**: Cannot dynamically support user's languages without code changes

## Current Implementation

### Backend (Correct Implementation)

**File**: `models/language.py`
- Contains `Language` table with columns: `code` (PK), `en_name`, `native_name`, etc.
- Supports language variants like `zh-CN` (Simplified) and `zh-TW` (Traditional)

**File**: `services/language_utils.py`
- Provides functions to query language mappings from database:
  ```python
  def get_language_name(language_code: str) -> Optional[str]
  def get_all_code_mappings() -> Dict[str, str]
  ```

### Frontend (Problematic Implementation)

**File**: `frontend/src/pages/History.tsx` (lines 179-192)
```typescript
const getLanguageName = (code: string) => {
  const languageNames: { [key: string]: string } = {
    en: "English",
    de: "German",
    ru: "Russian",
    es: "Spanish",
    fr: "French",
    it: "Italian",
    pt: "Portuguese",
    ja: "Japanese",
    ko: "Korean",
    // Missing: zh-CN, zh-TW variants
  }
  return languageNames[code] || code.toUpperCase()
}
```

**File**: `frontend/src/pages/Practice.tsx` (lines 31-45)
```typescript
const getLanguageName = (code: string) => {
  const languageNames: { [key: string]: string } = {
    en: "English",
    de: "German",
    ru: "Russian",
    es: "Spanish",
    fr: "French",
    it: "Italian",
    pt: "Portuguese",
    ja: "Japanese",
    ko: "Korean",
    "zh-CN": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
  }
  return languageNames[code] || code.toUpperCase()
}
```

**Issues**:
- Duplicate code between History and Practice
- History.tsx missing Chinese variants
- Hardcoded subset of languages (what if user has Arabic, Hindi, etc.?)
- No fallback to database truth

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │  useLanguages() Hook                              │  │
│  │  - Fetches language mappings on mount            │  │
│  │  - Caches in React Context                       │  │
│  │  - Provides getLanguageName(code) helper         │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  History.tsx & Practice.tsx                       │  │
│  │  - Uses useLanguages() hook                       │  │
│  │  - No hardcoded mappings                          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ GET /api/languages
┌─────────────────────────────────────────────────────────┐
│                     Backend                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  routes/api.py (or routes/language.py)            │  │
│  │  GET /api/languages                                │  │
│  │  - Returns all language mappings                   │  │
│  │  - Optional query param: ?codes=en,de,ru           │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  services/language_utils.py                        │  │
│  │  - get_all_code_mappings() (already exists)       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Database                               │
│  Language table (code, en_name, native_name, ...)      │
└─────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Backend API Endpoint

**File to Create/Modify**: `routes/api.py` or `routes/language.py`

Create new endpoint:
```python
@bp.route('/languages', methods=['GET'])
def get_languages():
    """
    Get language code to name mappings.

    Query Parameters:
        codes (str, optional): Comma-separated language codes to filter
            Example: ?codes=en,de,ru

    Returns:
        200: Language mappings
            {
                "languages": {
                    "en": "English",
                    "de": "German",
                    "ru": "Russian",
                    "zh-CN": "Chinese (Simplified)",
                    "zh-TW": "Chinese (Traditional)",
                    ...
                }
            }
    """
    try:
        codes_param = request.args.get('codes')

        if codes_param:
            # Filter by specific codes
            codes = [c.strip() for c in codes_param.split(',')]
            languages = {
                code: get_language_name(code)
                for code in codes
                if get_language_name(code)
            }
        else:
            # Return all languages
            languages = get_all_code_mappings()

        return jsonify({'languages': languages})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Key Design Decisions**:
- **Public endpoint**: No `@login_required` (language names are public data)
- **Optional filtering**: Can request only needed languages to reduce payload
- **Reuses existing service**: Leverages `language_utils.py` functions
- **Simple response format**: Plain dictionary for easy consumption

### Phase 2: Frontend Context/Hook

**File to Create**: `frontend/src/contexts/LanguageContext.tsx`

Create React Context to cache language mappings:

```typescript
interface LanguageContextType {
  languages: Record<string, string>
  loading: boolean
  error: string | null
  getLanguageName: (code: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [languages, setLanguages] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Fetch languages on mount
    fetch('/api/languages', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setLanguages(data.languages)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch languages:', err)
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const getLanguageName = (code: string): string => {
    return languages[code] || code.toUpperCase()
  }

  return (
    <LanguageContext.Provider value={{ languages, loading, error, getLanguageName }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguages() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguages must be used within LanguageProvider')
  }
  return context
}
```

**Alternative: Simple Hook (No Context)**

If we don't need to share state across components:

```typescript
export function useLanguages() {
  const [languages, setLanguages] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/languages', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setLanguages(data.languages))
      .catch(err => console.error('Failed to fetch languages:', err))
      .finally(() => setLoading(false))
  }, [])

  const getLanguageName = (code: string) => languages[code] || code.toUpperCase()

  return { languages, loading, getLanguageName }
}
```

**Key Design Decisions**:
- **Fetch on mount**: Languages rarely change, single fetch is sufficient
- **Graceful fallback**: If fetch fails, return code.toUpperCase() as fallback
- **Caching**: React state caches results, no repeated API calls
- **Simple API**: Provides same `getLanguageName()` interface as current code

### Phase 3: Refactor History Page

**File to Modify**: `frontend/src/pages/History.tsx`

**Before** (lines 179-192):
```typescript
const getLanguageName = (code: string) => {
  const languageNames: { [key: string]: string } = {
    en: "English",
    de: "German",
    // ... hardcoded mappings
  }
  return languageNames[code] || code.toUpperCase()
}
```

**After**:
```typescript
import { useLanguages } from "@/contexts/LanguageContext"

export default function History() {
  const { getLanguageName } = useLanguages()
  // ... rest of component
}
```

**Changes**:
1. Remove `getLanguageName` helper function (lines 179-192)
2. Add `useLanguages()` hook import and usage
3. Use `getLanguageName` from hook instead of local function

**No other changes needed** - the rest of the code stays identical.

### Phase 4: Refactor Practice Page

**File to Modify**: `frontend/src/pages/Practice.tsx`

**Before** (lines 31-45):
```typescript
const getLanguageName = (code: string) => {
  const languageNames: { [key: string]: string } = {
    en: "English",
    de: "German",
    // ... hardcoded mappings
  }
  return languageNames[code] || code.toUpperCase()
}
```

**After**:
```typescript
import { useLanguages } from "@/contexts/LanguageContext"

export default function Practice() {
  const { getLanguageName } = useLanguages()
  // ... rest of component
}
```

**Changes**:
1. Remove `getLanguageName` helper function (lines 31-45)
2. Add `useLanguages()` hook import and usage
3. Use `getLanguageName` from hook instead of local function

### Phase 5: Wire Up Context Provider

**File to Modify**: `frontend/src/App.tsx`

Wrap application with `LanguageProvider`:

```typescript
import { LanguageProvider } from './contexts/LanguageContext'

function App() {
  const { user, loading } = useAuth()

  // ... existing logic

  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          {/* ... existing routes */}
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  )
}
```

**Placement Note**:
- Place `LanguageProvider` outside `BrowserRouter` to avoid re-fetching on route changes
- Place inside `AuthProvider` since language fetching doesn't require authentication

## Benefits of Refactoring

### 1. Single Source of Truth
- Language data defined once in database
- Frontend always reflects database state
- No risk of frontend/backend drift

### 2. Reduced Code Duplication
- Remove ~15 lines of duplicate code from History.tsx
- Remove ~15 lines of duplicate code from Practice.tsx
- Future components can easily use same hook

### 3. Easier Maintenance
- Adding new language: Update database only (no frontend changes)
- Renaming language: Update database only
- Language variants automatically supported (zh-CN, zh-TW, pt-BR, etc.)

### 4. Better Scalability
- Supports any number of languages without code changes
- Works for all users regardless of language preferences
- Can add language-specific features (native names, right-to-left, etc.)

### 5. Improved User Experience
- Users see correct language names from database
- Support for language variants (Simplified vs Traditional Chinese)
- Consistent language naming across entire app

## Migration Path

### Option A: Big Bang (Recommended for Small Apps)

1. Implement all phases in one PR
2. Test thoroughly
3. Deploy all changes together
4. Rollback if issues arise

**Pros**: Clean, complete solution
**Cons**: Larger PR, more testing needed

### Option B: Gradual Migration

1. **PR 1**: Add backend API endpoint + frontend hook
2. **PR 2**: Refactor History.tsx to use hook (keep fallback to hardcoded)
3. **PR 3**: Refactor Practice.tsx to use hook (keep fallback to hardcoded)
4. **PR 4**: Remove hardcoded fallbacks once confirmed working

**Pros**: Lower risk, easier to test and rollback
**Cons**: More PRs, temporary code duplication

### Recommended: Option A
- Small, straightforward change (~100 lines added, ~30 removed)
- Easy to test manually
- Low risk (graceful fallback to code.toUpperCase() on error)

## Edge Cases and Considerations

### 1. API Fetch Failure

**Scenario**: `/api/languages` endpoint returns 500 error

**Handling**:
```typescript
const getLanguageName = (code: string) => {
  if (loading) return "Loading..."
  if (error) return code.toUpperCase() // Graceful fallback
  return languages[code] || code.toUpperCase()
}
```

### 2. Unknown Language Code

**Scenario**: User has language code not in database (e.g., manual DB edit)

**Handling**:
- Backend returns `null` from `get_language_name()`
- Filter out null values in API response
- Frontend falls back to `code.toUpperCase()`
- Result: Shows "DE" instead of "German" (acceptable degradation)

### 3. Loading State

**Scenario**: Languages haven't loaded yet, but component renders

**Handling**:
```typescript
const { languages, loading, getLanguageName } = useLanguages()

if (loading) {
  return <div>Loading...</div>
}

// OR: Show language codes until loaded
{userLanguages.map((langCode) => (
  <Button key={langCode}>
    {loading ? langCode : getLanguageName(langCode)}
  </Button>
))}
```

### 4. Cache Invalidation

**Scenario**: Admin adds new language while user's app is open

**Current Solution**: User must refresh page to see new languages

**Future Enhancement**:
- Add `/api/languages/version` endpoint that returns hash of language data
- Poll periodically to detect changes
- Refetch if version changed

### 5. Offline Mode

**Scenario**: User has no internet connection

**Handling**:
- API fetch fails
- Falls back to `code.toUpperCase()`
- App continues to work (degraded UX)

**Future Enhancement**:
- Store language mappings in localStorage
- Use cached data when offline
- Update cache on successful fetch

## Testing Plan

### Backend Tests

**File**: `tests/test_language_routes.py` (to create)

```python
def test_get_all_languages():
    """Test fetching all language mappings"""
    response = client.get('/api/languages')
    assert response.status_code == 200
    data = response.json
    assert 'languages' in data
    assert 'en' in data['languages']
    assert data['languages']['en'] == 'English'

def test_get_filtered_languages():
    """Test fetching specific language codes"""
    response = client.get('/api/languages?codes=en,de,ru')
    assert response.status_code == 200
    data = response.json
    assert len(data['languages']) == 3
    assert 'en' in data['languages']
    assert 'de' in data['languages']
    assert 'ru' in data['languages']
    assert 'fr' not in data['languages']  # Not requested

def test_get_languages_with_invalid_code():
    """Test handling of invalid language codes"""
    response = client.get('/api/languages?codes=en,invalid,de')
    assert response.status_code == 200
    data = response.json
    assert 'en' in data['languages']
    assert 'de' in data['languages']
    assert 'invalid' not in data['languages']  # Filtered out
```

### Frontend Tests

**Manual Testing Checklist**:
- [ ] History page displays correct language names
- [ ] Practice page displays correct language names
- [ ] Chinese variants (zh-CN, zh-TW) display correctly
- [ ] Unknown language codes fall back to uppercase (e.g., "XX")
- [ ] Loading state displays during initial fetch
- [ ] Error state falls back gracefully
- [ ] Language filters work correctly after refactoring
- [ ] No console errors or warnings

**Automated Tests** (if using Jest/React Testing Library):
```typescript
describe('useLanguages hook', () => {
  it('fetches and provides language mappings', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useLanguages())

    expect(result.current.loading).toBe(true)

    await waitForNextUpdate()

    expect(result.current.loading).toBe(false)
    expect(result.current.getLanguageName('en')).toBe('English')
    expect(result.current.getLanguageName('de')).toBe('German')
  })

  it('falls back to uppercase for unknown codes', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useLanguages())

    await waitForNextUpdate()

    expect(result.current.getLanguageName('unknown')).toBe('UNKNOWN')
  })
})
```

## Performance Considerations

### Network Performance

**Single Request**:
- Fetches all languages once on app mount
- Typical payload: ~50 languages × ~20 chars = ~1KB (negligible)
- Gzipped: ~500 bytes

**Optimization**:
- Could add caching headers: `Cache-Control: public, max-age=86400`
- Language data rarely changes, aggressive caching is safe

### Memory Usage

**Frontend State**:
- Object with 50 key-value pairs: ~2KB in memory
- Stored in React Context (single instance)
- Negligible impact

### Database Queries

**Backend**:
- `Language.query.all()` fetches all languages
- Small table (~50 rows), cached by SQLAlchemy
- Executed once per API request
- Could add application-level caching if needed:
  ```python
  from functools import lru_cache

  @lru_cache(maxsize=1)
  def get_cached_language_mappings():
      return get_all_code_mappings()
  ```

## Alternative Approaches Considered

### Alternative 1: Fetch on Demand

**Approach**: Fetch language name for each code as needed

**API**: `GET /api/languages/{code}`

**Pros**:
- Minimal initial payload
- Only fetches needed languages

**Cons**:
- Multiple API requests (N requests for N languages)
- More complex caching logic
- Higher server load

**Verdict**: ❌ Not recommended - violates "make the common case fast"

### Alternative 2: Embed in User Object

**Approach**: Include language mappings in `/api/user` response

**Pros**:
- No additional API request
- Available immediately after login

**Cons**:
- Increases user object size unnecessarily
- Not available for non-authenticated endpoints
- Couples unrelated concerns

**Verdict**: ❌ Not recommended - poor separation of concerns

### Alternative 3: Static Import/Build-Time Generation

**Approach**: Generate TypeScript file from database at build time

**Script**: `scripts/generate-languages.ts`
```typescript
// Auto-generated from database
export const LANGUAGE_NAMES = {
  "en": "English",
  "de": "German",
  // ...
}
```

**Pros**:
- Zero runtime overhead
- TypeScript autocompletion
- No API request needed

**Cons**:
- Requires build step after database changes
- Tightly couples frontend build to database state
- Difficult to keep in sync in development

**Verdict**: ❌ Not recommended - loses dynamic nature

### Alternative 4: GraphQL (Overkill)

**Approach**: Use GraphQL with language type and resolvers

**Pros**:
- Flexible querying
- Type safety
- Can fetch only needed fields

**Cons**:
- Massive overhead for simple key-value mapping
- Requires GraphQL server setup
- Overkill for this use case

**Verdict**: ❌ Not recommended - over-engineered

## Recommended Approach

**Use the proposed REST API + React Hook approach** because:
- ✅ Simple and straightforward
- ✅ Single source of truth (database)
- ✅ Minimal performance overhead
- ✅ Easy to maintain
- ✅ Scalable to any number of languages
- ✅ Graceful error handling
- ✅ Follows existing patterns in the codebase

## Conclusion

This refactoring removes technical debt by eliminating hardcoded language mappings in favor of a database-driven approach. The changes are minimal (3 files modified, 2 files created, ~100 lines added, ~30 lines removed) and provide significant long-term benefits.

The implementation is low-risk with graceful fallbacks, and can be completed in a single PR with thorough manual testing.

## Next Steps

1. **Review this document** with the team
2. **Create implementation ticket** with acceptance criteria
3. **Implement in phases**:
   - Phase 1: Backend API endpoint
   - Phase 2: Frontend hook/context
   - Phase 3: Refactor History.tsx
   - Phase 4: Refactor Practice.tsx
   - Phase 5: Wire up context provider
4. **Test thoroughly** using checklist
5. **Deploy and monitor** for any issues
6. **Document** in API reference and frontend guide

## Related Files

### To Modify
- `routes/api.py` or `routes/language.py` (backend)
- `frontend/src/pages/History.tsx`
- `frontend/src/pages/Practice.tsx`
- `frontend/src/App.tsx`

### To Create
- `frontend/src/contexts/LanguageContext.tsx` (or hook file)

### To Reference
- `models/language.py` - Database model
- `services/language_utils.py` - Existing utilities
- `docs/PRACTICE_PAGE_IMPLEMENTATION.md` - Practice page documentation