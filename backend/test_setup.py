"""
Test script to verify backend setup without Docker
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all core modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.config import settings
        print("✓ Config module loaded")
        print(f"  - API Host: {settings.api_host}")
        print(f"  - API Port: {settings.api_port}")
        print(f"  - Database URL: {settings.database_url[:30]}...")
        print(f"  - Polling Interval: {settings.polling_interval_minutes} minutes")
        print(f"  - Market Hours: {settings.market_hours_start} - {settings.market_hours_end}")
    except Exception as e:
        print(f"✗ Config module failed: {e}")
        return False
    
    try:
        from src.models.schemas import OptionType, StrikeModeType, BaseSchema
        print("✓ Schema models loaded")
        print(f"  - OptionType values: {[e.value for e in OptionType]}")
        print(f"  - StrikeModeType values: {[e.value for e in StrikeModeType]}")
    except Exception as e:
        print(f"✗ Schema models failed: {e}")
        return False
    
    try:
        from src.api.main import app
        print("✓ FastAPI app loaded")
        print(f"  - App title: {app.title}")
        print(f"  - App version: {app.version}")
    except Exception as e:
        print(f"✗ FastAPI app failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection (requires running PostgreSQL)"""
    print("\nTesting database connection...")
    
    try:
        from src.database.connection import engine
        from sqlalchemy import text
        
        # Try to connect
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✓ Database connected: {version[:50]}...")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("  (This is expected if PostgreSQL is not running)")
        return False

def test_health_endpoint():
    """Test FastAPI health endpoint"""
    print("\nTesting FastAPI endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print(f"✓ Health endpoint working: {response.json()}")
            return True
        else:
            print(f"✗ Health endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health endpoint test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("BACKEND SETUP VERIFICATION")
    print("=" * 60)
    
    results = {
        "Imports": test_imports(),
        "Health Endpoint": test_health_endpoint(),
        "Database": test_database_connection(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n⚠ Some tests failed (database failure is expected without PostgreSQL running)")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
