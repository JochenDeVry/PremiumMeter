"""
Manual scraper test - bypasses market hours check
Run this to test if the scraper is working
"""
import sys
sys.path.insert(0, 'C:/PremiumMeter/PremiumMeter/backend')

from src.database.connection import get_db
from src.models.stock import Stock
from src.services.scraper import create_scraper

db = next(get_db())

try:
    print("Creating scraper...")
    scraper = create_scraper(db)
    
    # Get first stock from database
    stock = db.query(Stock).filter(Stock.ticker == 'AAPL').first()
    if not stock:
        print("AAPL not found in database!")
        sys.exit(1)
    
    print(f"\nTesting scrape for {stock.ticker} (ID: {stock.stock_id})...")
    print("This will take 10-30 seconds...")
    
    contracts = scraper._scrape_stock(stock)
    print(f"\nSuccess! Collected {contracts} options contracts")
    
    # Check database
    from src.models.historical_premium_record import HistoricalPremiumRecord
    count = db.query(HistoricalPremiumRecord).filter(
        HistoricalPremiumRecord.stock_id == stock.stock_id
    ).count()
    print(f"Database now has {count} contracts for {stock.ticker}")
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
