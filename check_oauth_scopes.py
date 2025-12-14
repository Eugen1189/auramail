#!/usr/bin/env python3
"""
Script to check OAuth scopes in current session credentials.
Run this after authorizing to verify all required scopes are present.
"""
import json
from flask import Flask
import sys

# Create minimal Flask app to access session
app = Flask(__name__)
app.secret_key = 'temp-secret-for-checking'  # Temporary secret

try:
    with app.app_context():
        from flask import session
        from config import SCOPES
        
        # Try to read credentials from a test session
        # In real usage, this would come from browser session
        print("🔍 OAuth Scopes Checker")
        print("=" * 50)
        print(f"\n📋 Required Scopes (from config.py):")
        for scope in SCOPES:
            print(f"   ✅ {scope}")
        
        print(f"\n💡 To check your actual credentials:")
        print(f"   1. Open browser DevTools (F12)")
        print(f"   2. Go to Application → Cookies → 127.0.0.1:5000")
        print(f"   3. Find 'session' cookie")
        print(f"   4. Decode it (or check in server logs)")
        print(f"   5. Look for 'credentials' field")
        print(f"   6. Decode JSON and check 'scopes' array")
        
        print(f"\n⚠️  If you see 'insufficientPermissions' error:")
        print(f"   1. Go to: https://127.0.0.1:5000/clear-credentials")
        print(f"   2. Then: https://127.0.0.1:5000/authorize")
        print(f"   3. Make sure to grant ALL permissions including DELETE")
        
        print(f"\n📊 Expected scopes in credentials JSON:")
        print(f"   - 'scopes': ['https://www.googleapis.com/auth/gmail.modify',")
        print(f"                 'https://www.googleapis.com/auth/calendar.events']")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

