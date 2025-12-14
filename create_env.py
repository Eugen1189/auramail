#!/usr/bin/env python3
"""
Script to create/update .env file with a new secure FLASK_SECRET_KEY.
Generates a new secret key if it doesn't exist or updates it.
"""
import secrets
import os
import re

# Generate a new secure key
new_secret_key = secrets.token_hex(32)

print(f"Generated new FLASK_SECRET_KEY: {new_secret_key[:20]}...")

# Read existing .env file if it exists
env_content = {}
if os.path.exists('.env'):
    print("Reading existing .env file...")
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse existing variables
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env_content[key] = value

# Update or add FLASK_SECRET_KEY
env_content['FLASK_SECRET_KEY'] = new_secret_key

# Ensure required variables exist with defaults if not set
if 'GEMINI_API_KEY' not in env_content:
    print("⚠️  GEMINI_API_KEY not found in .env - you need to add it manually")
if 'REDIS_URL' not in env_content:
    env_content['REDIS_URL'] = 'redis://localhost:6379/0'
if 'DATABASE_URL' not in env_content:
    env_content['DATABASE_URL'] = 'sqlite:///auramail.db'
if 'BASE_URI' not in env_content:
    env_content['BASE_URI'] = 'https://127.0.0.1:5000'
if 'DEBUG' not in env_content:
    env_content['DEBUG'] = 'False'

# Write updated .env file
print("Writing updated .env file...")
with open('.env', 'w', encoding='utf-8') as f:
    f.write("# AuraMail Environment Variables\n")
    f.write("# DO NOT COMMIT THIS FILE TO GIT!\n\n")
    f.write(f"# Flask Secret Key (REQUIRED for session security)\n")
    f.write(f"FLASK_SECRET_KEY={new_secret_key}\n\n")
    
    # Write other variables
    for key, value in sorted(env_content.items()):
        if key != 'FLASK_SECRET_KEY':  # Already written
            f.write(f"{key}={value}\n")

print("✅ .env file created/updated successfully!")
print(f"✅ New FLASK_SECRET_KEY has been set")
print("\n⚠️  IMPORTANT: Make sure .env is in .gitignore to prevent committing secrets!")

