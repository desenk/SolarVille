# Branch: unified-main
# File: tests/test_trade_verification.py

import unittest
from unittest.mock import Mock
import asyncio
from datetime import datetime, timedelta

from core.trade_types import TradeOffer, TradeRequest, TradeMatch
from simulation.trade_verification import TradeVerificationSystem

class TestTradeVerificationSystem(unittest.TestCase):
    """Test suite for the TradeVerificationSystem class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock TradingManager
        self.mock_trading_manager = Mock()
        
        # Create verification system with mocked trading manager
        self.verification_system = TradeVerificationSystem(self.mock_trading_manager)
        
        # Create sample offers, requests, and matches
        # Valid offer
        self.valid_offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device1",
            amount=2.0,
            min_price=0.08,
            expiry=datetime.now() + timedelta(seconds=30)
        )
        
        # Expired offer
        self.expired_offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device1",
            amount=2.0,
            min_price=0.08,
            expiry=datetime.now() - timedelta(seconds=10)  # Already expired
        )
        
        # Low amount offer
        self.low_amount_offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device1",
            amount=0.5,  # Less than trade amount
            min_price=0.08,
            expiry=datetime.now() + timedelta(seconds=30)
        )
        
        # Valid request
        self.valid_request = TradeRequest(
            timestamp=datetime.now(),
            buyer_id="device2",
            amount=1.0,
            max_price=0.10,
            priority=1
        )
        
        # Valid match
        self.valid_match = TradeMatch(
            offer_id="offer_id",
            request_id="request_id",
            seller_id="device1",
            buyer_id="device2",
            amount=1.0,
            price=0.09
        )
    
    async def async_test_verify_trade_valid(self):
        """Async test helper for verify_trade with valid trade."""
        # Arrange
        self.mock_trading_manager.active_offers = {"offer_id": self.valid_offer}
        self.mock_trading_manager.active_requests = {"request_id": self.valid_request}
        
        # Act
        result = await self.verification_system.verify_trade("match_id", self.valid_match)
        
        # Assert
        self.assertTrue(result)
    
    def test_verify_trade_valid(self):
        """Test verifying a valid trade."""
        asyncio.run(self.async_test_verify_trade_valid())
    
    async def async_test_verify_trade_expired_offer(self):
        """Async test helper for verify_trade with expired offer."""
        # Arrange
        self.mock_trading_manager.active_offers = {"offer_id": self.expired_offer}
        self.mock_trading_manager.active_requests = {"request_id": self.valid_request}
        
        # Act
        result = await self.verification_system.verify_trade("match_id", self.valid_match)
        
        # Assert
        self.assertFalse(result)
    
    def test_verify_trade_expired_offer(self):
        """Test verifying a trade with an expired offer."""
        asyncio.run(self.async_test_verify_trade_expired_offer())
    
    async def async_test_verify_trade_insufficient_amount(self):
        """Async test helper for verify_trade with insufficient offer amount."""
        # Arrange
        self.mock_trading_manager.active_offers = {"offer_id": self.low_amount_offer}
        self.mock_trading_manager.active_requests = {"request_id": self.valid_request}
        
        # Act
        result = await self.verification_system.verify_trade("match_id", self.valid_match)
        
        # Assert
        self.assertFalse(result)
    
    def test_verify_trade_insufficient_amount(self):
        """Test verifying a trade with insufficient offer amount."""
        asyncio.run(self.async_test_verify_trade_insufficient_amount())
    
    async def async_test_verify_trade_missing_offer(self):
        """Async test helper for verify_trade with missing offer."""
        # Arrange
        self.mock_trading_manager.active_offers = {}  # No offers
        self.mock_trading_manager.active_requests = {"request_id": self.valid_request}
        
        # Act
        result = await self.verification_system.verify_trade("match_id", self.valid_match)
        
        # Assert
        self.assertFalse(result)
    
    def test_verify_trade_missing_offer(self):
        """Test verifying a trade with a missing offer."""
        asyncio.run(self.async_test_verify_trade_missing_offer())
    
    async def async_test_verify_trade_missing_request(self):
        """Async test helper for verify_trade with missing request."""
        # Arrange
        self.mock_trading_manager.active_offers = {"offer_id": self.valid_offer}
        self.mock_trading_manager.active_requests = {}  # No requests
        
        # Act
        result = await self.verification_system.verify_trade("match_id", self.valid_match)
        
        # Assert
        self.assertFalse(result)
    
    def test_verify_trade_missing_request(self):
        """Test verifying a trade with a missing request."""
        asyncio.run(self.async_test_verify_trade_missing_request())
    
    async def async_test_verify_trade_price_mismatch(self):
        """Async test helper for verify_trade with price mismatch."""
        # Arrange
        # Create a match with price outside acceptable range
        mismatch_match = TradeMatch(
            offer_id="offer_id",
            request_id="request_id",
            seller_id="device1",
            buyer_id="device2",
            amount=1.0,
            price=0.15  # Higher than max_price of 0.10
        )
        
        self.mock_trading_manager.active_offers = {"offer_id": self.valid_offer}
        self.mock_trading_manager.active_requests = {"request_id": self.valid_request}
        
        # Act
        result = await self.verification_system.verify_trade("match_id", mismatch_match)
        
        # Assert
        self.assertFalse(result)
    
    def test_verify_trade_price_mismatch(self):
        """Test verifying a trade with mismatched price."""
        asyncio.run(self.async_test_verify_trade_price_mismatch())
    
    async def async_test_verify_trade_seller_buyer_mismatch(self):
        """Async test helper for verify_trade with seller/buyer mismatch."""
        # Arrange
        # Create a match with incorrect seller/buyer
        mismatch_match = TradeMatch(
            offer_id="offer_id",
            request_id="request_id",
            seller_id="wrong_seller",  # Doesn't match the offer's seller_id
            buyer_id="device2",
            amount=1.0,
            price=0.09
        )
        
        self.mock_trading_manager.active_offers = {"offer_id": self.valid_offer}
        self.mock_trading_manager.active_requests = {"request_id": self.valid_request}
        
        # Act
        result = await self.verification_system.verify_trade("match_id", mismatch_match)
        
        # Assert
        self.assertFalse(result)
    
    def test_verify_trade_seller_buyer_mismatch(self):
        """Test verifying a trade with mismatched seller/buyer."""
        asyncio.run(self.async_test_verify_trade_seller_buyer_mismatch())

if __name__ == '__main__':
    unittest.main()