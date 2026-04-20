#!/usr/bin/env python3
"""
Quick dependency check before Render deployment
Tests if all imports work correctly
"""

import sys
import traceback

def test_imports():
    """Test if all critical imports work"""
    tests = [
        ("FastAPI", "from fastapi import FastAPI"),
        ("Uvicorn", "from uvicorn import run"),
        ("SQLAlchemy", "from sqlalchemy import create_engine"),
        ("Pydantic Settings", "from pydantic_settings import BaseSettings"),
        ("Pydantic", "from pydantic import BaseModel"),
        ("PyMySQL", "import pymysql"),
        ("Redis", "import redis"),
        ("WebSockets", "import websockets"),
    ]
    
    print("🧪 Testing dependencies...\n")
    
    all_passed = True
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name:<20} OK")
        except ImportError as e:
            print(f"❌ {name:<20} FAILED - {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"⚠️  {name:<20} ERROR - {str(e)}")
    
    print("\n" + "="*50)
    
    if all_passed:
        print("✅ All imports successful!")
        print("\n🚀 Ready to deploy to Render")
        return 0
    else:
        print("❌ Some imports failed!")
        print("\n💡 Run: pip install -r requirements.txt")
        return 1

def test_app_startup():
    """Test if app can startup without errors"""
    print("\n\n🧪 Testing app startup...\n")
    try:
        from app.main import app
        from app.config import get_settings
        
        settings = get_settings()
        print(f"✅ App imported successfully")
        print(f"✅ Config loaded - Environment: {settings.environment}")
        print(f"\n🚀 App is ready to start!")
        return 0
    except Exception as e:
        print(f"❌ App startup failed:")
        print(f"   {str(e)}\n")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    code1 = test_imports()
    code2 = test_app_startup()
    
    sys.exit(max(code1, code2))
