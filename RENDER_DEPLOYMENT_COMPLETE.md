# 🚀 Render Deployment Checklist - Complete Guide

## 🆘 Problem You Had
App was crashing silently during startup because:
- ❌ Lifespan handler was `raise` on database failure
- ❌ Missing/incorrect environment variables on Render
- ❌ No visible error logs due to early crash

## ✅ Solution Applied
- ✅ Fixed lifespan to use graceful degradation (no crashes)
- ✅ Better logging for debugging
- ✅ App starts even if DB/Redis temporarily unavailable

---

## 📋 BEFORE DEPLOYING TO RENDER

### ✅ Step 1: Verify Environment Variables

**In Render Dashboard**, go to your service and click **Environment**:

```
Set these variables:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PYTHONUNBUFFERED=1
ENVIRONMENT=PRODUCTION
DEBUG=False

SECRET_KEY=your-production-secret-key-min-32-characters
MYSQL_HOST=your-mysql-host.c.aivencloud.com
MYSQL_USER=avnadmin
MYSQL_PASSWORD=your-secure-password
MYSQL_DATABASE=defaultdb
REDIS_URL=redis://:your-password@your-redis-host:12345
```

**⚠️ CRITICAL:** All 6 database variables must be set, or app won't connect!

### ✅ Step 2: Clear Build Cache (THIS FIXES "Exited with status 1")

Often Render caches old build artifacts. Clear it:

1. Go to **Render Dashboard → Your Service**
2. Click **Settings** (bottom)
3. Scroll to **"Build Cache"**
4. Click **"Clear Build Cache"**
5. Wait 30 seconds
6. Go to **"Deployments"** and click **"Manual Deploy"**

**This forces a fresh build with your new requirements.txt**

### ✅ Step 3: Verify render.yaml

Ensure your `render.yaml` has:

```yaml
services:
  - type: web
    name: trading-platform-api
    runtime: python
    runtimeVersion: 3.11.9
    plan: free
    buildCommand: pip install --upgrade pip && pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHONUNBUFFERED
        value: "1"
```

**KEY POINTS:**
- ✅ `buildCommand` upgrades pip first (fixes dependency issues)
- ✅ `startCommand` uses `$PORT` variable (Render specific)
- ✅ `PYTHONUNBUFFERED=1` (see logs in real-time)

### ✅ Step 4: Verify Python Version

In Render Dashboard → Settings:
- **Runtime:** Python
- **Python Version:** 3.11 or 3.12 (NOT 3.14!)

```
✅ 3.11.9 ← Use this
✅ 3.12.x ← Or this
❌ 3.14.x ← Too new, has issues
```

---

## 🧪 Local Testing BEFORE Pushing

Test locally first to avoid wasting Render builds:

```bash
# 1. Create .env from template
cp .env.example .env

# 2. Edit .env with LOCAL credentials
nano .env
# Set:
#   MYSQL_HOST=localhost
#   MYSQL_USER=root
#   MYSQL_PASSWORD=your_local_password
#   REDIS_URL=redis://localhost:6379

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start app
uvicorn app.main:app --reload

# 5. Check logs for:
#   ✓ Database initialized
#   ✓ Redis initialized
#   ✓ Background price update task started
#   ✓ Application startup completed successfully!
```

If it works locally → it will work on Render

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Commit Changes
```bash
git add -A
git commit -m "fix: Graceful startup handling for production deployment

- Remove raise statement from lifespan (was crashing app)
- Add better logging for debugging
- Use graceful degradation for Redis/DB failures
- App now starts even if services temporarily unavailable"
```

### Step 2: Push to GitHub
```bash
git push origin main
```

### Step 3: Clear Cache & Redeploy on Render

1. **Render Dashboard** → Your Service
2. Click **Settings** (scroll to bottom)
3. **Clear Build Cache**
4. Click **Deployments**
5. Click **"Deploy Latest Commit"** or **"Manual Deploy"**

### Step 4: Monitor Logs
```
Render Dashboard → Logs

Watch for:
✅ "Starting Trading Platform API..."
✅ "Database initialized successfully"
✅ "Redis initialized successfully"  (or "continuing without Redis")
✅ "Background price update task started"
✅ "Application startup completed successfully!"
✅ "Uvicorn running on 0.0.0.0:PORT"
```

---

## 🔍 Troubleshooting: What to Do If It Still Crashes

### Issue: "Exited with status 1" (still silent crash)

**Solution 1: Check Environment Variables**
```bash
# In Render Logs, you should see environment info
# If you see: "MYSQL_HOST is None" → Not set in Render Dashboard
```

Add missing variables to Render Environment:
- MYSQL_HOST
- MYSQL_USER
- MYSQL_PASSWORD
- MYSQL_DATABASE
- REDIS_URL (optional)
- SECRET_KEY

