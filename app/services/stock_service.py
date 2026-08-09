"""Service for managing stock master data."""
from typing import Dict, List, Optional
import logging
from sqlalchemy.orm import Session
from app.models import Stock
from app.schemas import StockCreate, StockResponse, StockListResponse, StockSymbolResponse

logger = logging.getLogger(__name__)


class StockService:
    """Service for managing stocks"""
    
    _cache: Dict[str, dict] = {}  # In-memory cache for active stocks
    _cache_initialized = False
    
    @staticmethod
    def _load_cache(db: Session) -> None:
        """Load active stocks into cache"""
        try:
            active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
            StockService._cache = {
                stock.symbol: {
                    'id': stock.id,
                    'symbol': stock.symbol,
                    'company_name': stock.company_name,
                    'min_price': stock.min_price,
                    'max_price': stock.max_price,
                    'is_active': stock.is_active
                }
                for stock in active_stocks
            }
            StockService._cache_initialized = True
            logger.info(f"✓ Loaded {len(StockService._cache)} active stocks into cache")
        except Exception as e:
            logger.error(f"Failed to load stocks into cache: {e}")
            raise
    
    @classmethod
    def get_all_stocks(cls, db: Session) -> List[StockResponse]:
        """Get all stocks (active and inactive)"""
        try:
            stocks = db.query(Stock).all()
            return [StockResponse.from_orm(stock) for stock in stocks]
        except Exception as e:
            logger.error(f"Failed to fetch all stocks: {e}")
            raise
    
    @classmethod
    def get_all_active_stocks(cls, db: Session) -> List[StockResponse]:
        """Get all active stocks"""
        try:
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
            return [StockResponse.from_orm(stock) for stock in stocks]
        except Exception as e:
            logger.error(f"Failed to fetch active stocks: {e}")
            raise
    
    @classmethod
    def get_active_stock_list(cls, db: Session) -> List[StockListResponse]:
        """Get list of active stocks with minimal fields"""
        try:
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
            return [StockListResponse.from_orm(stock) for stock in stocks]
        except Exception as e:
            logger.error(f"Failed to fetch active stock list: {e}")
            raise
    
    @classmethod
    def get_active_symbols(cls, db: Session) -> List[str]:
        """Get list of active stock symbols"""
        try:
            symbols = db.query(Stock.symbol).filter(Stock.is_active == True).all()
            return [s[0] for s in symbols]
        except Exception as e:
            logger.error(f"Failed to fetch active symbols: {e}")
            raise
    
    @classmethod
    def get_stock_by_symbol(cls, db: Session, symbol: str) -> Optional[StockResponse]:
        """Get stock by symbol"""
        try:
            stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
            if stock:
                return StockResponse.from_orm(stock)
            return None
        except Exception as e:
            logger.error(f"Failed to fetch stock {symbol}: {e}")
            raise
    
    @classmethod
    def get_price_range_by_symbol(cls, db: Session, symbol: str) -> Optional[tuple]:
        """Get price range (min_price, max_price) for a symbol"""
        try:
            stock = db.query(Stock).filter(
                Stock.symbol == symbol.upper(),
                Stock.is_active == True
            ).first()
            if stock:
                return (stock.min_price, stock.max_price)
            return None
        except Exception as e:
            logger.error(f"Failed to fetch price range for {symbol}: {e}")
            raise
    
    @classmethod
    def create_stock(cls, db: Session, stock_data: StockCreate) -> StockResponse:
        """Create a new stock"""
        try:
            # Check if stock already exists
            existing = db.query(Stock).filter(
                Stock.symbol == stock_data.symbol.upper()
            ).first()
            if existing:
                raise ValueError(f"Stock with symbol {stock_data.symbol} already exists")
            
            new_stock = Stock(
                symbol=stock_data.symbol.upper(),
                company_name=stock_data.company_name,
                min_price=stock_data.min_price,
                max_price=stock_data.max_price,
                is_active=stock_data.is_active
            )
            db.add(new_stock)
            db.commit()
            db.refresh(new_stock)
            
            logger.info(f"✓ Created stock: {new_stock.symbol}")
            
            # Refresh cache if new stock is active
            if new_stock.is_active:
                cls._cache[new_stock.symbol] = {
                    'id': new_stock.id,
                    'symbol': new_stock.symbol,
                    'company_name': new_stock.company_name,
                    'min_price': new_stock.min_price,
                    'max_price': new_stock.max_price,
                    'is_active': new_stock.is_active
                }
            
            return StockResponse.from_orm(new_stock)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create stock: {e}")
            raise
    
    @classmethod
    def bulk_seed_stocks(cls, db: Session, stocks_data: List[Dict]) -> List[StockResponse]:
        """Bulk insert stocks (idempotent - only inserts if not present)"""
        try:
            created_stocks = []
            
            for stock_data in stocks_data:
                # Check if stock already exists
                existing = db.query(Stock).filter(
                    Stock.symbol == stock_data['symbol'].upper()
                ).first()
                
                if existing:
                    logger.debug(f"Stock {stock_data['symbol']} already exists, skipping")
                    continue
                
                new_stock = Stock(
                    symbol=stock_data['symbol'].upper(),
                    company_name=stock_data['company_name'],
                    min_price=stock_data['min_price'],
                    max_price=stock_data['max_price'],
                    is_active=stock_data.get('is_active', True)
                )
                db.add(new_stock)
                created_stocks.append(new_stock)
            
            if created_stocks:
                db.commit()
                for stock in created_stocks:
                    db.refresh(stock)
                logger.info(f"✓ Seeded {len(created_stocks)} new stocks")
            else:
                logger.info("No new stocks to seed (all already present)")
            
            # Refresh cache
            cls._load_cache(db)
            
            return [StockResponse.from_orm(stock) for stock in created_stocks]
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to seed stocks: {e}")
            raise
    
    @classmethod
    def activate_stock(cls, db: Session, symbol: str) -> StockResponse:
        """Activate a stock"""
        try:
            stock = db.query(Stock).filter(
                Stock.symbol == symbol.upper()
            ).first()
            
            if not stock:
                raise ValueError(f"Stock {symbol} not found")
            
            if stock.is_active:
                logger.info(f"Stock {symbol} is already active")
                return StockResponse.from_orm(stock)
            
            stock.is_active = True
            db.commit()
            db.refresh(stock)
            
            logger.info(f"✓ Activated stock: {symbol}")
            
            # Add to cache
            cls._cache[stock.symbol] = {
                'id': stock.id,
                'symbol': stock.symbol,
                'company_name': stock.company_name,
                'min_price': stock.min_price,
                'max_price': stock.max_price,
                'is_active': stock.is_active
            }
            
            return StockResponse.from_orm(stock)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to activate stock {symbol}: {e}")
            raise
    
    @classmethod
    def deactivate_stock(cls, db: Session, symbol: str) -> StockResponse:
        """Deactivate a stock"""
        try:
            stock = db.query(Stock).filter(
                Stock.symbol == symbol.upper()
            ).first()
            
            if not stock:
                raise ValueError(f"Stock {symbol} not found")
            
            if not stock.is_active:
                logger.info(f"Stock {symbol} is already inactive")
                return StockResponse.from_orm(stock)
            
            stock.is_active = False
            db.commit()
            db.refresh(stock)
            
            logger.info(f"✓ Deactivated stock: {symbol}")
            
            # Remove from cache
            if symbol.upper() in cls._cache:
                del cls._cache[symbol.upper()]
            
            return StockResponse.from_orm(stock)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to deactivate stock {symbol}: {e}")
            raise
    
    @classmethod
    def get_cached_active_stocks(cls) -> Dict[str, dict]:
        """Get cached active stocks (for performance-critical operations)"""
        return cls._cache.copy()
    
    @classmethod
    def refresh_cache(cls, db: Session) -> None:
        """Manually refresh the active stocks cache"""
        cls._load_cache(db)
