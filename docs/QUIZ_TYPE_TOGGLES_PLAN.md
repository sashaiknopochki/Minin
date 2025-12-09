# Quiz Type Toggles Implementation Plan

## Overview
Add user preferences to disable specific advanced quiz types (contextual, definition, synonym) at the Profile page. This allows users to customize their learning experience by skipping question types they find less helpful.

## Feature Scope

### Quiz Types Affected
- ✅ **Multiple Choice (Basic)** - Cannot be disabled (essential for beginners)
- ✅ **Text Input (Intermediate)** - Cannot be disabled (essential for recall)
- ⚙️ **Contextual (Advanced)** - Can be disabled
- ⚙️ **Definition (Advanced)** - Can be disabled  
- ⚙️ **Synonym (Advanced)** - Can be disabled

### Rationale
- Basic and intermediate questions teach core recognition and recall skills
- Advanced questions are specialized; users may prefer focusing on core translation skills
- Disabling all advanced types still allows progression through basic → intermediate → advanced stages
- Advanced stage will randomly select from remaining enabled types

## Database Changes

### 1. User Model Schema Update

**File:** `models/user.py`

Add three new boolean columns:

```python
# Quiz type preferences (advanced stage only)
enable_contextual_quiz = db.Column(db.Boolean, default=True)
enable_definition_quiz = db.Column(db.Boolean, default=True)
enable_synonym_quiz = db.Column(db.Boolean, default=True)
```

**Default Values:** All `True` (enabled by default, users opt-out if desired)

### 2. Database Migration

**File:** `migrations/versions/XXXX_add_quiz_type_preferences.py`

```python
"""Add quiz type preferences to users table

Revision ID: XXXX
Revises: YYYY
Create Date: 2024-XX-XX

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'XXXX'
down_revision = 'YYYY'  # Update with your current migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns with default=True
    op.add_column('users', sa.Column('enable_contextual_quiz', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('users', sa.Column('enable_definition_quiz', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('users', sa.Column('enable_synonym_quiz', sa.Boolean(), nullable=False, server_default='1'))

def downgrade():
    # Remove columns if rolling back
    op.drop_column('users', 'enable_synonym_quiz')
    op.drop_column('users', 'enable_definition_quiz')
    op.drop_column('users', 'enable_contextual_quiz')
```

## Backend Changes

### 3. QuizAttemptService Update

**File:** `services/quiz_attempt_service.py`

**Method:** `select_question_type(stage, user=None)`

Update to filter question types based on user preferences:

```python
@staticmethod
def select_question_type(stage: str, user: Optional[User] = None) -> str:
    """
    Select appropriate question type based on learning stage and user preferences.
    
    For advanced stage, respects user's quiz type preferences to skip 
    contextual, definition, or synonym questions if disabled.
    
    Args:
        stage: Learning stage (basic, intermediate, advanced)
        user: Optional User object to check quiz preferences (required for advanced stage)
    
    Returns:
        str: Selected question type
        
    Raises:
        ValueError: If no question types are available for the stage
    """
    stage = stage.strip().lower()
    
    question_types = {
        'basic': ['multiple_choice_target', 'multiple_choice_source'],
        'intermediate': ['text_input_target', 'text_input_source'],
        'advanced': ['contextual', 'definition', 'synonym'],
    }
    
    types = question_types.get(stage, [])
    if not types:
        raise ValueError(f"Invalid stage: {stage}")
    
    # For advanced stage, filter based on user preferences
    if stage == 'advanced' and user:
        available_types = []
        
        if user.enable_contextual_quiz:
            available_types.append('contextual')
        if user.enable_definition_quiz:
            available_types.append('definition')
        if user.enable_synonym_quiz:
            available_types.append('synonym')
        
        # If user disabled all advanced types, log warning and use all
        if not available_types:
            logger.warning(
                f"User {user.id} has disabled all advanced quiz types. "
                f"Falling back to all types."
            )
            available_types = types
        
        types = available_types
    
    return random.choice(types)
```

### 4. Update Service Calls

**Files to update:**
- `services/quiz_trigger_service.py` - Pass user to `select_question_type()`
- `routes/quiz.py` - Pass user to `select_question_type()` in practice mode

**Example changes:**

```python
# In quiz_trigger_service.py
question_type = QuizAttemptService.select_question_type(
    stage=progress.stage,
    user=user  # Add user parameter
)

# In routes/quiz.py - practice endpoint
question_type = QuizAttemptService.select_question_type(
    stage=progress.stage,
    user=current_user  # Add user parameter
)
```

### 5. Settings Endpoint Update

**File:** `routes/user.py`

**Endpoint:** `PATCH /api/user/settings`

Add new fields to request body validation and update logic:

