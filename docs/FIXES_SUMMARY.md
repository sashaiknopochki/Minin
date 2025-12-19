# Cross-Domain Authentication Fixes - Summary

## Problem
Your deployed app on Vercel + GCP was failing with CORS errors and authentication issues, even though it worked perfectly locally.

## Root Causes Identified

### 1. Flask-Login Redirecting Instead of Returning JSON (CRITICAL)
- **Issue**: When unauthenticated, Flask-Login redirected to `/login/google` instead of returning a 401 JSON response
- **Why it failed**: Browsers blocked the cross-origin redirect with CORS errors
- **Impact**: Practice, History, and Profile pages showed no data

### 2. Missing CORS Configuration for `/login/*`
- **Issue**: CORS whitelist didn't include `/login/*` endpoints
- **Why it failed**: Even if redirects worked, they'd be blocked by CORS
- **Impact**: All authentication-related redirects failed

### 3. Wrong Cookie SameSite Setting
- **Issue**: `SESSION_COOKIE_SAMESITE=Lax` blocked cross-domain cookies
- **Why it failed**: Vercel and GCP are different domains, Lax mode blocks third-party cookies
- **Impact**: Session cookies weren't saved/sent, causing logout on every page refresh

### 4. Frontend Not Protecting Routes
- **Issue**: Protected pages rendered even without authentication
- **Why it failed**: No route guard to redirect to login
- **Impact**: Pages loaded but API calls failed silently

### 5. No Global 401 Error Handling
- **Issue**: Individual pages caught 401 errors but didn't redirect to login
- **Why it failed**: Each page just logged errors to console
- **Impact**: Users stuck on broken pages with no clear error message

## Solutions Implemented

### Backend Changes (Python/Flask)

#### 1. `app.py` - Added Unauthorized Handler
```python
@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON error instead of redirect for unauthorized API requests"""
    return jsonify({
        'success': False,
        'error': 'Authentication required',
        'message': 'Please log in to access this resource'
    }), 401
```
**What it does**: Returns proper 401 JSON responses instead of redirecting to login page

#### 2. `app.py` - Added CORS for `/login/*`
```python
r"/login/*": {"origins": ALLOWED_ORIGINS},
```
**What it does**: Allows frontend to make requests to login endpoints

#### 3. `config.py` - Cross-Domain Cookie Configuration
```python
# In ProductionConfig:
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None")
```
**What it does**: Enables cookies to work across different domains (Vercel ↔ GCP)

### Frontend Changes (TypeScript/React)

#### 4. `App.tsx` - Protected Routes
```typescript
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div>Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}
```
**What it does**: Redirects unauthenticated users to login before rendering protected pages

#### 5. `api.ts` - Global 401 Handler
```typescript
if (response.status === 401 && !window.location.pathname.includes('/login')) {
  console.warn('Session expired or not authenticated. Redirecting to login...');
  window.location.href = '/login';
  throw new Error('Authentication required');
}
```
**What it does**: Automatically redirects to login when session expires or user is not authenticated

## Files Changed

