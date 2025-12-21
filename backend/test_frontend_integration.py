"""
Test script to verify the query form works end-to-end by making a request
from the frontend perspective (using axios configuration).
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_query_premium():
    """Test the query premium endpoint as the frontend would call it"""
    
    # Test 1: Exact strike mode
    print("\n=== Test 1: Exact Strike ===")
    request_data = {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_mode": "exact",
        "strike_price": 270.0,
        "duration_days": 30,
        "duration_tolerance_days": 3,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/query/premium",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Ticker: {data['ticker']}")
            print(f"Option Type: {data['option_type']}")
            print(f"Results: {len(data['results'])} strike/duration combinations")
            for result in data['results'][:3]:  # Show first 3
                print(f"  Strike ${result['strike_price']}: "
                      f"Avg Premium ${result['avg_premium']:.2f}, {result['data_points']} points")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Percentage range mode
    print("\n=== Test 2: Percentage Range (±5%) ===")
    request_data = {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_mode": "percentage_range",
        "strike_price": 270.0,
        "strike_range_percent": 5.0,
        "duration_days": 30,
        "duration_tolerance_days": 3,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/query/premium",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Results: {len(data['results'])} strike/duration combinations")
            strikes = sorted(set(r['strike_price'] for r in data['results']))
            print(f"Strike Range: ${min(strikes):.2f} - ${max(strikes):.2f}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 3: Nearest strikes mode
    print("\n=== Test 3: Nearest Strikes (3 above, 3 below) ===")
    request_data = {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_mode": "nearest",
        "strike_price": 270.0,
        "nearest_count_above": 3,
        "nearest_count_below": 3,
        "duration_days": 30,
        "duration_tolerance_days": 3,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/query/premium",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Results: {len(data['results'])} strike/duration combinations")
            strikes = sorted(set(r['strike_price'] for r in data['results']))
            print(f"Strikes: {', '.join(f'${s:.2f}' for s in strikes)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 4: CORS check
    print("\n=== Test 4: CORS Headers ===")
    try:
        response = requests.options(
            f"{API_URL}/api/query/premium",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"CORS Headers:")
        for header in ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Headers']:
            print(f"  {header}: {response.headers.get(header, 'NOT SET')}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Testing Frontend-Backend Integration")
    print("=" * 50)
    test_query_premium()
    print("\n" + "=" * 50)
    print("All tests completed!")