**Solution 2: Clear Build Cache**
Render sometimes caches old builds:
1. Settings → Clear Build Cache
2. Wait 30 seconds
3. Manual Deploy

**Solution 3: Check Logs for Error Messages**
Look for these error patterns in logs:
```
"Database initialization failed: Access denied for user"
  → MYSQL_PASSWORD is wrong or MYSQL_USER wrong

"Database initialization failed: Unknown host"
  → MYSQL_HOST is wrong or doesn't exist

"Redis initialization failed: Connection refused"
  → Redis URL is wrong (optional, app continues)
```

**Solution 4: Test Database Connection Separately**

Create `test_db_connection.py`:
```python
from app.config import get_settings

settings = get_settings()
print(f"MYSQL_HOST: {settings.mysql_host}")
print(f"MYSQL_USER: {settings.mysql_user}")
print(f"MYSQL_DATABASE: {settings.mysql_database}")
print(f"Full DB URL: {settings.database_url}")

# Try to connect
from sqlalchemy import create_engine
try:
    engine = create_engine(settings.database_url)
    engine.connect()
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
```

Run locally:
```bash
python test_db_connection.py
```

---

## 📦 Database & Redis Setup (If Not Already Created)

### Option 1: Use Render's Managed Services (Easiest)

In Render Dashboard:
1. Go to your service
2. Click **"+ Add a New Resource"**
3. Select **MySQL** or **PostgreSQL**
4. Click **"Create Database"**
5. Environment variables auto-populated!

### Option 2: External Cloud Databases

**MySQL Cloud (db4free.net):**
```
MYSQL_HOST=db4free.net
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_dbname
```

**Redis Cloud (redis.com):**
```
REDIS_URL=redis://:password@host:port
```

---

## ✅ Deployment Checklist

Before each deployment, verify:

- [ ] `.env.example` exists (template for docs)
- [ ] `requirements.txt` has Pydantic 2.x versions
- [ ] `app/config.py` uses `pydantic_settings`
- [ ] `app/main.py` has graceful lifespan (no raise statements)
- [ ] All environment variables set in Render Dashboard
- [ ] Python version is 3.11 or 3.12
- [ ] Build cache cleared (if deployment fails)
- [ ] Local testing passed: `uvicorn app.main:app --reload`
- [ ] Changes committed and pushed to GitHub
- [ ] Render deployment triggered (auto or manual)
- [ ] Logs checked for successful startup

---

## 📊 Expected Logs on Successful Deployment

```
2026-04-21 19:23:10.000  ==> Build successful
2026-04-21 19:23:12.000  ==> Running 'uvicorn app.main:app --host 0.0.0.0 --port 10000'
2026-04-21 19:23:13.000  ============================================================
2026-04-21 19:23:13.001  🚀 Starting Trading Platform API...
2026-04-21 19:23:13.002  Environment: PRODUCTION
2026-04-21 19:23:13.003  Debug: False
2026-04-21 19:23:13.004  ============================================================
2026-04-21 19:23:13.050  📊 Attempting database initialization...
2026-04-21 19:23:13.150  ✓ Database initialized successfully
2026-04-21 19:23:13.160  💾 Attempting Redis initialization...
2026-04-21 19:23:13.200  ✓ Redis initialized successfully
2026-04-21 19:23:13.210  📈 Initializing market prices...
2026-04-21 19:23:13.250  ✓ Market prices initialized
2026-04-21 19:23:13.260  🔄 Starting background price update task...
2026-04-21 19:23:13.270  ✓ Background price update task started
2026-04-21 19:23:13.280  ============================================================
2026-04-21 19:23:13.281  ✅ Application startup completed successfully!
2026-04-21 19:23:13.282  ============================================================
2026-04-21 19:23:13.500  INFO:     Uvicorn running on http://0.0.0.0:10000

✅ APP IS LIVE!
```

---

## 🎯 Next Steps

1. ✅ Clear build cache
2. ✅ Set all environment variables in Render
3. ✅ Push this commit
4. ✅ Monitor logs
5. ✅ Access API at `https://your-app.onrender.com/docs`

---

## 💡 Pro Tips

**Reduce deployment time:**
- Render builds are slow
- Test locally first with `uvicorn app.main:app --reload`
- Only push when confident

**Monitor logs in real-time:**
```bash
# In terminal (if Render CLI installed):
render logs --service trading-platform-api --tail
```

**Debug environment variables:**
Add this temporary endpoint:
```python
@app.get("/config")
def get_config():
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "database_host": settings.mysql_host,
        "redis_url": settings.redis_url[:50] + "..."  # Masked for security
    }
```

Access: `https://your-app.onrender.com/config`

(Remove after debugging!)

---

Good luck! 🚀 Your app should deploy successfully now!