```python
@user_bp.route('/settings', methods=['PATCH'])
@login_required
def update_settings():
    """Update user settings including quiz type preferences"""
    data = request.get_json()
    
    # Existing fields
    if 'primary_language_code' in data:
        current_user.primary_language_code = data['primary_language_code']
    
    if 'translator_languages' in data:
        current_user.translator_languages = data['translator_languages']
    
    if 'quiz_frequency' in data:
        current_user.quiz_frequency = data['quiz_frequency']
    
    if 'quiz_mode_enabled' in data:
        current_user.quiz_mode_enabled = data['quiz_mode_enabled']
    
    # New quiz type preference fields
    if 'enable_contextual_quiz' in data:
        current_user.enable_contextual_quiz = bool(data['enable_contextual_quiz'])
    
    if 'enable_definition_quiz' in data:
        current_user.enable_definition_quiz = bool(data['enable_definition_quiz'])
    
    if 'enable_synonym_quiz' in data:
        current_user.enable_synonym_quiz = bool(data['enable_synonym_quiz'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Settings updated successfully',
        'user': current_user.to_dict()  # Include new fields in response
    })
```

### 6. Profile Endpoint

**File:** `routes/user.py`

**Endpoint:** `GET /api/user/profile`

Ensure new fields are included in user object response:

```python
@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile including quiz preferences"""
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'primary_language_code': current_user.primary_language_code,
        'translator_languages': current_user.translator_languages,
        'quiz_frequency': current_user.quiz_frequency,
        'quiz_mode_enabled': current_user.quiz_mode_enabled,
        # Add new fields
        'enable_contextual_quiz': current_user.enable_contextual_quiz,
        'enable_definition_quiz': current_user.enable_definition_quiz,
        'enable_synonym_quiz': current_user.enable_synonym_quiz,
    })
```

## Frontend Changes

### 7. Profile Page Component

**File:** `frontend/src/pages/Profile.tsx`

Create new Profile page with toggle switches for quiz preferences:

```typescript
import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/components/ui/use-toast"
import { Loader2 } from "lucide-react"

interface UserProfile {
  id: number
  name: string
  email: string
  primary_language_code: string
  translator_languages: string[]
  quiz_frequency: number
  quiz_mode_enabled: boolean
  enable_contextual_quiz: boolean
  enable_definition_quiz: boolean
  enable_synonym_quiz: boolean
}

export default function Profile() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      const response = await fetch('/api/user/profile', {
        credentials: 'include',
      })
      if (!response.ok) throw new Error('Failed to fetch profile')
      const data = await response.json()
      setProfile(data)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load profile settings",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const updateSetting = async (field: string, value: boolean) => {
    if (!profile) return

    setSaving(true)
    try {
      const response = await fetch('/api/user/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ [field]: value }),
      })

      if (!response.ok) throw new Error('Failed to update setting')

      setProfile({ ...profile, [field]: value })
      
      toast({
        title: "Success",
        description: "Quiz preferences updated",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update setting",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground">Failed to load profile</p>
      </div>
    )
  }

  return (
    <div className="container max-w-2xl py-8">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Profile Settings</h1>
          <p className="text-muted-foreground">
            Manage your account preferences and quiz settings
          </p>
        </div>

        {/* Account Info */}
        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
            <CardDescription>Your basic account details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-sm font-medium">Name</Label>
              <p className="text-sm text-muted-foreground">{profile.name}</p>
            </div>
            <div>
              <Label className="text-sm font-medium">Email</Label>
              <p className="text-sm text-muted-foreground">{profile.email}</p>
            </div>
          </CardContent>
        </Card>

        {/* Quiz Preferences */}
        <Card>
          <CardHeader>
            <CardTitle>Quiz Preferences</CardTitle>
            <CardDescription>
              Customize which types of advanced quiz questions you want to practice
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Quiz Mode Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="quiz-mode">Quiz Mode</Label>
                <p className="text-sm text-muted-foreground">
                  Enable or disable automatic quizzes after translations
                </p>
              </div>
              <Switch
                id="quiz-mode"
                checked={profile.quiz_mode_enabled}
                onCheckedChange={(checked) => updateSetting('quiz_mode_enabled', checked)}
                disabled={saving}
              />
            </div>

            <Separator />

            {/* Advanced Quiz Types Section */}
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold">Advanced Question Types</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Choose which types of advanced questions to include in your practice. 
                  Basic and intermediate questions cannot be disabled.
                </p>
              </div>

              {/* Contextual Questions Toggle */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="contextual">Contextual Questions</Label>
                  <p className="text-sm text-muted-foreground">
                    Translate words within sentence context
                  </p>
                </div>
                <Switch
                  id="contextual"
                  checked={profile.enable_contextual_quiz}
                  onCheckedChange={(checked) => updateSetting('enable_contextual_quiz', checked)}
                  disabled={saving}
                />
              </div>

              {/* Definition Questions Toggle */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="definition">Definition Questions</Label>
                  <p className="text-sm text-muted-foreground">
                    Match words to their definitions
                  </p>
                </div>
                <Switch
                  id="definition"
                  checked={profile.enable_definition_quiz}
                  onCheckedChange={(checked) => updateSetting('enable_definition_quiz', checked)}
                  disabled={saving}
                />
              </div>

              {/* Synonym Questions Toggle */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="synonym">Synonym Questions</Label>
                  <p className="text-sm text-muted-foreground">
                    Identify synonyms and related words
                  </p>
                </div>
                <Switch
                  id="synonym"
                  checked={profile.enable_synonym_quiz}
                  onCheckedChange={(checked) => updateSetting('enable_synonym_quiz', checked)}
                  disabled={saving}
                />
              </div>
            </div>

            {/* Info Note */}
            <div className="rounded-lg bg-muted p-3">
              <p className="text-sm text-muted-foreground">
                <strong>Note:</strong> If all advanced question types are disabled, 
                the system will automatically enable them all to ensure you can still 
                progress to the advanced learning stage.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

### 8. Add Profile Route

**File:** `frontend/src/App.tsx`

Add route for Profile page:

```typescript
import Profile from "@/pages/Profile"

