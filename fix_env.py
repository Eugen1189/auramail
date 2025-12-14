#!/usr/bin/env python3
"""
Script to fix .env file format - adds line breaks and removes duplicates.
"""
import re

# Read the current .env file
try:
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print("Error: .env file not found!")
    exit(1)

# Extract values from the malformed content
values = {}

# Parse the malformed string
# Pattern to match KEY=VALUE
pattern = r'([A-Z_]+)=(.*?)(?=[A-Z_]+=|$)'

matches = re.findall(pattern, content)
for key, value in matches:
    # Clean up the value (remove trailing newlines/spaces)
    value = value.strip().rstrip('\n\r')
    if key not in values:  # Keep first occurrence, skip duplicates
        values[key] = value

# Add missing variables with defaults
if 'TIMEZONE' not in values:
    values['TIMEZONE'] = 'Europe/Kyiv'
if 'PROGRESS_FILE' not in values:
    values['PROGRESS_FILE'] = 'progress.json'
if 'CORS_ORIGINS' not in values:
    values['CORS_ORIGINS'] = ''
if 'ALLOW_ALL_CORS' not in values:
    values['ALLOW_ALL_CORS'] = 'False'
if 'FORCE_HTTPS' not in values:
    values['FORCE_HTTPS'] = 'True'

# Create properly formatted .env content
env_lines = [
    "# AuraMail Configuration File",
    "# IMPORTANT: Never commit .env file to Git! It contains secrets.",
    "",
    "# ============================================",
    "# CRITICAL SECURITY SETTINGS",
    "# ============================================",
    "",
    f"FLASK_SECRET_KEY={values.get('FLASK_SECRET_KEY', '')}",
    f"BASE_URI={values.get('BASE_URI', 'https://127.0.0.1:5000')}",
    f"DEBUG={values.get('DEBUG', 'False')}",
    "",
    "# ============================================",
    "# API KEYS",
    "# ============================================",
    "",
    f"GEMINI_API_KEY={values.get('GEMINI_API_KEY', '')}",
    f"GOOGLE_CLIENT_SECRETS_PATH={values.get('GOOGLE_CLIENT_SECRETS_PATH', 'client_secret.json')}",
    "",
    "# ============================================",
    "# DATABASE & REDIS",
    "# ============================================",
    "",
    f"REDIS_URL={values.get('REDIS_URL', 'redis://localhost:6379/0')}",
    "",
    "# ============================================",
    "# APPLICATION SETTINGS",
    "# ============================================",
    "",
    f"MAX_MESSAGES_TO_PROCESS={values.get('MAX_MESSAGES_TO_PROCESS', '50')}",
    f"TIMEZONE={values.get('TIMEZONE', 'Europe/Kyiv')}",
    f"LOG_FILE={values.get('LOG_FILE', 'auramail_log.json')}",
    f"PROGRESS_FILE={values.get('PROGRESS_FILE', 'progress.json')}",
    "",
    "# ============================================",
    "# SECURITY SETTINGS",
    "# ============================================",
    "",
    f"CORS_ORIGINS={values.get('CORS_ORIGINS', '')}",
    f"ALLOW_ALL_CORS={values.get('ALLOW_ALL_CORS', 'False')}",
    f"FORCE_HTTPS={values.get('FORCE_HTTPS', 'True')}",
    ""
]

# Write the corrected .env file
with open('.env', 'w', encoding='utf-8') as f:
    f.write('\n'.join(env_lines))

print("✅ .env file has been fixed!")
print("📝 Added line breaks and removed duplicates")
print("➕ Added missing variables: TIMEZONE, PROGRESS_FILE, CORS_ORIGINS, ALLOW_ALL_CORS, FORCE_HTTPS")


