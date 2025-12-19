# Fix for Language Settings Not Persisting (Cross-Domain Authentication Issue)

## Problem Summary

New users could log in successfully, but when they set their language preferences during onboarding, the settings weren't saved. Users were redirected back to the login screen, and in the database, the `primary_language_code` and `translator_languages` fields remained NULL.

## Root Cause

The issue was caused by **session cookie configuration** in cross-domain authentication:

1. **User logs in** → Flask-Login creates a session cookie
2. **User submits language preferences** → The session cookie wasn't being sent with the request
3. **Backend rejects the request** → Returns 401 Unauthorized because `current_user.is_authenticated` is False
4. **Frontend redirects to login** → User sees login screen again

In production with cross-domain setup (Vercel frontend + GCP backend), session cookies need specific configuration to work properly.

## Changes Made

### 1. Enhanced Cookie Configuration (`config.py`)

Added Flask-Login specific cookie settings to the `ProductionConfig` class:

```python
# Flask-Login specific cookie settings
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_SECURE = True
REMEMBER_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None")
REMEMBER_COOKIE_DURATION = 2592000  # 30 days in seconds
```

**Why this fixes it:**
- `REMEMBER_COOKIE_SECURE = True`: Ensures cookies are only sent over HTTPS
- `REMEMBER_COOKIE_SAMESITE = "None"`: Allows cookies to be sent in cross-domain requests
- These settings apply to the "remember me" cookie created by `login_user(user, remember=True)`

### 2. Enhanced Logging (`auth/oauth.py`)

Added detailed logging to track authentication state and debug session issues:

**In `/auth/google` (Google sign-in):**
- Logs session data after `login_user()` is called
- Verifies `current_user.is_authenticated` immediately after login

**In `/auth/update-languages` (Language update):**
- Logs authentication status at the start of the request
- Shows session data and cookies when authentication fails
- Logs the update operation for successful requests

**Benefits:**
- Easier debugging in production
- Clear visibility into when/why authentication fails
- Helps identify cookie transmission issues

## Deployment Steps

### Step 1: Deploy Backend Changes

1. **Commit and push the changes:**
   ```bash
   cd /Users/grace_scale/PycharmProjects/Minin
   git add Minin/config.py Minin/auth/oauth.py
   git commit -m "Fix: Add REMEMBER_COOKIE settings for cross-domain auth and enhanced logging"
   git push
   ```

2. **Deploy to Google Cloud Platform:**
   ```bash
   # Your existing GCP deployment command
   gcloud app deploy
   ```

3. **Verify environment variables are set on GCP:**
   - `SESSION_COOKIE_SAMESITE=None` (must be "None" for cross-domain)
   - `SECRET_KEY` (must be set to a secure random value)
   - `FLASK_ENV=production`

### Step 2: Test the Fix

1. **Clear browser cookies** (important!)
   - Open DevTools → Application → Cookies
   - Delete all cookies for both your frontend and backend domains

2. **Test new user registration:**
   - Go to your deployed app
   - Log in with a NEW Google account (one that hasn't been used before)
   - Complete the language setup
   - Verify you're redirected to the translate page (not back to login)

3. **Verify in database:**
   ```sql
   SELECT email, primary_language_code, translator_languages 
   FROM users 
   WHERE email = 'your-test-email@gmail.com';
   ```
   
   Both fields should now be populated!

4. **Check logs for debugging:**
   ```bash
   # View GCP logs
   gcloud app logs tail -s default
   ```
   
   Look for these log messages:
   - "User {email} logged in successfully via GIS"
   - "Session after login_user: {...}"
   - "Update languages request - Authenticated: True"
   - "Successfully updated languages for user {email}"

### Step 3: Monitor Production

After deployment, monitor the logs for:

✓ **Success indicators:**
- "Successfully updated languages for user {email}"
- No 401 errors on `/auth/update-languages`

✗ **Failure indicators:**
- "Update languages called but user not authenticated"
- "Session data: {}" (empty session)
- "Request cookies: dict_keys([])" (no cookies)

If you see failure indicators, check:
1. Is `SESSION_COOKIE_SAMESITE=None` set in GCP environment?
2. Is your backend using HTTPS? (required for SameSite=None)
3. Are CORS headers properly configured? (already done in your app.py)

## Technical Details

### Why SameSite=None is Required

In cross-domain scenarios:
- Frontend: `https://your-app.vercel.app`
- Backend: `https://your-backend.run.app`

These are different domains, so cookies need `SameSite=None` to be sent in cross-origin requests.

### Cookie Security

The configuration ensures:
- ✓ Cookies only sent over HTTPS (`Secure=True`)
- ✓ Cookies not accessible from JavaScript (`HttpOnly=True`)
- ✓ Cookies work across domains (`SameSite=None`)
- ✓ Cookies persist for 30 days (`REMEMBER_COOKIE_DURATION`)

## Rollback Plan

If issues occur after deployment:

1. Check the logs first (most issues are configuration-related)
2. If needed, temporarily revert:
   ```bash
   git revert HEAD
   git push
   gcloud app deploy
   ```

## Environment Variables Checklist

Ensure these are set in your GCP production environment:

- [ ] `SESSION_COOKIE_SAMESITE=None`
- [ ] `SECRET_KEY=<your-secure-random-key>`
- [ ] `FLASK_ENV=production`
- [ ] `GOOGLE_CLIENT_ID=<your-google-client-id>`
- [ ] `GOOGLE_CLIENT_SECRET=<your-google-client-secret>`
- [ ] `DATABASE_URI=<your-database-connection-string>`
- [ ] `ALLOWED_ORIGINS=https://your-app.vercel.app`

## Testing Checklist

After deployment, verify:

- [ ] Existing users can still log in
- [ ] Existing users can update their language settings
- [ ] New users can complete language setup without being redirected to login
- [ ] Language preferences are saved in the database
- [ ] Session persists across page refreshes
- [ ] Logout works correctly

## Additional Notes

- The fix applies to **production only** (cross-domain setup)
- Local development continues to work as before (SameSite=Lax is fine for same-domain)
- No frontend changes are required
- No database migrations are required

## Questions?

If you encounter issues:
1. Check the logs with `gcloud app logs tail -s default`
2. Verify environment variables with `gcloud app describe`
3. Test with browser DevTools → Network tab to see cookie headers
