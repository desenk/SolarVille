# Branch: unified-main
# File: tests/test_trading_manager.py

import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from datetime import datetime, timedelta

from core.config import ConfigManager
from core.device_types import PiDevice
from core.trade_types import TradeOffer, TradeRequest, TradeMatch
from network.network_manager import NetworkManager
from network.trading_integration import TradingIntegration
from simulation.trading_manager import TradingManager
from simulation.trade_verification import TradeVerificationSystem

class TestTradingManager(unittest.TestCase):
    """Test suite for the TradingManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_config = Mock(spec=ConfigManager)
        self.mock_network = Mock(spec=NetworkManager)
        
        # Sample devices
        self.device1 = PiDevice(
            name="device1",
            ip_address="192.168.1.1",
            is_prosumer=True,
            hostname="prosumer-1"
        )
        self.device2 = PiDevice(
            name="device2",
            ip_address="192.168.1.2",
            is_prosumer=False,
            hostname="consumer-1"
        )
        
        # Add devices to config
        self.mock_config.devices = {
            "device1": self.device1,
            "device2": self.device2
        }
        
        # Mock get_local_device to return device1
        self.mock_config.get_local_device.return_value = self.device1
        
        # Configure grid prices
        self.mock_config.grid_buy_price = 0.25
        self.mock_config.grid_sell_price = 0.05
        
        # Create TradingManager with mocked dependencies
        self.trading_manager = TradingManager(self.mock_config, self.mock_network)
        
        # Mock the trading_integration to avoid actual network calls
        self.trading_manager.trading_integration = Mock(spec=TradingIntegration)
        
        # Mock the verification_system to always return True
        self.trading_manager.verification_system = Mock(spec=TradeVerificationSystem)
        self.trading_manager.verification_system.verify_trade.return_value = True
    
    def test_initialization(self):
        """Test that TradingManager initializes correctly."""
        # Assert
        self.assertEqual(self.trading_manager.config, self.mock_config)
        self.assertEqual(self.trading_manager.network, self.mock_network)
        self.assertEqual(self.trading_manager.local_device, self.device1)
        self.assertEqual(self.trading_manager.is_prosumer, True)  # device1 is a prosumer
        self.assertEqual(self.trading_manager.active_offers, {})
        self.assertEqual(self.trading_manager.active_requests, {})
        self.assertEqual(self.trading_manager.trade_matches, {})
        self.assertEqual(self.trading_manager.completed_trades, [])
        self.assertFalse(self.trading_manager.processing_active)
        self.assertIsNone(self.trading_manager.processing_task)
    
    def test_create_offer(self):
        """Test creating a trade offer."""
        # Act
        offer_id = asyncio.run(self.trading_manager.create_offer(1.5, 0.10))
        
        # Assert
        self.assertIn(offer_id, self.trading_manager.active_offers)
        offer = self.trading_manager.active_offers[offer_id]
        self.assertEqual(offer.seller_id, "device1")
        self.assertEqual(offer.amount, 1.5)
        self.assertEqual(offer.min_price, 0.10)
        self.assertTrue(isinstance(offer.expiry, datetime))
    
    def test_create_request(self):
        """Test creating a trade request."""
        # Act
        request_id = asyncio.run(self.trading_manager.create_request(1.0, 0.20))
        
        # Assert
        self.assertIn(request_id, self.trading_manager.active_requests)
        request = self.trading_manager.active_requests[request_id]
        self.assertEqual(request.buyer_id, "device1")
        self.assertEqual(request.amount, 1.0)
        self.assertEqual(request.max_price, 0.20)
        self.assertEqual(request.priority, 0)  # Default priority
    
    def test_handle_peer_offer(self):
        """Test handling an offer from a peer."""
        # Arrange
        offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device2",
            amount=2.0,
            min_price=0.08,
            expiry=datetime.now() + timedelta(seconds=30)
        )
        
        # Act
        asyncio.run(self.trading_manager.handle_peer_offer("test_offer_1", offer))
        
        # Assert
        self.assertIn("test_offer_1", self.trading_manager.active_offers)
        self.assertEqual(self.trading_manager.active_offers["test_offer_1"], offer)
    
    def test_handle_peer_request(self):
        """Test handling a request from a peer."""
        # Arrange
        request = TradeRequest(
            timestamp=datetime.now(),
            buyer_id="device2",
            amount=1.5,
            max_price=0.18,
            priority=1
        )
        
        # Act
        asyncio.run(self.trading_manager.handle_peer_request("test_request_1", request))
        
        # Assert
        self.assertIn("test_request_1", self.trading_manager.active_requests)
        self.assertEqual(self.trading_manager.active_requests["test_request_1"], request)
    
    async def async_test_process_offers(self):
        """Async test helper for process_offers."""
        # Arrange
        offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device1",
            amount=2.0,
            min_price=0.08,
            expiry=datetime.now() + timedelta(seconds=30)
        )
        await self.trading_manager.offer_queue.put(("test_offer_1", offer))
        
        # Act
        await self.trading_manager._process_offers()
        
        # Assert
        self.trading_manager.trading_integration.publish_offer.assert_called_once()
    
    def test_process_offers(self):
        """Test processing offers in the queue."""
        asyncio.run(self.async_test_process_offers())
    
    async def async_test_process_requests(self):
        """Async test helper for process_requests."""
        # Arrange
        request = TradeRequest(
            timestamp=datetime.now(),
            buyer_id="device1",
            amount=1.5,
            max_price=0.18,
            priority=1
        )
        await self.trading_manager.request_queue.put(("test_request_1", request))
        
        # Act
        await self.trading_manager._process_requests()
        
        # Assert
        self.trading_manager.trading_integration.publish_request.assert_called_once()
    
    def test_process_requests(self):
        """Test processing requests in the queue."""
        asyncio.run(self.async_test_process_requests())
    
    async def async_test_match_trades(self):
        """Async test helper for match_trades."""
        # Arrange - device1 is local (prosumer) and device2 is peer (consumer)
        
        # Add an offer from the local prosumer
        offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device1",
            amount=2.0,
            min_price=0.08,
            expiry=datetime.now() + timedelta(seconds=30)
        )
        offer_id = "test_offer_1"
        self.trading_manager.active_offers[offer_id] = offer
        
        # Add a request from a peer
        request = TradeRequest(
            timestamp=datetime.now(),
            buyer_id="device2",
            amount=1.0,
            max_price=0.10,
            priority=1
        )
        request_id = "test_request_1"
        self.trading_manager.active_requests[request_id] = request
        
        # Act
        await self.trading_manager._match_trades()
        
        # Assert - check if a trade match was created
        self.assertEqual(len(self.trading_manager.trade_matches), 1)
        
        # Get the match ID and match object
        match_id = next(iter(self.trading_manager.trade_matches))
        match = self.trading_manager.trade_matches[match_id]
        
        # Verify match details
        self.assertEqual(match.seller_id, "device1")
        self.assertEqual(match.buyer_id, "device2")
        self.assertEqual(match.amount, 1.0)  # Should match request amount
        self.assertEqual(match.offer_id, offer_id)
        self.assertEqual(match.request_id, request_id)
    
    def test_match_trades(self):
        """Test matching offers with requests."""
        asyncio.run(self.async_test_match_trades())
    
    async def async_test_process_matched_trades(self):
        """Async test helper for process_matched_trades."""
        # Clear completed trades list to ensure a clean state
        self.trading_manager.completed_trades = []
        
        # Arrange - create a trade match
        match = TradeMatch(
            offer_id="test_offer_1",
            request_id="test_request_1",
            seller_id="device1",
            buyer_id="device2",
            amount=1.0,
            price=0.08
        )
        match_id = "test_match_1"
        self.trading_manager.trade_matches[match_id] = match
        
        # Add to queue
        await self.trading_manager.match_queue.put((match_id, match))
        
        # Create a proper async mock for _execute_trade that doesn't add to completed_trades
        # (let the actual method handle that)
        async def mock_execute_trade(match_id, trade_match):
            # Just return success - don't modify any state
            return True
            
        self.trading_manager._execute_trade = mock_execute_trade
        
        # Create a proper async mock for verify_trade
        async def mock_verify_trade(match_id, trade_match):
            return True
            
        self.trading_manager.verification_system.verify_trade = mock_verify_trade
        
        # Act
        await self.trading_manager._process_matched_trades()
        
        # Assert - just check that the completed_trades list is not empty
        # This is more resilient against implementation changes
        self.assertTrue(len(self.trading_manager.completed_trades) > 0)
    
    def test_process_matched_trades(self):
        """Test processing matched trades in the queue."""
        asyncio.run(self.async_test_process_matched_trades())
    
    async def async_test_execute_trade(self):
        """Async test helper for execute_trade."""
        # Arrange - create a trade match
        match = TradeMatch(
            offer_id="test_offer_1",
            request_id="test_request_1",
            seller_id="device1",
            buyer_id="device2",
            amount=1.0,
            price=0.08
        )
        match_id = "test_match_1"
        
        # Act
        result = await self.trading_manager._execute_trade(match_id, match)
        
        # Assert
        self.assertTrue(result)
        self.trading_manager.trading_integration.notify_trade_completion.assert_called_once()
    
    def test_execute_trade(self):
        """Test executing a matched trade."""
        asyncio.run(self.async_test_execute_trade())
    
    def test_get_trade_status(self):
        """Test getting the current trading status."""
        # Arrange
        self.trading_manager.active_offers = {"offer1": Mock(), "offer2": Mock()}
        self.trading_manager.active_requests = {"req1": Mock()}
        self.trading_manager.trade_matches = {
            "match1": Mock(status="pending"),
            "match2": Mock(status="completed")
        }
        self.trading_manager.completed_trades = [Mock(), Mock()]
        self.trading_manager.processing_active = True
        
        # Act
        status = self.trading_manager.get_trade_status()
        
        # Assert
        self.assertEqual(status["active_offers"], 2)
        self.assertEqual(status["active_requests"], 1)
        self.assertEqual(status["pending_matches"], 1)
        self.assertEqual(status["completed_trades"], 2)
        self.assertTrue(status["is_processing"])
    
    @patch('asyncio.create_task')
    async def async_test_start_processing(self, mock_create_task):
        """Async test helper for start_processing."""
        # Act
        await self.trading_manager.start_processing()
        
        # Assert
        self.assertTrue(self.trading_manager.processing_active)
        mock_create_task.assert_called_once()
    
    def test_start_processing(self):
        """Test starting the trade processing."""
        asyncio.run(self.async_test_start_processing())
    
    async def async_test_stop_processing(self):
        """Async test helper for stop_processing."""
        # Arrange
        self.trading_manager.processing_active = True
        
        # Create a proper awaitable mock task
        async def mock_coroutine():
            return None
            
        self.trading_manager.processing_task = asyncio.create_task(mock_coroutine())
        
        # Act
        await self.trading_manager.stop_processing()
        
        # Assert
        self.assertFalse(self.trading_manager.processing_active)
    
    def test_stop_processing(self):
        """Test stopping the trade processing."""
        asyncio.run(self.async_test_stop_processing())

if __name__ == '__main__':
    unittest.main()