#!/usr/bin/env python3
"""
Seed script for populating the stocks table with master data.
This script is idempotent and safe to run multiple times.
Run from project root: python scripts/seed_stocks.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Stock
from app.services.stock_service import StockService

# Stock master data - extracted from original SYMBOL_CATALOG
STOCK_SEED_DATA = [
    {"symbol": "SBIN", "company_name": "State Bank of India", "min_price": 550, "max_price": 750},
    {"symbol": "RELI", "company_name": "Reliance Industries", "min_price": 2200, "max_price": 3200},
    {"symbol": "TCS", "company_name": "Tata Consultancy Services", "min_price": 3200, "max_price": 4500},
    {"symbol": "INFY", "company_name": "Infosys", "min_price": 1300, "max_price": 2100},
    {"symbol": "HDFC", "company_name": "HDFC Bank", "min_price": 1400, "max_price": 1900},
    {"symbol": "ICIC", "company_name": "ICICI Bank", "min_price": 900, "max_price": 1300},
    {"symbol": "ITC", "company_name": "ITC Limited", "min_price": 350, "max_price": 550},
    {"symbol": "LT", "company_name": "Larsen & Toubro", "min_price": 3000, "max_price": 4800},
    {"symbol": "AXIS", "company_name": "Axis Bank", "min_price": 950, "max_price": 1400},
    {"symbol": "KOTK", "company_name": "Kotak Mahindra Bank", "min_price": 1600, "max_price": 2200},
    {"symbol": "BAJF", "company_name": "Bajaj Finance", "min_price": 6000, "max_price": 8000},
    {"symbol": "HUNI", "company_name": "Hindustan Unilever", "min_price": 2200, "max_price": 3000},
    {"symbol": "ASPA", "company_name": "Asian Paints", "min_price": 2800, "max_price": 3600},
    {"symbol": "MRTI", "company_name": "Maruti Suzuki", "min_price": 9000, "max_price": 13000},
    {"symbol": "SUNP", "company_name": "Sun Pharmaceutical Industries", "min_price": 1400, "max_price": 1900},
    {"symbol": "TITN", "company_name": "Titan Company", "min_price": 3000, "max_price": 4200},
    {"symbol": "NEST", "company_name": "Nestle India", "min_price": 2200, "max_price": 2800},
    {"symbol": "WIPR", "company_name": "Wipro", "min_price": 450, "max_price": 800},
    {"symbol": "TECH", "company_name": "Tech Mahindra", "min_price": 1200, "max_price": 1800},
    {"symbol": "ULTR", "company_name": "UltraTech Cement", "min_price": 9000, "max_price": 12000},
    {"symbol": "ADEN", "company_name": "Adani Enterprises", "min_price": 2500, "max_price": 3500},
    {"symbol": "ADPO", "company_name": "Adani Ports", "min_price": 900, "max_price": 1500},
    {"symbol": "PWRG", "company_name": "Power Grid Corporation", "min_price": 250, "max_price": 400},
    {"symbol": "NTPC", "company_name": "NTPC Limited", "min_price": 300, "max_price": 450},
    {"symbol": "ONGC", "company_name": "Oil and Natural Gas Corporation", "min_price": 250, "max_price": 400},
    {"symbol": "COAL", "company_name": "Coal India", "min_price": 350, "max_price": 550},
    {"symbol": "TSTE", "company_name": "Tata Steel", "min_price": 100, "max_price": 180},
    {"symbol": "BFSV", "company_name": "Bajaj Finserv", "min_price": 1500, "max_price": 2200},
    {"symbol": "SBLI", "company_name": "SBI Life Insurance", "min_price": 1200, "max_price": 1800},
    {"symbol": "INDB", "company_name": "IndusInd Bank", "min_price": 1300, "max_price": 1800},
    {"symbol": "HCLT", "company_name": "HCL Technologies", "min_price": 1200, "max_price": 1900},
    {"symbol": "GRAS", "company_name": "Grasim Industries", "min_price": 1800, "max_price": 2800},
    {"symbol": "JSWS", "company_name": "JSW Steel", "min_price": 700, "max_price": 1200},
    {"symbol": "BPCL", "company_name": "Bharat Petroleum", "min_price": 450, "max_price": 700},
    {"symbol": "DRRD", "company_name": "Dr. Reddy's Laboratories", "min_price": 4800, "max_price": 6500},
    {"symbol": "DIVI", "company_name": "Divi's Laboratories", "min_price": 3000, "max_price": 4300},
    {"symbol": "CIPL", "company_name": "Cipla", "min_price": 1200, "max_price": 1800},
    {"symbol": "EICH", "company_name": "Eicher Motors", "min_price": 3000, "max_price": 5000},
    {"symbol": "SHRI", "company_name": "Shriram Finance", "min_price": 2500, "max_price": 3800},
    {"symbol": "TTMO", "company_name": "Tata Motors", "min_price": 800, "max_price": 1300},
    {"symbol": "APOL", "company_name": "Apollo Hospitals", "min_price": 5000, "max_price": 7000},
    {"symbol": "MNM", "company_name": "Mahindra & Mahindra", "min_price": 2500, "max_price": 3800},
    {"symbol": "BRIT", "company_name": "Britannia Industries", "min_price": 4300, "max_price": 6000},
    {"symbol": "HERO", "company_name": "Hero MotoCorp", "min_price": 3500, "max_price": 5500},
    {"symbol": "TCON", "company_name": "Tata Consumer Products", "min_price": 800, "max_price": 1200},
    {"symbol": "HIND", "company_name": "Hindalco Industries", "min_price": 500, "max_price": 900},
    {"symbol": "UPL", "company_name": "UPL Limited", "min_price": 450, "max_price": 750},
    {"symbol": "VEDL", "company_name": "Vedanta", "min_price": 350, "max_price": 600},
    {"symbol": "BOSC", "company_name": "Bosch Limited", "min_price": 25000, "max_price": 35000},
    {"symbol": "LTIM", "company_name": "LTIMindtree", "min_price": 4500, "max_price": 6500},
    {"symbol": "PIDI", "company_name": "Pidilite Industries", "min_price": 2500, "max_price": 3500},
    {"symbol": "ZOMA", "company_name": "Zomato", "min_price": 130, "max_price": 250},
    {"symbol": "DMRT", "company_name": "Avenue Supermarts", "min_price": 3300, "max_price": 4700},
    {"symbol": "LICI", "company_name": "Life Insurance Corporation of India", "min_price": 800, "max_price": 1300},
    {"symbol": "HAVE", "company_name": "Havells India", "min_price": 1300, "max_price": 2000},
]


def create_tables():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")


def seed_stocks(db: Session):
    """Seed stocks into database using StockService (idempotent)"""
    print(f"\nSeeding {len(STOCK_SEED_DATA)} stocks...")
    
    created_stocks = StockService.bulk_seed_stocks(db, STOCK_SEED_DATA)
    
    print(f"✓ Seeded {len(created_stocks)} new stocks")
    
    # Show count of total stocks
    total = db.query(Stock).count()
    active = db.query(Stock).filter(Stock.is_active == True).count()
    print(f"✓ Total stocks in database: {total} (Active: {active})")


def main():
    """Main seed function"""
    print("=" * 60)
    print("Trading System - Stock Master Data Seeder")
    print("=" * 60)
    
    try:
        # Create tables
        create_tables()
        
        # Seed data
        db = SessionLocal()
        try:
            seed_stocks(db)
            print("\n" + "=" * 60)
            print("✓ Seed completed successfully!")
            print("=" * 60)
        finally:
            db.close()
            
    except Exception as e:
        print(f"\n✗ Seed failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
