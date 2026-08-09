"""
Stock management API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database import SessionLocal
from app.schemas import (
    StockCreate,
    StockResponse,
    StockListResponse,
    StockSymbolResponse,
    ApiResponse,
)
from app.services.stock_service import StockService
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stocks",
    tags=["Stocks"],
    responses={404: {"description": "Not found"}},
)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=dict)
def get_all_stocks(db: Session = Depends(get_db)):
    """
    Get all active stocks
    
    Returns list of active stocks with complete details for frontend consumption
    """
    try:
        stocks = StockService.get_active_stock_list(db)
        return {
            "success": True,
            "count": len(stocks),
            "data": [
                {
                    "id": stock.id,
                    "symbol": stock.symbol,
                    "company_name": stock.company_name,
                    "is_active": stock.is_active,
                }
                for stock in stocks
            ],
        }
    except Exception as e:
        logger.error(f"Failed to fetch stocks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stocks",
        )


@router.get("/details", response_model=dict)
def get_all_stocks_with_details(db: Session = Depends(get_db)):
    """
    Get all active stocks with complete details including price ranges
    """
    try:
        stocks = StockService.get_all_active_stocks(db)
        return {
            "success": True,
            "count": len(stocks),
            "data": [StockResponse.from_orm(stock).dict() for stock in stocks],
        }
    except Exception as e:
        logger.error(f"Failed to fetch stock details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stock details",
        )


@router.get("/symbols", response_model=dict)
def get_active_symbols(db: Session = Depends(get_db)):
    """
    Get list of active stock symbols only
    
    Frontend use case: Symbol selector, trading forms, watchlists
    """
    try:
        symbols = StockService.get_active_symbols(db)
        return {
            "success": True,
            "symbols": symbols,
            "count": len(symbols),
        }
    except Exception as e:
        logger.error(f"Failed to fetch symbols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch symbols",
        )


@router.get("/{symbol}", response_model=dict)
def get_stock_by_symbol(symbol: str, db: Session = Depends(get_db)):
    """
    Get details for a specific stock by symbol
    
    Frontend use case: Stock detail page, trading screen, symbol information panel
    """
    try:
        stock = StockService.get_stock_by_symbol(db, symbol.upper())
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {symbol} not found",
            )
        
        return {
            "success": True,
            "data": {
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "min_price": stock.min_price,
                "max_price": stock.max_price,
                "is_active": stock.is_active,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch stock {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stock {symbol}",
        )


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_stock(
    stock_data: StockCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new stock (Admin API)
    
    Allows administrators to add new stocks without code modification
    """
    try:
        new_stock = StockService.create_stock(db, stock_data)
        return {
            "success": True,
            "message": f"Stock {stock_data.symbol} created successfully",
            "data": StockResponse.from_orm(new_stock).dict(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create stock: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create stock",
        )


@router.patch("/{symbol}/activate", response_model=dict)
def activate_stock(symbol: str, db: Session = Depends(get_db)):
    """
    Activate a stock (Admin API)
    
    Makes a stock available for trading
    """
    try:
        stock = StockService.activate_stock(db, symbol.upper())
        return {
            "success": True,
            "message": f"Stock {symbol} activated",
            "data": StockResponse.from_orm(stock).dict(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to activate stock {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate stock",
        )


@router.patch("/{symbol}/deactivate", response_model=dict)
def deactivate_stock(symbol: str, db: Session = Depends(get_db)):
    """
    Deactivate a stock (Admin API)
    
    Makes a stock unavailable for trading
    """
    try:
        stock = StockService.deactivate_stock(db, symbol.upper())
        return {
            "success": True,
            "message": f"Stock {symbol} deactivated",
            "data": StockResponse.from_orm(stock).dict(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to deactivate stock {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate stock",
        )


@router.get("/health", response_model=dict)
def stock_service_health(db: Session = Depends(get_db)):
    """
    Health check for stock service
    """
    try:
        total = StockService.get_all_stocks(db)
        active = StockService.get_all_active_stocks(db)
        return {
            "status": "healthy",
            "total_stocks": len(total),
            "active_stocks": len(active),
        }
    except Exception as e:
        logger.error(f"Stock service health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
