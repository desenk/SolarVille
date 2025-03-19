# Branch: unified-main
# File: tests/test_trading_integration.py

import unittest
from unittest.mock import Mock, patch
import asyncio
from datetime import datetime, timedelta

from core.device_types import PiDevice
from core.trade_types import TradeOffer, TradeRequest, TradeMatch
from network.network_manager import NetworkManager
from network.trading_integration import TradingIntegration

class TestTradingIntegration(unittest.TestCase):
    """Test suite for the TradingIntegration class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock NetworkManager
        self.mock_network = Mock(spec=NetworkManager)
        
        # Explicitly add get_device_by_name method to the mock
        self.mock_network.get_device_by_name = Mock()
        
        # Create TradingIntegration with mocked dependencies
        self.trading_integration = TradingIntegration(self.mock_network)
        
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
        
        # Sample trade data
        self.offer = TradeOffer(
            timestamp=datetime.now(),
            seller_id="device1",
            amount=2.0,
            min_price=0.08,
            expiry=datetime.now() + timedelta(seconds=30)
        )
        
        self.request = TradeRequest(
            timestamp=datetime.now(),
            buyer_id="device2",
            amount=1.5,
            max_price=0.18,
            priority=1
        )
        
        self.trade_match = TradeMatch(
            offer_id="test_offer_1",
            request_id="test_request_1",
            seller_id="device1",
            buyer_id="device2",
            amount=1.0,
            price=0.08
        )
    
    async def async_test_publish_offer(self):
        """Async test helper for publish_offer."""
        # Arrange
        self.mock_network.broadcast.return_value = {
            "192.168.1.2": {"status": "success"}
        }
        
        # Act
        result = await self.trading_integration.publish_offer("test_offer_1", self.offer)
        
        # Assert
        self.assertTrue(result)
        self.mock_network.broadcast.assert_called_once()
        broadcast_data = self.mock_network.broadcast.call_args[1]["data"]
        self.assertEqual(broadcast_data["type"], "offer")
        self.assertEqual(broadcast_data["id"], "test_offer_1")
        self.assertEqual(broadcast_data["offer"], self.offer.to_dict())
    
    def test_publish_offer(self):
        """Test publishing an offer to peers."""
        asyncio.run(self.async_test_publish_offer())
    
    async def async_test_publish_request(self):
        """Async test helper for publish_request."""
        # Arrange
        self.mock_network.broadcast.return_value = {
            "192.168.1.1": {"status": "success"}
        }
        
        # Act
        result = await self.trading_integration.publish_request("test_request_1", self.request)
        
        # Assert
        self.assertTrue(result)
        self.mock_network.broadcast.assert_called_once()
        broadcast_data = self.mock_network.broadcast.call_args[1]["data"]
        self.assertEqual(broadcast_data["type"], "request")
        self.assertEqual(broadcast_data["id"], "test_request_1")
        self.assertEqual(broadcast_data["request"], self.request.to_dict())
    
    def test_publish_request(self):
        """Test publishing a request to peers."""
        asyncio.run(self.async_test_publish_request())
    
    async def async_test_notify_trade_completion(self):
        """Async test helper for notify_trade_completion."""
        # Arrange
        self.mock_network.get_device_by_name = Mock(return_value=self.device2)
        self.mock_network.send_request.return_value = {"status": "success"}
        
        # Act
        result = await self.trading_integration.notify_trade_completion(
            "device2", "test_match_1", self.trade_match
        )
        
        # Assert
        self.assertTrue(result)
        self.mock_network.send_request.assert_called_once()
        
        # Check the notification data
        request_data = self.mock_network.send_request.call_args[1]["data"]
        self.assertEqual(request_data["type"], "trade_completion")
        self.assertEqual(request_data["id"], "test_match_1")
        self.assertEqual(request_data["trade"], self.trade_match.to_dict())
    
    def test_notify_trade_completion(self):
        """Test notifying a peer about a completed trade."""
        asyncio.run(self.async_test_notify_trade_completion())
    
    async def async_test_publish_offer_network_error(self):
        """Async test helper for publish_offer with network error."""
        # Arrange
        self.mock_network.broadcast.side_effect = Exception("Network error")
        
        # Act
        result = await self.trading_integration.publish_offer("test_offer_1", self.offer)
        
        # Assert
        self.assertFalse(result)
        self.mock_network.broadcast.assert_called_once()
    
    def test_publish_offer_network_error(self):
        """Test publishing an offer with network error."""
        asyncio.run(self.async_test_publish_offer_network_error())
    
    async def async_test_notify_trade_completion_peer_not_found(self):
        """Async test helper for notify_trade_completion with peer not found."""
        # Arrange
        self.mock_network.get_device_by_name.return_value = None
        
        # Act
        result = await self.trading_integration.notify_trade_completion(
            "unknown_device", "test_match_1", self.trade_match
        )
        
        # Assert
        self.assertFalse(result)
        self.mock_network.send_request.assert_not_called()
    
    def test_notify_trade_completion_peer_not_found(self):
        """Test notifying an unknown peer about a completed trade."""
        asyncio.run(self.async_test_notify_trade_completion_peer_not_found())

if __name__ == '__main__':
    unittest.main()