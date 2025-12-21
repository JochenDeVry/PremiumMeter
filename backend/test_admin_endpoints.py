"""
Test script to verify admin endpoints (watchlist and scheduler).
"""
import requests

API_URL = "http://localhost:8000"

def test_admin_endpoints():
    """Test watchlist and scheduler endpoints"""
    
    print("\n=== Test 1: Get Watchlist ===")
    try:
        response = requests.get(f"{API_URL}/api/watchlist")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total stocks: {data['total_count']}")
            for stock in data['watchlist'][:3]:  # Show first 3
                print(f"  {stock['ticker']}: {stock['data_points_count']} data points")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n=== Test 2: Get Scheduler Config ===")
    try:
        response = requests.get(f"{API_URL}/api/scheduler/config")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Polling interval: {data['polling_interval_minutes']} minutes")
            print(f"Market hours: {data['market_hours_start']} - {data['market_hours_end']}")
            print(f"Timezone: {data['timezone']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Testing Admin Endpoints")
    print("=" * 50)
    test_admin_endpoints()
    print("\n" + "=" * 50)
    print("Tests completed!")
