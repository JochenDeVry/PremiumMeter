"""
Temporary test endpoint to trigger scraper manually
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.services.scraper import create_scraper
import traceback

router = APIRouter()

@router.post("/trigger")
async def trigger_scraper(db: Session = Depends(get_db)):
    """Manually trigger a scraper run"""
    try:
        scraper = create_scraper(db)
        metrics = scraper.scrape_all_stocks()
        return {
            "status": "completed",
            "metrics": metrics.to_dict()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
