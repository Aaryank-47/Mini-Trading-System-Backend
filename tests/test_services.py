"""
Unit tests for Service layer (business logic)
Tests the core trading logic without HTTP layer
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP
from app.services.order_service import OrderService
from app.services.wallet_service import WalletService
from app.services.position_service import PositionService
from app.services.user_service import UserService
from app.schemas import OrderCreate
from app.models import OrderSide


class TestWalletService:
    """Test wallet operations"""
    
    def test_deduct_balance_success(self, db, test_user):
        """Test successful balance deduction"""
        initial_balance = test_user.wallet.balance
        amount = Decimal("1000.00")
        
        WalletService.deduct_balance(db, test_user.id, amount)
        
        db.refresh(test_user.wallet)
        assert test_user.wallet.balance == initial_balance - amount
    
    def test_deduct_balance_insufficient_funds(self, db, test_user):
        """Test deduction with insufficient funds"""
        # Try to deduct more than balance
        result = WalletService.deduct_balance(db, test_user.id, Decimal("999999999999.00"))
        assert result is False
    
    def test_add_balance_success(self, db, test_user):
        """Test successful balance addition"""
        initial_balance = test_user.wallet.balance
        amount = Decimal("500.00")
        
        WalletService.add_balance(db, test_user.id, amount)
        
        db.refresh(test_user.wallet)
        assert test_user.wallet.balance == initial_balance + amount
    
    def test_decimal_precision(self, db, test_user):
        """Test Decimal precision (not float)"""
        # Test the classic 0.1 + 0.2 ≠ 0.3 problem
        amount1 = Decimal("0.1")
        amount2 = Decimal("0.2")
        
        WalletService.deduct_balance(db, test_user.id, amount1)
        WalletService.deduct_balance(db, test_user.id, amount2)
        
        db.refresh(test_user.wallet)
        # Should be exactly 0.3, not 0.30000000000000004
        expected = Decimal("1000000.00") - Decimal("0.3")
        assert test_user.wallet.balance == expected


class TestPositionService:
    """Test position management"""
    
    def test_calculate_weighted_average_price(self, db, test_user):
        """Test weighted average price calculation"""
        symbol = "SBIN"
        
        # First purchase: 100 @ 500
        PositionService.update_position_on_buy(db, test_user.id, symbol, 100, Decimal("500.00"))
        
        # Second purchase: 50 @ 510
        PositionService.update_position_on_buy(db, test_user.id, symbol, 50, Decimal("510.00"))
        
        position = PositionService.get_position(db, test_user.id, symbol)
        
        # Expected: (100*500 + 50*510) / 150 = 503.333...
        expected_avg = Decimal("503.33")  # Rounded to 2 decimals
        assert abs(position.average_price - expected_avg) < Decimal("0.01")
    
    def test_position_deletion_on_zero_quantity(self, db, test_user):
        """Test position is deleted when quantity becomes 0"""
        symbol = "SBIN"
        
        # Buy 100 shares
        PositionService.update_position_on_buy(db, test_user.id, symbol, 100, Decimal("500.00"))
        
        # Sell all 100 shares
        PositionService.update_position_on_sell(db, test_user.id, symbol, 100)
        
        # Position should be deleted
        position = PositionService.get_position(db, test_user.id, symbol)
        assert position is None


class TestOrderService:
    """Test order execution logic"""
    
    def test_execute_buy_order(self, db, test_user):
        """Test BUY order execution"""
        order_data = OrderCreate(
            user_id=test_user.id,
            symbol="SBIN",
            qty=100,
            side="BUY"
        )
        
        initial_balance = test_user.wallet.balance
        order = OrderService.execute_order(db, order_data)
        
        assert order is not None
        assert order.side == OrderSide.BUY
        # Balance should be reduced (depends on price)
        db.refresh(test_user.wallet)
        assert test_user.wallet.balance < initial_balance
    
    def test_execute_sell_order_insufficient_quantity(self, db, test_user):
        """Test SELL order fails with insufficient quantity"""
        order_data = OrderCreate(
            user_id=test_user.id,
            symbol="SBIN",
            qty=1000,  # Don't have this many
            side="SELL"
        )
        
        with pytest.raises(ValueError):
            OrderService.execute_order(db, order_data)
    
    def test_atomic_transaction_rollback(self, db, test_user):
        """Test transaction rollback on error"""
        initial_balance = test_user.wallet.balance
        
        # Try to buy more shares than can afford
        order_data = OrderCreate(
            user_id=test_user.id,
            symbol="SBIN",
            qty=10000000,  # Extremely large amount
            side="BUY"
        )
        
        try:
            OrderService.execute_order(db, order_data)
        except (ValueError, Exception):
            pass
        
        # Balance should be unchanged (transaction rolled back)
        db.refresh(test_user.wallet)
        assert test_user.wallet.balance == initial_balance


class TestUserService:
    """Test user management"""
    
    def test_create_user_with_wallet(self, db):
        """Test that wallet is created with user"""
        from app.schemas import UserCreate
        user_data = UserCreate(name="New User", email="newuser@example.com")
        user = UserService.create_user(db, user_data)
        
        assert user.wallet is not None
        assert user.wallet.balance == Decimal("1000000.00")
    
    def test_get_user(self, db, test_user):
        """Test getting user by ID"""
        user = UserService.get_user(db, test_user.id)
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
