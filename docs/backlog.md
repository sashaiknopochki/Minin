# Security Backlog

Authentication security review findings - 2025-11-18

---

## Critical Vulnerabilities

### CRITICAL-1: Hardcoded Default SECRET_KEY
**File:** `config.py:9`

**Issue:** Default SECRET_KEY is used if environment variable is not set. The `.env` file is currently empty.

```python
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
```

**Impact:** Session forgery, user impersonation, complete authentication bypass

**Fix:**
```python
SECRET_KEY = os.getenv('SECRET_KEY')

@staticmethod
def validate_config():
    if not Config.SECRET_KEY:
        raise ValueError(
            "FATAL: SECRET_KEY must be set. "
            "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
```

---

### CRITICAL-2: Debug Mode Hardcoded as True
**File:** `app.py:68`

**Issue:** Debug mode is always enabled regardless of environment.

```python
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
```

**Impact:** Remote code execution through Flask debugger, source code disclosure

**Fix:**
```python
if __name__ == '__main__':
    app = create_app()
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(debug=debug_mode)
```

---

### CRITICAL-3: No CSRF Protection
**File:** Multiple (Flask-WTF not installed)

**Issue:** No CSRF protection configured. Flask-WTF is not in requirements.txt.

**Impact:** Cross-site request forgery attacks on all POST/PUT/DELETE endpoints

**Fix:**
1. Add to `requirements.txt`:
   ```
   Flask-WTF>=1.2.1
   ```

2. Add to `config.py`:
   ```python
   WTF_CSRF_ENABLED = True
   WTF_CSRF_TIME_LIMIT = None
   ```

3. Initialize in `app.py`:
   ```python
   from flask_wtf.csrf import CSRFProtect
   csrf = CSRFProtect()
   csrf.init_app(app)
   ```

---

### CRITICAL-4: Missing Secure Session Cookie Configuration
**File:** `config.py`

**Issue:** Session cookies lack security flags, making them vulnerable to interception and theft.

**Impact:**
- XSS can steal cookies (no HttpOnly)
- MITM can intercept cookies (no Secure)
- CSRF attacks possible (no SameSite)

**Fix:** Add to `config.py`:
```python
class Config:
    # Session security
    SESSION_COOKIE_SECURE = True       # Only send over HTTPS
    SESSION_COOKIE_HTTPONLY = True     # Block JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF protection
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour timeout

class DevelopmentConfig(Config):
    SESSION_COOKIE_SECURE = False      # Allow HTTP in dev
```

---

## Medium Severity Issues

### MEDIUM-1: Information Disclosure in Error Messages
**File:** `auth/oauth.py:46,57,69,83`

**Issue:** Error logs include sensitive data (google_id, full exception traces).

```python
logger.error(f'Failed to create/retrieve user for google_id: {google_id}')
logger.exception(f'Exception during Google OAuth callback: {str(e)}')
```

**Impact:** Information disclosure about users and application internals

**Fix:** Use generic error messages for users, detailed logs only in debug mode:
```python
if app.debug:
    logger.exception(f'OAuth error: {str(e)}')
else:
    logger.error('Authentication error occurred')
flash('Authentication failed. Please try again.', 'error')
```

---

### MEDIUM-2: No @login_required on Routes
**File:** `routes/*.py`

**Issue:** Route handlers don't require authentication. All endpoints are publicly accessible.

```python
@bp.route('/test')
def test():
    return jsonify({'message': 'Translation blueprint working'})
```

**Impact:** Unauthenticated access to user data and functionality

**Fix:**
```python
from flask_login import login_required, current_user

@bp.route('/translations/<int:id>')
@login_required
def get_translation(id):
    search = UserSearch.query.get_or_404(id)
    if search.user_id != current_user.id:
        abort(403)
    return jsonify(search.to_dict())
```

---

### MEDIUM-3: No Input Validation on OAuth Data
**File:** `auth/oauth.py:52-54`

**Issue:** OAuth response data stored without validation.

```python
google_id = google_info.get('id')
email = google_info.get('email')
name = google_info.get('name', '')
```

**Impact:** Invalid data in database, potential injection if rendered unsafely

**Fix:**
```python
from email_validator import validate_email, EmailNotValidError

google_id = google_info.get('id', '').strip()
email = google_info.get('email', '').strip()
name = google_info.get('name', '').strip()

# Validate
if not google_id or len(google_id) > 21:
    raise ValueError('Invalid google_id')
try:
    email = validate_email(email)['email']
except EmailNotValidError:
    raise ValueError('Invalid email')
if len(name) > 255:
    name = name[:255]
```

Add to `requirements.txt`:
```
email-validator>=2.0.0
```

---

### MEDIUM-4: Weak google_id Column Definition
**File:** `models/user.py:13`

**Issue:** No length constraint on google_id column.

```python
google_id = db.Column(db.String, unique=True, nullable=False)
```

**Impact:** Database integrity issues, potential abuse

**Fix:**
```python
google_id = db.Column(db.String(21), unique=True, nullable=False, index=True)
```

---

### MEDIUM-5: Incomplete Logout Session Cleanup
**File:** `auth/oauth.py:94-98`

**Issue:** Only clears OAuth token, not full session.

```python
logout_user()
if 'google_oauth_token' in session:
    del session['google_oauth_token']
```

**Impact:** Residual sensitive data remains in session after logout

**Fix:**
```python
logout_user()
session.clear()  # Clear ALL session data
```

---

## Low Severity Issues

### LOW-1: No Rate Limiting on Auth Endpoints
**File:** `auth/oauth.py`

**Issue:** Authentication endpoints can be called unlimited times.

**Impact:** Brute force attacks, automated abuse

**Fix:**
1. Add to `requirements.txt`:
   ```
   Flask-Limiter>=3.5.0
   ```

2. Implement:
   ```python
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)

   @bp.route('/google')
   @limiter.limit("5 per minute")
   def google_login():
       # ...
   ```

---

### LOW-2: No HTTPS Enforcement
**File:** `config.py`

**Issue:** No configuration to enforce HTTPS in production.

**Impact:** Traffic can be intercepted over HTTP

**Fix:**
```python
class ProductionConfig(Config):
    PREFERRED_URL_SCHEME = 'https'

# In app.py, add after_request handler:
@app.after_request
def set_security_headers(response):
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

---

### LOW-3: Missing Security Logging Configuration
**File:** `auth/oauth.py`

**Issue:** No persistent log storage or rotation for security events.

**Impact:** Authentication events lost on process restart

**Fix:**
```python
import logging
from logging.handlers import RotatingFileHandler

def setup_security_logging(app):
    if not app.debug:
        handler = RotatingFileHandler(
            'logs/auth.log',
            maxBytes=10240,
            backupCount=10
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        app.logger.addHandler(handler)
```

---

## Positive Findings

- SQLAlchemy ORM usage prevents SQL injection
- No password storage (OAuth-only design is appropriate)
- Current dependency versions
- Proper use of Flask-Login UserMixin

---

## Priority Order

### Immediate (before any deployment)
1. Set SECRET_KEY environment variable
2. Fix debug mode to check environment
3. Add secure session cookie configuration
4. Install and configure Flask-WTF for CSRF

### Short-term
5. Add @login_required to all protected routes
6. Validate OAuth input data
7. Fix logout to clear full session
8. Add rate limiting

### Before production
9. Enforce HTTPS
10. Configure security logging
11. Run `pip-audit` for dependency vulnerabilities
12. Add column length constraints to models