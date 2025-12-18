# PostgreSQL Migration Guide for Minin

## Table of Contents
1. [Overview](#overview)
2. [Technology vs Provider: Clearing Up Confusion](#technology-vs-provider)
3. [Why Migrate to PostgreSQL?](#why-migrate-to-postgresql)
4. [PostgreSQL Provider Options](#postgresql-provider-options)
5. [Code Changes Required](#code-changes-required)
6. [Migration Process](#migration-process)
7. [Pre-Deployment Checklist](#pre-deployment-checklist)
8. [Testing the Migration](#testing-the-migration)
9. [Rollback Plan](#rollback-plan)

---

## Overview

This guide walks you through migrating your Minin application from SQLite to PostgreSQL for production deployment. Your application is already well-structured for this migration thanks to:

- ✅ Using Flask-SQLAlchemy ORM (database-agnostic)
- ✅ Flask-Migrate for schema migrations (supports PostgreSQL)
- ✅ Configuration-based database URI (easy to switch)
- ✅ No SQLite-specific SQL queries detected

**Estimated Migration Time:** 1-2 hours (excluding data migration if needed)

---

## Technology vs Provider: Clearing Up Confusion

### What is Prisma? (And Why It's NOT Relevant Here)

**Prisma** is an ORM (Object-Relational Mapper) for **Node.js/TypeScript** applications. It's similar to SQLAlchemy but for JavaScript ecosystems. Since your application is written in **Python with Flask**, Prisma is **not applicable** to your project.

### What You're Already Using

- **SQLAlchemy**: Your ORM (Python's equivalent to Prisma)
- **Flask-SQLAlchemy**: Flask integration for SQLAlchemy
- **Alembic** (via Flask-Migrate): Database migration tool

### What You Need to Choose

You need to choose **TWO things**:

1. **PostgreSQL Database Adapter** (Technology Layer)
   - `psycopg2` or `psycopg2-binary` - The Python library that connects to PostgreSQL
   - This is the ONLY new technology you need to add

2. **PostgreSQL Hosting Provider** (Infrastructure Layer)
   - Where your PostgreSQL database will be hosted (see options below)
   - Examples: Render, Railway, Supabase, AWS RDS, Heroku Postgres

**Bottom Line:** You don't need a new ORM. You just need:
- A PostgreSQL database adapter (`psycopg2`)
- A place to host your PostgreSQL database (a provider)

---

## Why Migrate to PostgreSQL?

### SQLite Limitations for Production

| Feature | SQLite | PostgreSQL |
|---------|--------|-----------|
| **Concurrent Writes** | ❌ Single writer | ✅ Multiple concurrent writers |
| **Database Size** | ⚠️ Limited (280 TB theoretical) | ✅ Virtually unlimited |
| **Data Types** | ⚠️ Limited (5 types) | ✅ Rich type system (JSON, arrays, etc.) |
| **Full-Text Search** | ⚠️ Basic FTS | ✅ Advanced full-text search |
| **Network Access** | ❌ File-based only | ✅ Remote connections |
| **Backup/Replication** | ⚠️ Manual file copies | ✅ Built-in replication |
| **Connection Pooling** | ❌ Not applicable | ✅ Supported |

### Why PostgreSQL for Minin?

Your application has features that benefit from PostgreSQL:

1. **JSON Columns**: You use `db.JSON` extensively (user preferences, translation cache)
   - PostgreSQL has native JSON support with indexing and querying

2. **Multi-User Application**: OAuth authentication means multiple concurrent users
   - PostgreSQL handles concurrent reads/writes efficiently

3. **Cost Tracking**: Your `LLMPricing` and `PhraseTranslation` models use `db.Numeric`
   - PostgreSQL has precise decimal arithmetic

4. **Future Scalability**: As your user base grows, PostgreSQL scales better

---

## PostgreSQL Provider Options

### Recommended Providers for Minin

#### 1. **Render** (Recommended for Beginners)
- **Pros:**
  - Free tier available (for development)
  - Automatic backups
  - Easy deployment with Flask
  - Good documentation
- **Cons:**
  - Free tier suspends after 90 days of inactivity
- **Pricing:** Free tier, Paid plans from $7/month
- **Setup:** 5 minutes via web dashboard

#### 2. **Railway** (Recommended for Simplicity)
- **Pros:**
  - $5 credit free each month
  - Extremely simple setup
  - Great developer experience
  - Integrated deployment with Git
- **Cons:**
  - No permanent free tier
- **Pricing:** Pay-as-you-go ($5 free/month)
- **Setup:** 2 minutes via CLI or dashboard

#### 3. **Supabase** (Recommended for PostgreSQL Features)
- **Pros:**
  - Generous free tier (500MB database)
  - Real-time capabilities (if you want to add real-time features)
  - Built-in authentication (though you use Google OAuth)
  - REST API auto-generated from your database
- **Cons:**
  - More features than you might need
- **Pricing:** Free tier, Paid plans from $25/month
- **Setup:** 5 minutes via dashboard

#### 4. **Heroku Postgres** (Classic Choice)
- **Pros:**
  - Reliable and mature
  - Easy integration with Heroku apps
  - Good monitoring tools
- **Cons:**
  - No free tier anymore (was removed in 2022)
  - Can be expensive for small projects
- **Pricing:** From $5/month (Mini plan)
- **Setup:** Instant with Heroku CLI

#### 5. **AWS RDS** (Enterprise Option)
- **Pros:**
  - Highly scalable and reliable
  - Full control over configuration
  - AWS ecosystem integration
- **Cons:**
  - More complex setup
  - Can be expensive
  - Overkill for small projects
- **Pricing:** Free tier 1 year, then ~$15-20/month
- **Setup:** 15-20 minutes via AWS Console

#### 6. **Neon** (Modern Serverless Option)
- **Pros:**
  - Serverless PostgreSQL (auto-scaling)
  - Generous free tier (0.5GB storage)
  - Instant branching (great for testing)
- **Cons:**
  - Relatively new (launched 2022)
- **Pricing:** Free tier, Paid plans from $19/month
- **Setup:** 3 minutes via dashboard

### Quick Comparison Table

| Provider | Free Tier | Best For | Complexity |
|----------|-----------|----------|------------|
| **Render** | 90 days | Beginners, Simple apps | Low |
| **Railway** | $5/month credit | Developers who value DX | Very Low |
| **Supabase** | 500MB forever | Apps needing real-time features | Medium |
| **Heroku** | None | Apps already on Heroku | Low |
| **AWS RDS** | 1 year | Enterprise apps | High |
| **Neon** | 0.5GB forever | Serverless apps | Low |

**My Recommendation for Minin:** Start with **Railway** or **Render** for ease of use, or **Supabase** if you want a generous free tier with room to grow.

---

## Code Changes Required

### 1. Install PostgreSQL Adapter

Add to your `requirements.txt`:

```txt
# Add this line
psycopg2-binary==2.9.9
```

**Why `psycopg2-binary`?**
- `psycopg2` requires compilation from source (needs PostgreSQL dev tools)
- `psycopg2-binary` is pre-compiled (easier installation, perfect for development/small apps)
- For production with high performance needs, consider `psycopg2` (compiled from source)

**Install the new dependency:**
```bash
pip install psycopg2-binary==2.9.9
pip freeze > requirements.txt
```

### 2. Update Configuration (config.py)

Your current `config.py` is already set up perfectly! No changes needed to the code itself.

**Current code (config.py:14):**
```python
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///database.db')
```

This line already reads from an environment variable, so you just need to **set the `DATABASE_URI` environment variable** in your `.env` file.

### 3. Update Environment Variables (.env)

Add your PostgreSQL connection string to `.env`:

```bash
# PostgreSQL Configuration
DATABASE_URI=postgresql://username:password@host:port/database_name

# Example for Railway:
# DATABASE_URI=postgresql://postgres:password@containers-us-west-123.railway.app:5432/railway

# Example for Render:
# DATABASE_URI=postgresql://minin_user:abc123@dpg-xxxxx.oregon-postgres.render.com/minin_db

# Example for Supabase:
# DATABASE_URI=postgresql://postgres.xxxxx:password@aws-0-us-west-1.pooler.supabase.com:5432/postgres

# Example for local PostgreSQL:
# DATABASE_URI=postgresql://localhost:5432/minin
```

**Connection String Format:**
```
postgresql://[username]:[password]@[host]:[port]/[database_name]
```

- `username`: PostgreSQL user (often `postgres`)
- `password`: Database password
- `host`: Database server address
- `port`: Usually `5432` (PostgreSQL default)
- `database_name`: Your database name

### 4. Code Compatibility Check

Your models are already PostgreSQL-compatible! Here's what I verified:

#### ✅ JSON Columns
```python
# user.py:24
translator_languages = db.Column(db.JSON)

# phrase_translation.py:17
translations_json = db.Column(db.JSON, nullable=False)
```
PostgreSQL has **native JSON support** with better performance than SQLite.

#### ✅ Numeric Precision
```python
# phrase_translation.py:40
estimated_cost_usd = db.Column(db.Numeric(precision=10, scale=6), default=0.0)
```
PostgreSQL handles `NUMERIC` types with exact precision (perfect for money).

#### ✅ DateTime Handling
```python
# user.py:37
created_at = db.Column(db.DateTime, default=datetime.utcnow)
last_active_at = db.Column(db.DateTime)

# phrase_translation.py:29
updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

**⚠️ Minor Note:** `datetime.utcnow()` is deprecated in Python 3.12+. Consider updating to `datetime.now(timezone.utc)` in the future, but this works fine for now in both SQLite and PostgreSQL.

#### ✅ String Lengths
```python
# user.py:21
primary_language_code = db.Column(db.String(10), ...)

# phrase_translation.py:14
target_language_code = db.Column(db.String(2), ...)
```
String length constraints work identically in PostgreSQL.

#### ✅ Unique Constraints
```python
# phrase_translation.py:48-50
__table_args__ = (
    db.UniqueConstraint('phrase_id', 'target_language_code', name='uq_phrase_target_language'),
)
```
Multi-column unique constraints are fully supported.

### 5. No Model Changes Needed

**Good news:** You don't need to change any model files! SQLAlchemy abstracts away database differences, and your models use only standard SQLAlchemy types that work across all databases.

---

## Migration Process

### Step 1: Set Up PostgreSQL Database

**Option A: Using Railway (Recommended for Speed)**

1. Create account at [railway.app](https://railway.app)
2. Create new project → "Provision PostgreSQL"
3. Click on PostgreSQL service → "Variables" tab
4. Copy the `DATABASE_URL` value
5. Rename `DATABASE_URL` to `DATABASE_URI` in your `.env` file

**Option B: Using Render**

1. Create account at [render.com](https://render.com)
2. Dashboard → "New +" → "PostgreSQL"
3. Choose free tier, set database name to `minin`
4. Once created, copy "External Database URL"
5. Add to `.env` as `DATABASE_URI`

**Option C: Using Supabase**

1. Create account at [supabase.com](https://supabase.com)
2. Create new project, set password
3. Go to Project Settings → Database
4. Copy "Connection string" (URI format)
5. Replace `[YOUR-PASSWORD]` with your password
6. Add to `.env` as `DATABASE_URI`

**Option D: Local PostgreSQL (For Testing)**

```bash
# Install PostgreSQL (macOS with Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb minin

# Connection string for .env
DATABASE_URI=postgresql://localhost:5432/minin
```

### Step 2: Export Existing Data (If You Have Important Data)

If your SQLite database has data you want to keep:

```bash
# Create a backup script
python -c "
from app import create_app, db
from models.user import User
from models.phrase import Phrase
from models.phrase_translation import PhraseTranslation
import json

app = create_app('development')
with app.app_context():
    # Export users
    users = User.query.all()
    users_data = [{
        'google_id': u.google_id,
        'email': u.email,
        'name': u.name,
        'primary_language_code': u.primary_language_code,
        'translator_languages': u.translator_languages,
    } for u in users]

    with open('data_export_users.json', 'w') as f:
        json.dump(users_data, f, indent=2)

    print(f'Exported {len(users)} users')
"
```

**Alternative:** If your data is small, you can manually re-populate after migration.

### Step 3: Update Environment and Install Dependencies

```bash
# Activate your virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install PostgreSQL adapter
pip install psycopg2-binary==2.9.9

# Update requirements.txt
pip freeze > requirements.txt
```

### Step 4: Run Migrations on PostgreSQL

```bash
# Set the DATABASE_URI in your .env file first!
# Make sure it points to your PostgreSQL database

# Create all tables in PostgreSQL
flask db upgrade

# This will run all your existing migrations on the new database
```

**What happens:**
- Flask-Migrate reads your migration files in `migrations/versions/`
- Applies them in order to create the schema in PostgreSQL
- Your database structure will be identical to your SQLite database

### Step 5: Verify Migration

```bash
# Check if tables were created
python -c "
from app import create_app, db
app = create_app('development')
with app.app_context():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print('Tables created:')
    for table in tables:
        print(f'  - {table}')
"
```

You should see:
- `users`
- `languages`
- `phrases`
- `phrase_translations`
- `sessions`
- `user_searches`
- `user_learning_progress`
- `quiz_attempts`
- `llm_pricing`
- `alembic_version` (migration tracking)

### Step 6: Import Data (If Applicable)

If you exported data in Step 2:

```bash
python -c "
from app import create_app, db
from models.user import User
import json

app = create_app('development')
with app.app_context():
    with open('data_export_users.json', 'r') as f:
        users_data = json.load(f)

    for user_data in users_data:
        user = User(**user_data)
        db.session.add(user)

    db.session.commit()
    print(f'Imported {len(users_data)} users')
"
```

### Step 7: Test the Application

```bash
# Run the app
python app.py

# Open http://localhost:5001
# Test key features:
# - User login (Google OAuth)
# - Search translation
# - Quiz functionality
# - Settings page
```

---

## Pre-Deployment Checklist

Before deploying your application to production, make these critical changes:

### 1. ⚠️ CRITICAL: Change SECRET_KEY

Your current `.env` has the default secret key, which is **INSECURE** for production.

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env (or production environment variables)
SECRET_KEY=your_generated_secure_key_here
```

**Why this matters:**
- `SECRET_KEY` encrypts session cookies
- Default key means anyone can forge session cookies (security breach!)
- Must be unique and never committed to Git

### 2. Update CORS Configuration (app.py:102-110)

Your current CORS allows only `http://localhost:5173` (React dev server). Update for production:

```python
# In app.py, update CORS configuration
CORS(app, resources={
    r"/api/*": {"origins": [
        "http://localhost:5173",  # Keep for local development
        "https://your-production-domain.com"  # Add production domain
    ]},
    r"/auth/*": {"origins": [
        "http://localhost:5173",
        "https://your-production-domain.com"
    ]},
    # ... repeat for all routes
}, supports_credentials=True)
```

**Or use environment variable:**

```python
# Better approach - make it configurable
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')

CORS(app, resources={
    r"/api/*": {"origins": ALLOWED_ORIGINS},
    # ...
}, supports_credentials=True)
```

Then in `.env`:
```bash
ALLOWED_ORIGINS=http://localhost:5173,https://your-production-domain.com
```

### 3. Environment Variables to Set in Production

Create a `.env.production` or set these in your hosting platform:

```bash
# Flask Configuration
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your_generated_secure_key_here

# Database
DATABASE_URI=postgresql://user:password@host:port/database

# OAuth (you'll need production credentials)
GOOGLE_CLIENT_ID=your_production_google_client_id
GOOGLE_CLIENT_SECRET=your_production_google_client_secret

# LLM APIs (use production keys with billing limits)
OPENAI_API_KEY=sk-prod-xxxxx
MISTRAL_API_KEY=prod-xxxxx
LLM_PROVIDER=mistral

# CORS
ALLOWED_ORIGINS=https://your-production-domain.com

# Optional: Database connection pool settings
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_MAX_OVERFLOW=20
```

### 4. Update Google OAuth Redirect URIs

Your Google OAuth credentials need production redirect URIs:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. APIs & Services → Credentials
4. Edit OAuth 2.0 Client ID
5. Add Authorized redirect URIs:
   - `https://your-production-domain.com/login/google/authorized`
6. Save changes

### 5. Database Connection Pooling (Optional but Recommended)

For production, configure connection pooling in `config.py`:

```python
class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    # Add these lines for connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,        # Number of connections to keep open
        'pool_recycle': 3600,   # Recycle connections after 1 hour
        'pool_pre_ping': True,  # Verify connections before using
        'max_overflow': 20      # Max connections beyond pool_size
    }
```

**Why this matters:**
- PostgreSQL connections are expensive to create
- Pooling reuses connections for better performance
- `pool_pre_ping` prevents "connection already closed" errors

### 6. Logging Configuration

Your app already has good logging (app.py:11-88), but verify logs are accessible in production:

```python
# Check your hosting platform's log location
# Most platforms capture stdout/stderr automatically

# If you need to customize log location for production:
class ProductionConfig(Config):
    # In config.py, you might want to add:
    LOG_FILE = os.getenv('LOG_FILE', '/var/log/minin/app.log')
```

### 7. Static Files and Frontend

If you're serving your React frontend separately (recommended):
- Deploy React app to Vercel/Netlify/Cloudflare Pages
- Deploy Flask backend to Render/Railway/Heroku
- Update CORS to allow frontend domain

If you're serving React from Flask (all-in-one):
- Build React app: `cd frontend && npm run build`
- Configure Flask to serve static files (requires additional setup)

### 8. Security Headers (Recommended)

Add security headers to your Flask app:

```bash
# Add to requirements.txt
flask-talisman==1.1.0
```

```python
# In app.py, add after imports:
from flask_talisman import Talisman

# In create_app(), add after CORS:
if not app.debug:
    Talisman(app,
        force_https=True,
        strict_transport_security=True,
        content_security_policy=None  # Configure based on your needs
    )
```

### 9. Database Backups

Configure automated backups:

- **Render**: Automatic daily backups on paid plans
- **Railway**: Manual backups via dashboard
- **Supabase**: Automatic backups (retention depends on plan)
- **Heroku**: Automatic backups with Heroku Postgres
- **AWS RDS**: Configure automated snapshots

**Manual backup script** (run regularly):

```bash
# Create a backup script: scripts/backup_postgres.sh
#!/bin/bash
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Get DATABASE_URI from .env
export $(grep DATABASE_URI .env | xargs)

# Use pg_dump to create backup
pg_dump "$DATABASE_URI" > "$BACKUP_DIR/minin_backup_$TIMESTAMP.sql"

echo "Backup created: $BACKUP_DIR/minin_backup_$TIMESTAMP.sql"
```

### 10. Environment-Specific Configuration

Make sure you're using the right config:

```python
# In app.py (line 93), you already have:
config_name = os.getenv('FLASK_ENV', 'development')

# Ensure FLASK_ENV=production is set in production
```

### 11. Rate Limiting (Recommended for LLM APIs)

Since you're calling OpenAI/Mistral APIs, add rate limiting:

```bash
# Add to requirements.txt
flask-limiter==3.5.0
```

```python
# In app.py:
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# In create_app():
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production for multiple workers
)

# Then in your translation routes, add:
# @limiter.limit("10 per minute")
```

### 12. Health Check Endpoint

Add a health check for monitoring:

```python
# In app.py, add before returning app:
@app.route('/health')
def health_check():
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

---

## Testing the Migration

### Local Testing Checklist

Before deploying to production, test locally with PostgreSQL:

- [ ] Application starts without errors
- [ ] All database tables created correctly
- [ ] User registration/login works (Google OAuth)
- [ ] Translation search works
- [ ] Translation caching works (try same phrase twice)
- [ ] Quiz generation works
- [ ] Learning progress tracking works
- [ ] User settings save correctly
- [ ] JSON columns serialize/deserialize correctly
- [ ] No errors in logs

### Test Database Queries

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest tests/test_models.py
python -m pytest tests/test_translation.py
```

### Manual Testing Scenarios

1. **Test Multi-Language Translation Caching:**
   - Search "hello" (English → German) → should call LLM
   - Search "hello" (English → German) again → should use cache (no LLM call)
   - Search "hello" (English → French) → should call LLM for French
   - Check `phrase_translations` table has 2 rows (one for DE, one for FR)

2. **Test Concurrent Users:**
   - Open app in two different browsers
   - Log in as different users
   - Perform searches simultaneously
   - Verify no conflicts or errors

3. **Test Data Persistence:**
   - Create user, search phrases, take quiz
   - Restart application
   - Verify all data persists

---

## Rollback Plan

If something goes wrong, you can quickly rollback to SQLite:

### Quick Rollback (Emergency)

```bash
# In .env, change back to SQLite:
DATABASE_URI=sqlite:///database.db

# Restart application
python app.py
```

Your SQLite database files are still intact (not deleted during migration).

### Proper Rollback (If You Deleted SQLite Database)

```bash
# Stop the application
# Restore SQLite database from backup
cp backups/database_backup.db database.db

# Update .env
DATABASE_URI=sqlite:///database.db

# Restart application
python app.py
```

---

## Summary: What Changes Are Needed?

### Minimal Changes for Basic Migration

1. **Add one line to `requirements.txt`:**
   ```
   psycopg2-binary==2.9.9
   ```

2. **Set one environment variable in `.env`:**
   ```
   DATABASE_URI=postgresql://user:password@host:port/database
   ```

3. **Run migrations:**
   ```bash
   flask db upgrade
   ```

### Additional Changes for Production Deployment

4. **Update `SECRET_KEY` in `.env`** (security critical!)
5. **Update CORS configuration** in `app.py` (add production domain)
6. **Update Google OAuth redirect URIs** (add production URL)
7. **Set `FLASK_ENV=production`** in production environment
8. **Configure database connection pooling** in `config.py` (optional but recommended)
9. **Set up automated backups** (via your PostgreSQL provider)
10. **Add rate limiting** for LLM API calls (optional but recommended)

---

## FAQ

### Q: Do I need to rewrite my models?
**A:** No! SQLAlchemy abstracts database differences. Your models work as-is.

### Q: Will my migrations work with PostgreSQL?
**A:** Yes! Alembic (via Flask-Migrate) generates database-agnostic migrations.

### Q: Should I use `psycopg2` or `psycopg2-binary`?
**A:** Use `psycopg2-binary` for simplicity. For production with high traffic, consider compiled `psycopg2`.

### Q: Can I run PostgreSQL locally for development?
**A:** Yes! Install PostgreSQL locally and use `postgresql://localhost:5432/minin`.

### Q: What if I want to switch between SQLite (dev) and PostgreSQL (prod)?
**A:** Use different `.env` files:
```bash
# .env.development
DATABASE_URI=sqlite:///database.db

# .env.production
DATABASE_URI=postgresql://...
```

Then load the appropriate file based on environment.

### Q: Do I need to change my queries?
**A:** No! SQLAlchemy ORM queries work identically across databases.

### Q: Is Prisma better than SQLAlchemy?
**A:** They're for different languages! Prisma is for Node.js/TypeScript, SQLAlchemy is for Python. Both are excellent ORMs for their respective ecosystems.

### Q: Can I use both SQLite and PostgreSQL?
**A:** Yes! Common pattern:
- SQLite for local development and testing
- PostgreSQL for staging and production

Just use different `DATABASE_URI` values.

---

## Additional Resources

- [PostgreSQL Official Docs](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [Flask-SQLAlchemy Configuration](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/config/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Railway PostgreSQL Docs](https://docs.railway.app/databases/postgresql)
- [Render PostgreSQL Docs](https://render.com/docs/databases)
- [Supabase Database Docs](https://supabase.com/docs/guides/database)

---

## Need Help?

If you encounter issues during migration:

1. **Check logs:** `logs/minin.log` has detailed error messages
2. **Test connection:** Use `psql` to connect directly to your PostgreSQL database
3. **Verify environment variables:** Print `DATABASE_URI` to ensure it's correct
4. **Check PostgreSQL provider status:** Some providers have status pages for outages

---

**Last Updated:** December 2024
**For:** Minin Application v1.0.0
**Author:** Generated Migration Guide