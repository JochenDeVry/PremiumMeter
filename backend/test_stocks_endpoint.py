"""
Test the stocks endpoint.
"""
import requests

API_URL = "http://localhost:8000"

def test_stocks_endpoint():
    """Test the stocks list endpoint"""
    
    print("\n=== Test: Get All Stocks ===")
    try:
        response = requests.get(f"{API_URL}/api/stocks")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            stocks = response.json()
            print(f"Total stocks: {len(stocks)}")
            print("\nFirst 5 stocks:")
            for stock in stocks[:5]:
                print(f"  {stock['ticker']}: {stock['company_name']}")
            
            # Test filtering
            print("\nTesting filter for 'AA':")
            aa_stocks = [s for s in stocks if 'aa' in s['ticker'].lower() or 'aa' in s['company_name'].lower()]
            for stock in aa_stocks[:5]:
                print(f"  {stock['ticker']}: {stock['company_name']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Testing Stocks Endpoint")
    print("=" * 50)
    test_stocks_endpoint()
    print("\n" + "=" * 50)
