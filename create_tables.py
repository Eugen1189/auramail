#!/usr/bin/env python3
"""
Quick script to create database tables in Docker.
Run: docker compose exec web python create_tables.py
"""
from server import app
from database import db, ActionLog, Progress, Report

with app.app_context():
    print("🔧 Creating database tables...")
    
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
        print(f"   - {ActionLog.__tablename__}")
        print(f"   - {Progress.__tablename__}")
        print(f"   - {Report.__tablename__}")
        
        # Verify tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n✅ Verified {len(tables)} tables exist in database")
        for table in tables:
            print(f"   ✓ {table}")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

