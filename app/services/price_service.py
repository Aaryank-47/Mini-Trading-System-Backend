"""Price service for managing synthetic stock prices in Redis."""
from typing import Dict, List, Optional
import random
import logging

from app.utils.redis_manager import get_all_prices, get_price, set_price

logger = logging.getLogger(__name__)

SYMBOL_CATALOG = [
    {"code": "SBIN", "name": "State Bank of India", "low": 550, "high": 750},
    {"code": "RELI", "name": "Reliance Industries", "low": 2200, "high": 3200},
    {"code": "TCS", "name": "Tata Consultancy Services", "low": 3200, "high": 4500},
    {"code": "INFY", "name": "Infosys", "low": 1300, "high": 2100},
    {"code": "HDFC", "name": "HDFC Bank", "low": 1400, "high": 1900},
    {"code": "ICIC", "name": "ICICI Bank", "low": 900, "high": 1300},
    {"code": "ITC", "name": "ITC Limited", "low": 350, "high": 550},
    {"code": "LT", "name": "Larsen & Toubro", "low": 3000, "high": 4800},
    {"code": "AXIS", "name": "Axis Bank", "low": 950, "high": 1400},
    {"code": "KOTK", "name": "Kotak Mahindra Bank", "low": 1600, "high": 2200},
    {"code": "BAJF", "name": "Bajaj Finance", "low": 6000, "high": 8000},
    {"code": "HUNI", "name": "Hindustan Unilever", "low": 2200, "high": 3000},
    {"code": "ASPA", "name": "Asian Paints", "low": 2800, "high": 3600},
    {"code": "MRTI", "name": "Maruti Suzuki", "low": 9000, "high": 13000},
    {"code": "SUNP", "name": "Sun Pharmaceutical Industries", "low": 1400, "high": 1900},
    {"code": "TITN", "name": "Titan Company", "low": 3000, "high": 4200},
    {"code": "NEST", "name": "Nestle India", "low": 2200, "high": 2800},
    {"code": "WIPR", "name": "Wipro", "low": 450, "high": 800},
    {"code": "TECH", "name": "Tech Mahindra", "low": 1200, "high": 1800},
    {"code": "ULTR", "name": "UltraTech Cement", "low": 9000, "high": 12000},
    {"code": "ADEN", "name": "Adani Enterprises", "low": 2500, "high": 3500},
    {"code": "ADPO", "name": "Adani Ports", "low": 900, "high": 1500},
    {"code": "PWRG", "name": "Power Grid Corporation", "low": 250, "high": 400},
    {"code": "NTPC", "name": "NTPC Limited", "low": 300, "high": 450},
    {"code": "ONGC", "name": "Oil and Natural Gas Corporation", "low": 250, "high": 400},
    {"code": "COAL", "name": "Coal India", "low": 350, "high": 550},
    {"code": "TSTE", "name": "Tata Steel", "low": 100, "high": 180},
    {"code": "BFSV", "name": "Bajaj Finserv", "low": 1500, "high": 2200},
    {"code": "SBLI", "name": "SBI Life Insurance", "low": 1200, "high": 1800},
    {"code": "INDB", "name": "IndusInd Bank", "low": 1300, "high": 1800},
    {"code": "HCLT", "name": "HCL Technologies", "low": 1200, "high": 1900},
    {"code": "GRAS", "name": "Grasim Industries", "low": 1800, "high": 2800},
    {"code": "JSWS", "name": "JSW Steel", "low": 700, "high": 1200},
    {"code": "BPCL", "name": "Bharat Petroleum", "low": 450, "high": 700},
    {"code": "DRRD", "name": "Dr. Reddy's Laboratories", "low": 4800, "high": 6500},
    {"code": "DIVI", "name": "Divi's Laboratories", "low": 3000, "high": 4300},
    {"code": "CIPL", "name": "Cipla", "low": 1200, "high": 1800},
    {"code": "EICH", "name": "Eicher Motors", "low": 3000, "high": 5000},
    {"code": "SHRI", "name": "Shriram Finance", "low": 2500, "high": 3800},
    {"code": "TTMO", "name": "Tata Motors", "low": 800, "high": 1300},
    {"code": "APOL", "name": "Apollo Hospitals", "low": 5000, "high": 7000},
    {"code": "MNM", "name": "Mahindra & Mahindra", "low": 2500, "high": 3800},
    {"code": "BRIT", "name": "Britannia Industries", "low": 4300, "high": 6000},
    {"code": "HERO", "name": "Hero MotoCorp", "low": 3500, "high": 5500},
    {"code": "TCON", "name": "Tata Consumer Products", "low": 800, "high": 1200},
    {"code": "HIND", "name": "Hindalco Industries", "low": 500, "high": 900},
    {"code": "UPL", "name": "UPL Limited", "low": 450, "high": 750},
    {"code": "VEDL", "name": "Vedanta", "low": 350, "high": 600},
    {"code": "BOSC", "name": "Bosch Limited", "low": 25000, "high": 35000},
    {"code": "LTIM", "name": "LTIMindtree", "low": 4500, "high": 6500},
    {"code": "PIDI", "name": "Pidilite Industries", "low": 2500, "high": 3500},
    {"code": "ZOMA", "name": "Zomato", "low": 130, "high": 250},
    {"code": "DMRT", "name": "Avenue Supermarts", "low": 3300, "high": 4700},
    {"code": "LICI", "name": "Life Insurance Corporation of India", "low": 800, "high": 1300},
    {"code": "HAVE", "name": "Havells India", "low": 1300, "high": 2000},
]