### Backend
- ✅ `app.py` - Added unauthorized handler + CORS for /login/*
- ✅ `config.py` - Production cookie configuration

### Frontend  
- ✅ `frontend/src/App.tsx` - Protected route wrapper
- ✅ `frontend/src/lib/api.ts` - Global 401 error handler

### Documentation
- ✅ `docs/DEPLOYMENT.md` - Complete deployment guide
- ✅ `docs/QUICK_FIX.md` - Step-by-step fix instructions
- ✅ `docs/FIXES_SUMMARY.md` - This file

## Deployment Checklist

### Before Deploying

- [ ] All code changes committed
- [ ] Pushed to GitHub

### Backend Deployment (GCP Cloud Run)

- [ ] Set environment variable: `SESSION_COOKIE_SAMESITE=None`
- [ ] Verify: `FLASK_ENV=production`
- [ ] Verify: `ALLOWED_ORIGINS=https://minin-weld.vercel.app`
- [ ] Deploy latest code

### Frontend Deployment (Vercel)

- [ ] Verify environment variable: `VITE_API_URL=https://minin-backend-51849650360.europe-west3.run.app`
- [ ] Deploy latest code (automatic via GitHub or manual via `vercel --prod`)

### Testing

- [ ] Open app in incognito mode
- [ ] Should redirect to `/login` automatically
- [ ] Log in with Google
- [ ] Should redirect to `/translate`
- [ ] Navigate to Practice - phrases load ✓
- [ ] Navigate to History - data loads ✓
- [ ] Navigate to Profile - settings work ✓
- [ ] Refresh page - stay logged in ✓
- [ ] No CORS errors in console ✓

## How to Deploy

See `docs/QUICK_FIX.md` for detailed step-by-step instructions (~15 minutes total).

## Expected Behavior After Fix

### ✅ What Should Work Now

1. **Automatic login redirect**: Accessing protected pages when not logged in → redirects to `/login`
2. **Session persistence**: Refresh the page → stay logged in
3. **Practice page**: Displays filtered phrases based on language/stage
4. **History page**: Shows translation history with pagination
5. **Profile page**: Can update quiz settings and preferences
6. **No CORS errors**: Console is clean
7. **Session expiry handling**: If session expires mid-session → auto-redirect to login

### 🔄 Authentication Flow

```
User visits https://minin-weld.vercel.app/practice
  ↓
Frontend: Check if authenticated (AuthContext)
  ↓ (not authenticated)
ProtectedRoute redirects to /login
  ↓
User logs in with Google
  ↓
Backend sets session cookie (SameSite=None, Secure=True)
  ↓
Frontend redirects to /translate
  ↓
User navigates to /practice
  ↓
Frontend makes API call with credentials: 'include'
  ↓
Backend validates session cookie
  ↓
Returns practice data
  ↓
Practice page displays phrases ✓
```

### 🔐 Security Notes

All security best practices maintained:
- ✅ HTTPS only (Secure=True)
- ✅ HttpOnly cookies (JavaScript can't access)
- ✅ CORS restricted to specific origins
- ✅ Session-based authentication
- ✅ No credentials in frontend code

## Why This Architecture Works

### Cross-Domain Cookie Requirements

When frontend and backend are on different domains, browsers treat requests as "third-party" and block cookies by default. To enable cross-domain authentication:

1. **Backend must set `SameSite=None`** - Tells browser to allow cross-domain cookies
2. **Backend must set `Secure=True`** - Required by browsers when using SameSite=None (HTTPS only)
3. **Backend must set proper CORS headers** - Allows frontend domain to make requests
4. **Frontend must use `credentials: 'include'`** - Explicitly tells fetch to send/receive cookies
5. **Backend must return JSON errors** - No redirects that browsers will block

All 5 requirements are now met! ✅

## Troubleshooting

If issues persist after deployment, see:
- `docs/QUICK_FIX.md` - Debugging checklist
- `docs/DEPLOYMENT.md` - Complete deployment guide

Check GCP logs:
```bash
gcloud run services logs read minin-backend --region europe-west3 --limit 50
```

Check browser console for specific errors.

## Technical Insights

### Why Local Development Worked

In development:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5001`
- **Same domain**: `localhost`
- **SameSite=Lax**: Works for same-site requests
- **No CORS issues**: Vite proxy handles it

### Why Production Failed

In production:
- Frontend: `https://minin-weld.vercel.app` (Vercel domain)
- Backend: `https://minin-backend...run.app` (Google domain)
- **Different domains**: `vercel.app` ≠ `run.app`
- **SameSite=Lax**: Blocks third-party cookies ❌
- **CORS required**: Different origins need explicit permission

### The Fix

Changed to:
- **SameSite=None**: Allow third-party cookies ✅
- **Secure=True**: Required for SameSite=None ✅
- **Proper CORS**: Whitelist all necessary endpoints ✅
- **JSON errors**: No redirects that browsers block ✅
- **Protected routes**: Frontend guards routes properly ✅

---

**All fixes are code-complete and ready to deploy!**

Follow `docs/QUICK_FIX.md` for deployment steps.
