"""
US Stocks API Endpoints

Handles fetching available US stocks from Yahoo Finance.
"""

from fastapi import APIRouter, HTTPException
import logging
import pandas as pd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/us-stocks", tags=["us-stocks"])


@router.get("")
async def get_us_stocks():
    """
    Get comprehensive list of available US stocks from multiple exchanges.
    Returns stocks from NYSE, NASDAQ, and AMEX.
    """
    try:
        stocks = []
        
        # Fetch from multiple sources for comprehensive coverage
        logger.info("Fetching US stock list from FTP sources")
        
        # NASDAQ listed stocks
        try:
            nasdaq_url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
            nasdaq_df = pd.read_csv(nasdaq_url, sep="|")
            nasdaq_df = nasdaq_df[nasdaq_df['Test Issue'] == 'N']  # Exclude test issues
            nasdaq_df = nasdaq_df[nasdaq_df['Financial Status'] != 'D']  # Exclude deficient
            
            for _, row in nasdaq_df.iterrows():
                if pd.notna(row['Symbol']) and row['Symbol'] != 'Symbol':
                    stocks.append({
                        'ticker': row['Symbol'],
                        'company_name': row['Security Name'] if pd.notna(row['Security Name']) else row['Symbol']
                    })
            logger.info(f"Fetched {len(stocks)} NASDAQ stocks")
        except Exception as e:
            logger.warning(f"Failed to fetch NASDAQ stocks: {e}")
        
        # Other listed stocks (NYSE, AMEX, etc.)
        try:
            other_url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
            other_df = pd.read_csv(other_url, sep="|")
            other_df = other_df[other_df['Test Issue'] == 'N']  # Exclude test issues
            
            initial_count = len(stocks)
            for _, row in other_df.iterrows():
                if pd.notna(row['ACT Symbol']) and row['ACT Symbol'] != 'ACT Symbol':
                    # Convert to Yahoo Finance format (replace $ with -)
                    ticker = row['ACT Symbol'].replace('$', '-').replace('.', '-')
                    stocks.append({
                        'ticker': ticker,
                        'company_name': row['Security Name'] if pd.notna(row['Security Name']) else ticker
                    })
            logger.info(f"Fetched {len(stocks) - initial_count} NYSE/AMEX stocks")
        except Exception as e:
            logger.warning(f"Failed to fetch NYSE/AMEX stocks: {e}")
        
        # Remove duplicates and sort
        unique_stocks = {stock['ticker']: stock for stock in stocks}
        stocks = sorted(unique_stocks.values(), key=lambda x: x['ticker'])
        
        logger.info(f"Successfully fetched {len(stocks)} total US stocks")
        return {
            'stocks': stocks,
            'total_count': len(stocks)
        }
        
    except Exception as e:
        logger.error(f"Error fetching US stocks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch US stocks: {str(e)}"
        )
