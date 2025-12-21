"""
Test script for Premium Query API endpoint

Tests all three strike matching modes with real data from database.
"""

import requests
import json
from decimal import Decimal


def test_query_endpoint():
    """Test the /api/query/premium endpoint with different modes"""
    
    base_url = "http://localhost:8000/api/query/premium"
    
    print("=" * 80)
    print("Testing Premium Query API Endpoint")
    print("=" * 80)
    
    # Test 1: Exact strike matching
    print("\n" + "=" * 80)
    print("Test 1: Exact Strike Matching (AAPL $270 call, 1 day duration)")
    print("=" * 80)
    payload = {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_mode": "exact",
        "strike_price": 270.00,
        "duration_days": 1,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(base_url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nQuery Results:")
            print(f"  Ticker: {data['ticker']}")
            print(f"  Option Type: {data['option_type']}")
            print(f"  Strike Mode: {data['strike_mode']}")
            print(f"  Total Strikes: {data['total_strikes']}")
            print(f"  Total Data Points: {data['total_data_points']}")
            
            if data['results']:
                print(f"\n  Results:")
                for result in data['results']:
                    print(f"\n    Strike: ${result['strike_price']}")
                    print(f"      Min Premium:    ${result['min_premium']}")
                    print(f"      Max Premium:    ${result['max_premium']}")
                    print(f"      Avg Premium:    ${result['avg_premium']}")
                    print(f"      Median Premium: ${result.get('median_premium', 'N/A')}")
                    print(f"      Std Dev:        ${result.get('std_premium', 'N/A')}")
                    print(f"      Avg Delta:      {result.get('avg_delta', 'N/A')}")
                    print(f"      Data Points:    {result['data_points']}")
                    print(f"      Time Range:     {result['first_seen']} to {result['last_seen']}")
            else:
                print("\n  No data found for this query")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Percentage range matching
    print("\n" + "=" * 80)
    print("Test 2: Percentage Range Matching (AAPL ±5% around $270)")
    print("=" * 80)
    payload = {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_mode": "percentage_range",
        "strike_price": 270.00,
        "strike_range_percent": 5.0,
        "duration_days": 1,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(base_url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nQuery Results:")
            print(f"  Total Strikes Found: {data['total_strikes']}")
            print(f"  Total Data Points: {data['total_data_points']}")
            print(f"  Strike Range: ${270 * 0.95:.2f} - ${270 * 1.05:.2f}")
            
            if data['results']:
                print(f"\n  Strikes in range:")
                for result in data['results'][:5]:  # Show first 5
                    print(f"    ${result['strike_price']}: Avg=${result['avg_premium']}, Points={result['data_points']}")
                if len(data['results']) > 5:
                    print(f"    ... and {len(data['results']) - 5} more strikes")
            else:
                print("\n  No data found for this query")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Nearest strikes matching
    print("\n" + "=" * 80)
    print("Test 3: Nearest Strikes Matching (3 above, 3 below current price)")
    print("=" * 80)
    payload = {
        "ticker": "AAPL",
        "option_type": "put",
        "strike_mode": "nearest",
        "nearest_count_above": 3,
        "nearest_count_below": 3,
        "duration_days": 1,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(base_url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nQuery Results:")
            print(f"  Total Strikes Found: {data['total_strikes']}")
            print(f"  Total Data Points: {data['total_data_points']}")
            
            if data['results']:
                print(f"\n  Nearest strikes:")
                for result in data['results']:
                    print(f"    ${result['strike_price']}: Avg=${result['avg_premium']}, Points={result['data_points']}")
            else:
                print("\n  No data found for this query")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Error handling - invalid ticker
    print("\n" + "=" * 80)
    print("Test 4: Error Handling (Invalid Ticker)")
    print("=" * 80)
    payload = {
        "ticker": "INVALID",
        "option_type": "call",
        "strike_mode": "exact",
        "strike_price": 100.00,
        "duration_days": 7,
        "lookback_days": 30
    }
    
    try:
        response = requests.post(base_url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Without duration filter
    print("\n" + "=" * 80)
    print("Test 5: No Duration Filter (All durations)")
    print("=" * 80)
    payload = {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_mode": "exact",
        "strike_price": 270.00,
        "lookback_days": 7
    }
    
    try:
        response = requests.post(base_url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nQuery Results:")
            print(f"  Total Strikes: {data['total_strikes']}")
            print(f"  Total Data Points: {data['total_data_points']}")
            
            if data['results']:
                for result in data['results']:
                    print(f"\n    Strike: ${result['strike_price']}")
                    print(f"      Avg Premium: ${result['avg_premium']}")
                    print(f"      Data Points: {result['data_points']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80)
    print("Testing Complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_query_endpoint()
