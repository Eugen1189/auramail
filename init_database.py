#!/usr/bin/env python3
"""
Initialize AuraMail database.
Creates all tables and initial schema.
Run this script once after installing dependencies.
"""
from database import db, ActionLog, Progress, Report
from config import DATABASE_URL
from app_factory import create_app

# Use the same app factory as the main application
# This ensures tables are created in the same database
app = create_app()

with app.app_context():
    print("🔧 Creating database tables...")
    print(f"📊 Database URL: {DATABASE_URL}")
    
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
