#!/usr/bin/env python3
"""
Initialize AuraMail database.
Creates all tables and initial schema.
Run this script once after installing dependencies.
"""
from flask import Flask
from database import db, ActionLog, Progress, Report, init_db
from config import DATABASE_URL

# Create minimal Flask app for initialization (avoid circular import)
app = Flask(__name__)

# Initialize database
init_db(app)

with app.app_context():
    print("🔧 Creating database tables...")
    db.create_all()
    print("✅ Database tables created successfully!")
    print(f"   - {ActionLog.__tablename__}")
    print(f"   - {Progress.__tablename__}")
    print(f"   - {Report.__tablename__}")
    print(f"\n📊 Database URL: {DATABASE_URL}")
