"""Price service for managing synthetic stock prices in Redis."""
from typing import Dict, List, Optional
import random
import logging
from sqlalchemy.orm import Session

from app.utils.redis_manager import get_all_prices, get_price, set_price
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)

# Fallback prices cache for when Redis is unavailable
_fallback_prices: Dict[str, float] = {}


def _get_initial_price(symbol: str, min_price: float = 100, max_price: float = 5000) -> float:
    """Generate a synthetic opening price for a symbol."""
    return round(random.uniform(min_price, max_price), 2)


class PriceService:
    """Service for managing market prices"""
    
    # Class-level cache of active symbols and their price ranges
    _symbols_cache: Dict[str, tuple] = {}  # symbol -> (min_price, max_price)
    _cache_initialized = False
    
    @classmethod
    def initialize_cache(cls, db: Session) -> None:
        """Initialize the symbols and price ranges cache from database"""
        try:
            cached_stocks = StockService.get_cached_active_stocks()
            cls._symbols_cache = {
                symbol: (stock['min_price'], stock['max_price'])
                for symbol, stock in cached_stocks.items()
            }
            cls._cache_initialized = True
            logger.info(f"✓ Price service cache initialized with {len(cls._symbols_cache)} symbols")
        except Exception as e:
            logger.error(f"Failed to initialize price service cache: {e}")
            raise
    
    @classmethod
    def get_active_symbols(cls) -> List[str]:
        """Get list of active symbols from cache"""
        return list(cls._symbols_cache.keys())
    
    @staticmethod
    def initialize_prices(symbols: list = None, db: Session = None) -> None:
        """
        Initialize prices for symbols
        
        Args:
            symbols: List of symbols to initialize (uses active symbols from DB if None)
            db: Database session (required if symbols is None)
        """
        if symbols is None:
            if db is None:
                raise ValueError("Database session required when symbols is None")
            symbols = StockService.get_active_symbols(db)
        
        for symbol in symbols:
            # Get price range for this symbol
            price_range = PriceService._symbols_cache.get(symbol)
            if price_range:
                min_price, max_price = price_range
            else:
                min_price, max_price = 100, 5000
            
            initial_price = _get_initial_price(symbol, min_price, max_price)
            _fallback_prices[symbol] = initial_price
            set_price(symbol, initial_price)
        
        logger.info(f"✓ Prices initialized for {len(symbols)} symbols")
    
    @staticmethod
    def update_prices(symbols: list = None, db: Session = None) -> Dict[str, float]:
        """
        Update prices with random fluctuation (±2%)
        
        Args:
            symbols: List of symbols to update (uses active symbols from cache if None)
            db: Database session (unused, for API compatibility)
            
        Returns:
            Dictionary of updated prices
        """
        if symbols is None:
            # Always use cache for symbols - it's already loaded at startup
            symbols = PriceService.get_active_symbols()
        
        updated_prices = {}
        
        for symbol in symbols:
            current_price = get_price(symbol)
            if current_price is None:
                current_price = _fallback_prices.get(symbol)
            
            if current_price is None:
                # Initialize price if not exists
                price_range = PriceService._symbols_cache.get(symbol)
                if price_range:
                    min_price, max_price = price_range
                else:
                    min_price, max_price = 100, 5000
                
                initial_price = _get_initial_price(symbol, min_price, max_price)
                _fallback_prices[symbol] = initial_price
                set_price(symbol, initial_price)
                updated_prices[symbol] = initial_price
            else:
                # Update with ±2% random change
                change_percent = random.uniform(-0.02, 0.02)
                new_price = round(current_price * (1 + change_percent), 2)
                _fallback_prices[symbol] = new_price
                set_price(symbol, new_price)
                updated_prices[symbol] = new_price
        
        return updated_prices
    
    @staticmethod
    def get_current_prices(symbols: list = None, db: Session = None) -> Dict[str, float]:
        """
        Get current prices for symbols
        
        Args:
            symbols: List of symbols to fetch (uses active symbols from cache if None)
            db: Database session (unused, for API compatibility)
            
        Returns:
            Dictionary of symbol -> price
        """
        if symbols is None:
            # Always use cache for symbols - it's already loaded at startup
            symbols = PriceService.get_active_symbols()
        
        redis_prices = get_all_prices(symbols)
        prices: Dict[str, float] = dict(redis_prices)

        for symbol in symbols:
            if symbol not in prices and symbol in _fallback_prices:
                prices[symbol] = _fallback_prices[symbol]

        if not prices:
            # Lazy warm fallback prices when Redis is unavailable from cold start
            for symbol in symbols:
                price_range = PriceService._symbols_cache.get(symbol)
                if price_range:
                    min_price, max_price = price_range
                else:
                    min_price, max_price = 100, 5000
                
                _fallback_prices[symbol] = _get_initial_price(symbol, min_price, max_price)
            
            prices.update({symbol: _fallback_prices[symbol] for symbol in symbols})

        return prices

    @staticmethod
    def get_symbol_catalog(db: Session = None) -> List[Dict[str, str]]:
        """
        Return the full symbol catalog for the frontend (from in-memory cache).
        Database parameter is optional for backward compatibility.
        """
        try:
            # Use cached stocks for better performance (no database query)
            cached_stocks = StockService.get_cached_active_stocks()
            return [
                {
                    "symbol": stock['symbol'],
                    "name": stock['company_name'],
                }
                for stock in cached_stocks.values()
            ]
        except Exception as e:
            logger.error(f"Failed to get symbol catalog: {e}")
            return []

    @staticmethod
    def get_symbol_name(symbol: str, db: Session) -> str:
        """Return the full display name for a symbol code."""
        try:
            stock = StockService.get_stock_by_symbol(db, symbol)
            if stock:
                return stock.company_name
            return symbol
        except Exception as e:
            logger.error(f"Failed to get symbol name for {symbol}: {e}")
            return symbol
    
    @staticmethod
    def get_symbol_price(symbol: str) -> Optional[float]:
        """
        Get current price for a single symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None
        """
        price = get_price(symbol)
        if price is not None:
            _fallback_prices[symbol] = price
            return price

        fallback_price = _fallback_prices.get(symbol)
        if fallback_price is not None:
            return fallback_price

        if symbol in PriceService._symbols_cache:
            min_price, max_price = PriceService._symbols_cache[symbol]
            fallback_price = _get_initial_price(symbol, min_price, max_price)
            _fallback_prices[symbol] = fallback_price
            return fallback_price

        return None