DEFAULT_SYMBOLS = [item["code"] for item in SYMBOL_CATALOG]

_INITIAL_PRICE_RANGES = {
    item["code"]: (item["low"], item["high"])
    for item in SYMBOL_CATALOG
}

_SYMBOL_LOOKUP = {item["code"]: item for item in SYMBOL_CATALOG}
_fallback_prices: Dict[str, float] = {}


def _get_initial_price(symbol: str) -> float:
    """Generate a synthetic opening price for a symbol."""
    low, high = _INITIAL_PRICE_RANGES.get(symbol, (100, 5000))
    return round(random.uniform(low, high), 2)


def _get_symbol_name(symbol: str) -> str:
    """Return the full display name for a market code."""
    return _SYMBOL_LOOKUP.get(symbol, {}).get("name", symbol)


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
            initial_price = _get_initial_price(symbol)
            _fallback_prices[symbol] = initial_price
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
                current_price = _fallback_prices.get(symbol)
            
            if current_price is None:
                # Initialize price if not exists
                initial_price = _get_initial_price(symbol)
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
    def get_current_prices(symbols: list = None) -> Dict[str, float]:
        """
        Get current prices for symbols
        
        Args:
            symbols: List of symbols to fetch
            
        Returns:
            Dictionary of symbol -> price
        """
        symbols = symbols or DEFAULT_SYMBOLS
        redis_prices = get_all_prices(symbols)
        prices: Dict[str, float] = dict(redis_prices)

        for symbol in symbols:
            if symbol not in prices and symbol in _fallback_prices:
                prices[symbol] = _fallback_prices[symbol]

        if not prices:
            # Lazy warm fallback prices when Redis is unavailable from cold start.
            for symbol in symbols:
                _fallback_prices[symbol] = _get_initial_price(symbol)
            prices.update({symbol: _fallback_prices[symbol] for symbol in symbols})

        return prices

    @staticmethod
    def get_symbol_catalog() -> List[Dict[str, str]]:
        """Return the full symbol catalog for the frontend."""
        return [
            {
                "symbol": item["code"],
                "name": item["name"],
            }
            for item in SYMBOL_CATALOG
        ]

    @staticmethod
    def get_symbol_name(symbol: str) -> str:
        """Return the full display name for a symbol code."""
        return _get_symbol_name(symbol)
    
    @staticmethod
    def get_symbol_price(symbol: str) -> float:
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

        if symbol in DEFAULT_SYMBOLS:
            fallback_price = _get_initial_price(symbol)
            _fallback_prices[symbol] = fallback_price
            return fallback_price

        return None
