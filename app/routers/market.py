"""
Market data API routes
"""
from fastapi import APIRouter, HTTPException, status
from app.services.price_service import PriceService
from typing import Dict

router = APIRouter(
    prefix="/market",
    tags=["Market"],
    responses={404: {"description": "Not found"}}
)


@router.get("/prices", response_model=Dict[str, float])
def get_prices():
    """
    Get current market prices for all active symbols
    Prices are fetched from Redis in real-time
    """
    try:
        prices = PriceService.get_current_prices()
        if not prices:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No prices available. Price service may not be running."
            )
        return prices
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch prices: {str(e)}"
        )


@router.get("/symbols")
def get_symbols():
    """Return the synthetic symbol catalog with short codes and full names."""
    return {"symbols": PriceService.get_symbol_catalog()}


@router.get("/symbols")
def get_symbols():
    """Get the synthetic market symbol catalog with short codes and full names."""
    return {
        "symbols": PriceService.get_symbol_catalog()
    }


@router.get("/price/{symbol}")
def get_symbol_price(symbol: str):
    """
    Get current price for a specific symbol
    """
    price = PriceService.get_symbol_price(symbol.upper())
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price not found for symbol {symbol}"
        )
    return {
        "symbol": symbol.upper(),
        "price": price
    }


@router.get("/health")
def market_health():
    """Check market data service health"""
    try:
        prices = PriceService.get_current_prices()
        return {
            "status": "healthy" if prices else "degraded",
            "available_symbols": len(prices) if prices else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
