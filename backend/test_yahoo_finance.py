"""
Yahoo Finance Diagnostic Test Script

Tests Yahoo Finance API access and provides detailed diagnostic information.
"""

import yfinance as yf
import requests
import time
from datetime import datetime

def test_basic_connectivity():
    """Test basic HTTP connectivity to Yahoo Finance"""
    print("=" * 70)
    print("TEST 1: Basic HTTP Connectivity")
    print("=" * 70)
    
    try:
        response = requests.get('https://finance.yahoo.com', timeout=10)
        print(f"✓ Status Code: {response.status_code}")
        print(f"✓ Response Time: {response.elapsed.total_seconds():.2f}s")
        print(f"✓ Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['server', 'x-request-id', 'content-type', 'cache-control']:
                print(f"  - {key}: {value}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_yfinance_single_stock(ticker='AAPL'):
    """Test fetching a single stock with yfinance"""
    print("\n" + "=" * 70)
    print(f"TEST 2: yfinance Single Stock ({ticker})")
    print("=" * 70)
    
    try:
        print(f"Fetching {ticker}...")
        stock = yf.Ticker(ticker)
        
        # Test 1: Basic info
        print("\n--- Test 2a: Basic Info ---")
        try:
            info = stock.info
            print(f"✓ Company: {info.get('longName', 'N/A')}")
            print(f"✓ Current Price: ${info.get('currentPrice', 'N/A')}")
            print(f"✓ Market Cap: ${info.get('marketCap', 'N/A'):,}")
        except Exception as e:
            print(f"✗ Info failed: {e}")
        
        # Test 2: Fast info (lighter weight)
        print("\n--- Test 2b: Fast Info ---")
        try:
            fast_info = stock.fast_info
            print(f"✓ Last Price: ${fast_info.get('last_price', 'N/A')}")
            print(f"✓ Previous Close: ${fast_info.get('previous_close', 'N/A')}")
            print(f"✓ Market State: {fast_info.get('market_state', 'N/A')}")
        except Exception as e:
            print(f"✗ Fast Info failed: {e}")
        
        # Test 3: Historical data
        print("\n--- Test 2c: Historical Data ---")
        try:
            hist = stock.history(period='1d')
            if not hist.empty:
                print(f"✓ Got {len(hist)} day(s) of data")
                print(f"✓ Latest Close: ${hist['Close'].iloc[-1]:.2f}")
            else:
                print("✗ No historical data returned")
        except Exception as e:
            print(f"✗ Historical data failed: {e}")
        
        # Test 4: Options chain
        print("\n--- Test 2d: Options Chain ---")
        try:
            exp_dates = stock.options
            if exp_dates:
                print(f"✓ Found {len(exp_dates)} expiration dates")
                print(f"✓ Nearest expiration: {exp_dates[0]}")
                
                # Try to get options for first expiration
                options = stock.option_chain(exp_dates[0])
                print(f"✓ Calls: {len(options.calls)} contracts")
                print(f"✓ Puts: {len(options.puts)} contracts")
            else:
                print("✗ No expiration dates found")
        except Exception as e:
            print(f"✗ Options chain failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Overall failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_requests():
    """Test making multiple rapid requests to check for rate limiting"""
    print("\n" + "=" * 70)
    print("TEST 3: Rate Limiting Check (5 rapid requests)")
    print("=" * 70)
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    results = []
    
    for i, ticker in enumerate(tickers, 1):
        start = time.time()
        try:
            print(f"\n[{i}/5] Fetching {ticker}...", end=' ')
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            elapsed = time.time() - start
            
            if not hist.empty:
                print(f"✓ Success ({elapsed:.2f}s)")
                results.append({'ticker': ticker, 'success': True, 'time': elapsed})
            else:
                print(f"✗ Empty data ({elapsed:.2f}s)")
                results.append({'ticker': ticker, 'success': False, 'time': elapsed, 'error': 'Empty data'})
        except Exception as e:
            elapsed = time.time() - start
            print(f"✗ Failed ({elapsed:.2f}s): {str(e)[:50]}")
            results.append({'ticker': ticker, 'success': False, 'time': elapsed, 'error': str(e)})
    
    # Summary
    print("\n--- Summary ---")
    successful = sum(1 for r in results if r['success'])
    print(f"Success Rate: {successful}/{len(results)} ({successful/len(results)*100:.0f}%)")
    print(f"Average Time: {sum(r['time'] for r in results)/len(results):.2f}s")
    
    return successful == len(results)


def test_with_delays():
    """Test with delays between requests"""
    print("\n" + "=" * 70)
    print("TEST 4: Requests with 2-second Delays")
    print("=" * 70)
    
    tickers = ['AAPL', 'MSFT', 'NVDA']
    results = []
    
    for i, ticker in enumerate(tickers, 1):
        if i > 1:
            print(f"Waiting 2 seconds...")
            time.sleep(2)
        
        start = time.time()
        try:
            print(f"\n[{i}/{len(tickers)}] Fetching {ticker}...", end=' ')
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            elapsed = time.time() - start
            
            if not hist.empty:
                print(f"✓ Success ({elapsed:.2f}s)")
                results.append(True)
            else:
                print(f"✗ Empty data ({elapsed:.2f}s)")
                results.append(False)
        except Exception as e:
            elapsed = time.time() - start
            print(f"✗ Failed ({elapsed:.2f}s): {str(e)[:50]}")
            results.append(False)
    
    successful = sum(results)
    print(f"\nSuccess Rate: {successful}/{len(results)}")
    return successful == len(results)


def test_session_headers():
    """Test with custom session and headers"""
    print("\n" + "=" * 70)
    print("TEST 5: Custom Headers Test")
    print("=" * 70)
    
    try:
        # Create session with custom headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        print("Testing with browser-like headers...")
        stock = yf.Ticker('AAPL', session=session)
        hist = stock.history(period='1d')
        
        if not hist.empty:
            print(f"✓ Success with custom headers")
            print(f"✓ Got {len(hist)} day(s) of data")
            return True
        else:
            print("✗ Empty data even with custom headers")
            return False
            
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("YAHOO FINANCE DIAGNOSTIC TEST")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    results = {
        'connectivity': test_basic_connectivity(),
        'single_stock': test_yfinance_single_stock('AAPL'),
        'rate_limiting': test_multiple_requests(),
        'with_delays': test_with_delays(),
        'custom_headers': test_session_headers()
    }
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nOverall: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.0f}%)")
    
    if results['connectivity'] and not results['single_stock']:
        print("\n⚠ DIAGNOSIS: Yahoo Finance is accessible but API calls are failing.")
        print("   This could indicate rate limiting or API changes.")
        print("   Recommendation: Add delays between requests and retry logic.")
    elif not results['connectivity']:
        print("\n⚠ DIAGNOSIS: Cannot reach Yahoo Finance servers.")
        print("   Check your internet connection and firewall settings.")
    elif results['with_delays'] and not results['rate_limiting']:
        print("\n⚠ DIAGNOSIS: Rate limiting detected.")
        print("   Recommendation: Add 2-3 second delays between stock requests.")
    elif all(results.values()):
        print("\n✓ DIAGNOSIS: All tests passed!")
        print("   Yahoo Finance API is working normally.")


if __name__ == '__main__':
    main()
