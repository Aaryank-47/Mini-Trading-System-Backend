"""
Price service for managing stock prices in Redis
"""
from app.utils.redis_manager import set_price, get_price, get_all_prices
from typing import Dict
import random
import logging

logger = logging.getLogger(__name__)

# Default symbols for the platform
DEFAULT_SYMBOLS = ["SBIN", "RELIANCE", "TCS", "INFY", "HDFC"]


class PriceService:
    """Service for managing market prices"""
    
    @staticmethod
    def initialize_prices(symbols: list = None) -> None:
        """
        Initialize prices for symbols
        
        Args:
            symbols: List of symbols to initialize (uses defaults if None)
        """
        symbols = symbols or DEFAULT_SYMBOLS
        
        for symbol in symbols:
            # Generate initial price between 1000-5000
            initial_price = round(random.uniform(1000, 5000), 2)
            set_price(symbol, initial_price)
        
        logger.info(f"✓ Prices initialized for symbols: {symbols}")
    
    @staticmethod
    def update_prices(symbols: list = None) -> Dict[str, float]:
        """
        Update prices with random fluctuation (±2%)
        
        Args:
            symbols: List of symbols to update (uses defaults if None)
            
        Returns:
            Dictionary of updated prices
        """
        symbols = symbols or DEFAULT_SYMBOLS
        updated_prices = {}
        
        for symbol in symbols:
            current_price = get_price(symbol)
            
            if current_price is None:
                # Initialize price if not exists
                initial_price = round(random.uniform(1000, 5000), 2)
                set_price(symbol, initial_price)
                updated_prices[symbol] = initial_price
            else:
                # Update with ±2% random change
                change_percent = random.uniform(-0.02, 0.02)
                new_price = round(current_price * (1 + change_percent), 2)
                set_price(symbol, new_price)
                updated_prices[symbol] = new_price
        
        return updated_prices
    
    @staticmethod
    def get_current_prices(symbols: list = None) -> Dict[str, float]:
        """
        Get current prices for symbols
        
        Args:
            symbols: List of symbols to fetch
            
        Returns:
            Dictionary of symbol -> price
        """
        symbols = symbols or DEFAULT_SYMBOLS
        return get_all_prices(symbols)
    
    @staticmethod
    def get_symbol_price(symbol: str) -> float:
        """
        Get current price for a single symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None
        """
        return get_price(symbol)
