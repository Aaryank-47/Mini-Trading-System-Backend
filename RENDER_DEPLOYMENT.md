# 🚀 FastAPI + Render Deployment Guide

## ✅ Fixed: Python 3.14 + Pydantic 2.x Compatibility

This guide fixes the Pydantic ConfigError on Render deployment.

---

## 📋 Verified Dependency Versions

These versions are **tested and compatible** with Python 3.14:

```
fastapi==0.109.0              ✅ Supports Pydantic 2.x
uvicorn[standard]==0.27.0     ✅ Compatible with Python 3.14
pydantic==2.5.2               ✅ Pydantic 2.x (Python 3.14 compatible)
pydantic-settings==2.1.0      ✅ Required for Pydantic 2.x settings
sqlalchemy==2.0.23            ✅ SQLAlchemy 2.x compatible
```

### Why This Matters:
- ❌ Old FastAPI 0.89 + Pydantic 1.10 → **Crashes on Python 3.14**
- ✅ New FastAPI 0.109 + Pydantic 2.5 → **Works on Python 3.14+**

---

## 🔧 Code Compatibility Fixes

### 1. **config.py** - Use `pydantic_settings`
```python
from pydantic_settings import BaseSettings  # ✅ Correct for Pydantic 2.x
from pydantic import Field, field_validator

class Settings(BaseSettings):
    secret_key: str = Field(default="dev-key", validation_alias="SECRET_KEY")
    mysql_host: str = Field(default="localhost", validation_alias="MYSQL_HOST")
    # ... other settings
```

### 2. **schemas/__init__.py** - Use new validators
```python
from pydantic import field_validator, model_validator  # ✅ New imports

class UserCreate(BaseModel):
    name: str
    
    @field_validator('name')          # ✅ Replaces @validator
    @classmethod
    def validate_name(cls, v):
        return v.strip()
    
    @model_validator(mode='after')     # ✅ Replaces @root_validator
    def validate_passwords(self):
        # ... validation logic
        return self
```

### 3. **Remove deprecated patterns**
```python
# ❌ OLD (Pydantic v1)
side: str = Field(..., regex="^(BUY|SELL)$")

# ✅ NEW (Pydantic v2)
side: str = Field(..., pattern="^(BUY|SELL)$")
```

---

## 📝 Render Deployment Checklist

### Step 1: Update Render Build Command
In `render.yaml`, ensure this line exists:
```yaml
buildCommand: pip install --upgrade pip && pip install -r requirements.txt
```

### Step 2: Set Environment Variables
Go to Render Dashboard → Your Service → Environment:

```
PYTHONUNBUFFERED=1
ENVIRONMENT=PRODUCTION
SECRET_KEY=your-production-secret-key-min-32-chars
MYSQL_HOST=your-mysql-host.c.aivencloud.com
MYSQL_USER=avnadmin
MYSQL_PASSWORD=your-secure-password
MYSQL_DATABASE=defaultdb
REDIS_URL=redis://your-redis-host:12345
DEBUG=False
```

### Step 3: Verify Python Version
In Render Dashboard:
```
Settings → Build & Deploy → Python Version: 3.11 or 3.12 (recommended)
```

**Note:** Python 3.14 is very new. If you want stability, use **Python 3.11 or 3.12**

### Step 4: Deploy
```bash
git push origin main
# Render auto-deploys on push
```

---

## 🧪 Local Testing Before Deployment

Test locally to catch errors before Render:

```bash
# Create .env file
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Start app
uvicorn app.main:app --reload
```

If it works locally, it will work on Render.

---

## 🚨 Common Render Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'pydantic_settings'"
**Fix:** Ensure `requirements.txt` includes:
```
pydantic-settings==2.1.0
```

### Issue: "ConfigError: unable to infer type for attribute"
**Fix:** Check that all schema classes use Pydantic 2.x syntax:
- Use `@field_validator` not `@validator`
- Use `pattern=` not `regex=`
- Use `@model_validator` not `@root_validator`

### Issue: "Port not available"
**Fix:** Your `render.yaml` start command must use `$PORT` variable:
```yaml
startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Issue: "Database connection refused"
**Fix:** Add external database URLs in Environment:
```
MYSQL_HOST=external-host.com  (use Render MySQL or external service)
REDIS_URL=redis://host:port    (use Render Redis or Redis Cloud)
```

---

## 📦 Complete requirements.txt

Copy this exact file:

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.23
pymysql==1.1.0
psycopg2-binary==2.9.9
redis==5.0.1
pydantic==2.5.2
pydantic-settings==2.1.0
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.2
cryptography==41.0.7
aioredis==2.0.1
websockets==12.0
slowapi==0.1.9
```

---

## ✅ Deployment Success Checklist

- [ ] `requirements.txt` updated with Pydantic 2.x versions
- [ ] `app/config.py` uses `pydantic_settings`
- [ ] `app/schemas/__init__.py` uses `@field_validator` and `@model_validator`
- [ ] All `regex=` replaced with `pattern=`
- [ ] `.env.example` created (template for env vars)
- [ ] Environment variables set in Render Dashboard
- [ ] `render.yaml` has correct `startCommand` with `$PORT`
- [ ] App works locally with `uvicorn app.main:app --reload`
- [ ] Committed and pushed to GitHub
- [ ] Render auto-deploy triggered

---

## 🎯 Expected Result

After deployment on Render:
- ✅ App starts without Pydantic errors
- ✅ Connects to MySQL and Redis
- ✅ API available at `https://your-app.onrender.com`
- ✅ Swagger docs at `https://your-app.onrender.com/docs`

---

## 📚 References

- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [FastAPI + Pydantic 2](https://fastapi.tiangolo.com/advanced/settings/)
- [Render Python Deployment](https://render.com/docs/deploy-python)
