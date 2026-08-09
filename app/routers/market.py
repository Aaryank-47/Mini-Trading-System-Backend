"""
Market data API routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.services.price_service import PriceService
from app.database import get_db
from sqlalchemy.orm import Session
from typing import Dict

router = APIRouter(
    prefix="/market",
    tags=["Market"],
    responses={404: {"description": "Not found"}}
)


@router.get("/prices", response_model=Dict[str, float])
def get_prices(db: Session = Depends(get_db)):
    """
    Get current market prices for all active symbols
    Prices are fetched from Redis in real-time
    Frontend use case: Market dashboard, live ticker, portfolio valuation
    """
    try:
        prices = PriceService.get_current_prices(db=db)
        if not prices:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No prices available. Price service may not be running."
            )
        return prices
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch prices: {str(e)}"
        )


@router.get("/price/{symbol}")
def get_symbol_price(symbol: str):
    """
    Get current price for a specific symbol
    Frontend use case: Trading page, order placement screen, stock details page
    """
    price = PriceService.get_symbol_price(symbol.upper())
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price not found for symbol {symbol}"
        )
    return {
        "success": True,
        "symbol": symbol.upper(),
        "price": price
    }


@router.get("/symbols")
def get_symbols(db: Session = Depends(get_db)):
    """
    Get the symbol catalog with company names (from in-memory cache)
    Frontend use case: Symbol dropdowns, search, stock lists
    """
    try:
        symbols = PriceService.get_symbol_catalog()  # Now uses cache, db optional
        return {
            "success": True,
            "symbols": symbols,
            "count": len(symbols)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch symbols: {str(e)}"
        )


@router.get("/health")
def market_health(db: Session = Depends(get_db)):
    """Check market data service health"""
    try:
        prices = PriceService.get_current_prices(db=db)
        return {
            "status": "healthy" if prices else "degraded",
            "available_symbols": len(prices) if prices else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
