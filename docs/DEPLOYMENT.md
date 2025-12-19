# Deployment Guide for Minin

This guide covers deploying Minin with:
- **Database**: Supabase (PostgreSQL)
- **Backend**: Google Cloud Platform (Cloud Run)
- **Frontend**: Vercel

## Overview

Your application is split across three services:
- Database: Supabase PostgreSQL
- Backend API: `https://minin-backend-51849650360.europe-west3.run.app`
- Frontend: `https://minin-weld.vercel.app`

## Required Environment Variables

### Backend (GCP Cloud Run)

Set these environment variables in your GCP Cloud Run service:

```bash
# Flask Environment
FLASK_ENV=production

# Database
DATABASE_URI=postgresql://user:password@host:port/database
# Get this from your Supabase project settings -> Database -> Connection String

# Security
SECRET_KEY=your-secure-random-secret-key-min-32-chars
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"

# CORS - Allow your frontend domain
ALLOWED_ORIGINS=https://minin-weld.vercel.app,https://your-custom-domain.com
# Separate multiple domains with commas, no spaces

# Session Configuration for Cross-Domain
SESSION_COOKIE_SAMESITE=None
# Required for cookies to work across different domains (Vercel <-> GCP)

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional: DeepL Translation API
DEEPL_API_KEY=your-deepl-api-key
```

### Frontend (Vercel)

Set these environment variables in your Vercel project settings:

```bash
# Backend API URL
VITE_API_URL=https://minin-backend-51849650360.europe-west3.run.app

# Google OAuth Client ID (for frontend Google Sign-In button)
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

## Critical Configuration for Cross-Domain Authentication

### Why Session Cookies Were Failing

When frontend and backend are on different domains, browsers block cookies by default for security. To make authentication work:

1. **Backend must set `SameSite=None` on cookies** ✅ Now configured
   - This tells browsers to allow cross-domain cookies
   - Requires `Secure=True` (HTTPS only)

2. **Backend must include frontend domain in CORS** ✅ Now configured
   - Set `ALLOWED_ORIGINS` to include your Vercel URL
   - Includes all necessary endpoints: `/api/*`, `/auth/*`, `/login/*`, etc.

3. **Frontend must send credentials** ✅ Already configured in `api.ts`
   - All API calls use `credentials: 'include'`

## Google OAuth Configuration

Your Google OAuth application needs to know about your deployed URLs:

### Authorized JavaScript Origins
Add these in [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
```
https://minin-weld.vercel.app
https://your-custom-domain.com (if using custom domain)
```

### Authorized Redirect URIs
```
https://minin-backend-51849650360.europe-west3.run.app/login/google/authorized
https://minin-backend-51849650360.europe-west3.run.app/auth/google/callback
```

## Deployment Steps

### 1. Deploy Backend to GCP Cloud Run

```bash
# From the Minin directory
cd Minin

# Build and deploy
gcloud run deploy minin-backend \
  --source . \
  --region europe-west3 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "FLASK_ENV=production,SESSION_COOKIE_SAMESITE=None" \
  --set-env-vars "ALLOWED_ORIGINS=https://minin-weld.vercel.app"
```

Or set environment variables through the GCP Console:
1. Go to Cloud Run → Select your service
2. Click "EDIT & DEPLOY NEW REVISION"
3. Go to "Variables & Secrets" tab
4. Add all required environment variables from above

### 2. Deploy Frontend to Vercel

```bash
# From the frontend directory
cd Minin/frontend

# Deploy using Vercel CLI
vercel --prod
```

Or through Vercel Dashboard:
1. Connect your GitHub repository
2. Set root directory to `Minin/frontend`
3. Add environment variables in Settings → Environment Variables
4. Deploy

### 3. Verify Deployment

Test these endpoints:

```bash
# Backend health check
curl https://minin-backend-51849650360.europe-west3.run.app/health

# Should return:
# {"status": "healthy", "database": "connected"}
```

Visit your frontend:
```
https://minin-weld.vercel.app
```

## Troubleshooting

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution:** Ensure `ALLOWED_ORIGINS` environment variable is set correctly on GCP:
```bash
ALLOWED_ORIGINS=https://minin-weld.vercel.app
```

### Issue: Getting logged out on page refresh

**Solution:** This was the main issue - cookies weren't being saved. Fixed by:
- Setting `SESSION_COOKIE_SAMESITE=None` in production config
- Setting `SESSION_COOKIE_SECURE=True` (automatic in production)
- Frontend already uses `credentials: 'include'`

### Issue: "Failed to fetch" or redirect to login

**Causes:**
1. Backend not running or wrong URL in `VITE_API_URL`
2. Database connection failed
3. Session cookie configuration incorrect

**Solution:**
- Check GCP Cloud Run logs: `gcloud run services logs read minin-backend --region europe-west3`
- Verify environment variables are set
- Check browser DevTools → Network tab for actual error

### Issue: "Mixed Content" errors

**Solution:** Ensure both frontend and backend use HTTPS:
- Vercel provides HTTPS by default
- GCP Cloud Run provides HTTPS by default
- Never use `http://` URLs in production

## Security Checklist

- [ ] `SECRET_KEY` is set to a strong random value (not the default)
- [ ] `SESSION_COOKIE_SECURE=True` in production (automatic with ProductionConfig)
- [ ] `SESSION_COOKIE_SAMESITE=None` for cross-domain
- [ ] `ALLOWED_ORIGINS` only includes your actual frontend domains
- [ ] Google OAuth credentials are configured with correct redirect URIs
- [ ] Database password is strong and kept secret
- [ ] All environment variables are set in deployment platforms (not in code)

## Monitoring

### GCP Cloud Run Logs
```bash
# View recent logs
gcloud run services logs read minin-backend --region europe-west3 --limit 50

# Follow logs in real-time
gcloud run services logs tail minin-backend --region europe-west3
```

### Vercel Logs
- View in Vercel Dashboard → Project → Deployments → Click deployment → Runtime Logs

## Cost Optimization

### GCP Cloud Run
- Uses "scale to zero" - only charged when requests are being processed
- Free tier: 2 million requests/month
- Your current setup with connection pooling is optimized for serverless

### Vercel
- Free tier: 100GB bandwidth/month
- Unlimited deployments

### Supabase
- Free tier: 500MB database, 2GB bandwidth/month
- More than enough for personal use

## Next Steps

1. **Custom Domain**: Configure custom domain in Vercel
2. **Update ALLOWED_ORIGINS**: Add custom domain to backend environment variables
3. **Update Google OAuth**: Add custom domain to authorized origins
4. **Monitoring**: Set up uptime monitoring (e.g., UptimeRobot)
5. **Backups**: Supabase provides automatic backups, but consider export strategy

## Environment Variables Quick Reference

| Variable | Required | Where | Example |
|----------|----------|-------|---------|
| `FLASK_ENV` | Yes | GCP | `production` |
| `DATABASE_URI` | Yes | GCP | `postgresql://...` |
| `SECRET_KEY` | Yes | GCP | `abc123...` (32+ chars) |
| `ALLOWED_ORIGINS` | Yes | GCP | `https://minin-weld.vercel.app` |
| `SESSION_COOKIE_SAMESITE` | Yes | GCP | `None` |
| `GOOGLE_CLIENT_ID` | Yes | Both | `...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Yes | GCP | `GOCSPX-...` |
| `VITE_API_URL` | Yes | Vercel | `https://...run.app` |
| `DEEPL_API_KEY` | Optional | GCP | DeepL API key |

