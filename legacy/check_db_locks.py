"""
Script to check for database locks and hanging processes.
Run this before tests if you encounter "database is locked" errors.
"""
import os
import glob
import sys

def check_sqlite_files():
    """Check for SQLite database files and lock files."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Main database file (expected to exist)
    main_db = os.path.join(project_root, 'auramail.db')
    
    # Test database files (should not exist or be locked)
    test_patterns = [
        'test_*.db',
        'test_*.db-shm',
        'test_*.db-wal',
        'test_*.db-journal',
        '*.db-shm',  # Lock files for main DB
        '*.db-wal',  # WAL files for main DB
        '*.db-journal'  # Journal files
    ]
    
    # Check main database
    main_db_locked = False
    if os.path.exists(main_db):
        try:
            with open(main_db, 'r+b') as f:
                pass
            print(f"✓ Main database ({os.path.basename(main_db)}) - accessible")
        except PermissionError:
            print(f"⚠️  Main database ({os.path.basename(main_db)}) - LOCKED")
            main_db_locked = True
        except Exception as e:
            print(f"? Main database ({os.path.basename(main_db)}) - {e}")
    
    # Check test database files and lock files
    test_files = []
    for pattern in test_patterns:
        files = glob.glob(os.path.join(project_root, pattern))
        # Filter out main database file
        test_files.extend([f for f in files if f != main_db])
    
    if test_files:
        print("\n⚠️  Found test database files or lock files:")
        for file in test_files:
            if os.path.exists(file):
                try:
                    with open(file, 'r+b') as f:
                        pass
                    print(f"  ✓ {os.path.basename(file)} - accessible")
                except PermissionError:
                    print(f"  ✗ {os.path.basename(file)} - LOCKED (cannot access)")
                except Exception as e:
                    print(f"  ? {os.path.basename(file)} - {e}")
    else:
        print("\n✓ No test database files found (good for in-memory tests)")
    
    return test_files, main_db_locked

def check_python_processes():
    """Check for running Python processes (Windows)."""
    if sys.platform == 'win32':
        try:
            import subprocess
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split('\n')
            # Skip header
            processes = [line for line in lines[1:] if line.strip()]
            
            if processes:
                print(f"\n⚠️  Found {len(processes)} Python process(es):")
                for proc in processes:
                    print(f"  {proc}")
                print("\n💡 Tip: Close these processes if they're holding database locks")
                print("   Use Task Manager or: taskkill /F /IM python.exe")
            else:
                print("\n✓ No Python processes found")
            
            return processes
        except Exception as e:
            print(f"\n⚠️  Could not check processes: {e}")
            return []
    else:
        print("\n💡 On Linux/Mac, use: ps aux | grep python")
        return []

def cleanup_lock_files():
    """Attempt to remove SQLite lock files."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    lock_patterns = [
        '*.db-shm',
        '*.db-wal',
        '*.db-journal'
    ]
    
    cleaned = []
    for pattern in lock_patterns:
        files = glob.glob(os.path.join(project_root, pattern))
        for file in files:
            try:
                os.remove(file)
                cleaned.append(file)
                print(f"  ✓ Removed: {file}")
            except Exception as e:
                print(f"  ✗ Could not remove {file}: {e}")
    
    return cleaned

if __name__ == '__main__':
    print("=" * 60)
    print("Database Lock Checker")
    print("=" * 60)
    
    print("\n1. Checking for SQLite files...")
    test_files, main_db_locked = check_sqlite_files()
    
    print("\n2. Checking for Python processes...")
    processes = check_python_processes()
    
    # Only show warning if main DB is locked or test files exist
    if main_db_locked or test_files:
        print("\n3. Attempting to clean up lock files...")
        cleaned = cleanup_lock_files()
        if cleaned:
            print(f"\n✓ Cleaned up {len(cleaned)} lock file(s)")
        else:
            if test_files:
                print("\n⚠️  Could not clean up some lock files")
            else:
                print("\nℹ️  No lock files to clean up")
    
    # Show specific recommendations based on findings
    print("\n" + "=" * 60)
    print("Status Summary:")
    print("=" * 60)
    if main_db_locked:
        print("⚠️  Main database is LOCKED - close Flask/Python processes")
    else:
        print("✓ Main database is accessible")
    
    if test_files:
        print("⚠️  Test database files found - these should be cleaned up")
    else:
        print("✓ No test database files (tests use in-memory DB)")
    
    if processes:
        print(f"⚠️  {len(processes)} Python process(es) running")
        print("   Note: This is OK if it's your test runner or IDE")
    else:
        print("✓ No Python processes running")
    
    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)
    print("1. Ensure all Flask/Python processes are stopped")
    print("2. Use in-memory database for tests (sqlite:///:memory:)")
    print("3. Check pytest.ini has -p no:xdist (no parallel execution)")
    print("4. Run tests with: pytest tests/ -v")
    print("=" * 60)