// Inside Routes
<Route path="/profile" element={<Profile />} />
```


## Testing Checklist

### Backend Tests

- [ ] Migration runs successfully without errors
- [ ] User model includes new fields with correct defaults
- [ ] `select_question_type()` respects user preferences for advanced stage
- [ ] `select_question_type()` falls back to all types if all disabled
- [ ] Settings endpoint accepts and saves new fields
- [ ] Profile endpoint returns new fields
- [ ] Quiz generation works with various combinations of disabled types

### Frontend Tests

- [ ] Profile page loads successfully
- [ ] Toggles display current user preferences
- [ ] Toggling switches saves settings to backend
- [ ] Toast notifications appear on success/failure
- [ ] Loading states display correctly
- [ ] Navigation to/from profile works from UserMenu
- [ ] Mobile responsive design works properly

### Integration Tests

- [ ] Disabling contextual questions removes them from quiz rotation
- [ ] Disabling definition questions removes them from quiz rotation
- [ ] Disabling synonym questions removes them from quiz rotation
- [ ] Disabling all advanced types still allows quizzes (fallback works)
- [ ] Practice mode respects quiz type preferences
- [ ] Auto-triggered quizzes respect quiz type preferences
- [ ] Settings persist across sessions

## Edge Cases & Considerations

### 1. All Types Disabled
**Scenario:** User disables all three advanced quiz types
**Solution:** Log warning and use all types as fallback
**User Experience:** Show info message on profile page explaining this behavior

### 2. Backward Compatibility
**Scenario:** Existing users without these preferences
**Solution:** Default to `True` for all types (migration sets `server_default='1'`)
**User Experience:** No change in behavior for existing users

### 3. Quiz Generation Failure
**Scenario:** LLM fails to generate disabled question type
**Solution:** Existing fallback mechanisms handle this
**User Experience:** Falls back to available question types

### 4. Stage Progression
**Scenario:** User is at advanced stage with all types disabled
**Solution:** Fallback ensures they can still complete quizzes
**User Experience:** They'll still progress but see all types temporarily

## Documentation Updates

Add to relevant docs:
- Update `README.md` with new profile page feature
- Update `endpoints.md` with new fields in settings/profile endpoints
- Add user guide section explaining quiz type customization

## API Documentation

### Updated Endpoint: `PATCH /api/user/settings`

```json
{
  "primary_language_code": "en",
  "translator_languages": ["en", "de", "ru"],
  "quiz_frequency": 5,
  "quiz_mode_enabled": true,
  "enable_contextual_quiz": true,
  "enable_definition_quiz": false,
  "enable_synonym_quiz": true
}
```

### Updated Response: `GET /api/user/profile`

```json
{
  "id": 1,
  "name": "Sasha",
  "email": "sasha@example.com",
  "primary_language_code": "en",
  "translator_languages": ["en", "de", "ru"],
  "quiz_frequency": 5,
  "quiz_mode_enabled": true,
  "enable_contextual_quiz": true,
  "enable_definition_quiz": true,
  "enable_synonym_quiz": false
}
```

## Implementation Order

1. **Database**: Add migration and update User model
2. **Backend Services**: Update `QuizAttemptService.select_question_type()`
3. **Backend Routes**: Update user settings and profile endpoints
4. **Frontend Profile Page**: Create Profile component
5. **Frontend Navigation**: Add routes and menu links
6. **Testing**: Verify all functionality works end-to-end
7. **Documentation**: Update relevant docs

## Estimated Effort

- Backend changes: ~2 hours
- Frontend Profile page: ~3 hours  
- Testing & debugging: ~2 hours
- Documentation: ~1 hour
- **Total: ~8 hours**

## Future Enhancements

Potential additions for later:
- Toggle for basic/intermediate types (with warnings)
- Slider for question type frequency weights
- Analytics showing which types user struggles with most
- Recommended types based on performance data