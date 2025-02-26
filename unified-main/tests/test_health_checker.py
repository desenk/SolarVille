# Branch: unified-main
# File: tests/test_health_checker.py

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import time
import threading

from core.config import ConfigManager
from core.device_types import PiDevice
from network.network_manager import NetworkManager
from network.health_check import HealthChecker

class TestHealthChecker(unittest.TestCase):
    """Test suite for the HealthChecker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock config and network manager
        self.mock_config = Mock(spec=ConfigManager)
        self.mock_network_manager = Mock(spec=NetworkManager)
        
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
        
        # Mock NetworkManager.send_request
        self.mock_network_manager.send_request.return_value = {"status": "healthy"}
        
        # Mock get_local_device to return device1
        self.mock_config.get_local_device.return_value = self.device1
        
        # Create HealthChecker with mocked dependencies
        self.health_checker = HealthChecker(self.mock_config, self.mock_network_manager)
        
        # Reduce check interval for faster tests
        self.health_checker.check_interval = 0.1
    
    def test_initialization(self):
        """Test that HealthChecker initializes correctly."""
        # Assert
        self.assertEqual(self.health_checker.config, self.mock_config)
        self.assertEqual(self.health_checker.network_manager, self.mock_network_manager)
        self.assertEqual(self.health_checker.health_status, {})
        self.assertEqual(self.health_checker.last_check_time, {})
        self.assertFalse(self.health_checker.checking_active)
        self.assertIsNone(self.health_checker.check_thread)
    
    def test_start_checking(self):
        """Test starting health checking process."""
        # Act
        self.health_checker.start_checking()
        
        # Assert
        self.assertTrue(self.health_checker.checking_active)
        self.assertIsNotNone(self.health_checker.check_thread)
        self.assertTrue(self.health_checker.check_thread.is_alive())
        
        # Cleanup
        self.health_checker.stop_checking()
    
    def test_stop_checking(self):
        """Test stopping health checking process."""
        # Arrange
        self.health_checker.start_checking()
        self.assertTrue(self.health_checker.checking_active)
        
        # Act
        self.health_checker.stop_checking()
        
        # Assert
        self.assertFalse(self.health_checker.checking_active)
        self.assertIsNone(self.health_checker.check_thread)
    
    def test_check_peer(self):
        """Test checking health of a specific peer."""
        # Arrange
        self.mock_network_manager.send_request.return_value = {"status": "healthy"}
        
        # Act
        self.health_checker._check_peer(self.device2)
        
        # Assert
        self.mock_network_manager.send_request.assert_called_with(
            peer=self.device2,
            endpoint="/health",
            timeout=2.0,
            critical=False
        )
        self.assertTrue(self.health_checker.health_status[self.device2.ip_address])
        self.assertIn(self.device2.ip_address, self.health_checker.last_check_time)
    
    def test_check_peer_unhealthy(self):
        """Test checking health of an unhealthy peer."""
        # Arrange
        self.mock_network_manager.send_request.return_value = {"error": "connection_failed"}
        
        # Act
        self.health_checker._check_peer(self.device2)
        
        # Assert
        self.assertFalse(self.health_checker.health_status[self.device2.ip_address])
    
    def test_check_peer_error(self):
        """Test handling exceptions when checking peer health."""
        # Arrange
        self.mock_network_manager.send_request.side_effect = Exception("Test error")
        
        # Act
        self.health_checker._check_peer(self.device2)
        
        # Assert
        self.assertFalse(self.health_checker.health_status.get(self.device2.ip_address, True))
    
    def test_check_all_peers(self):
        """Test checking health of all peers."""
        # Act
        self.health_checker._check_all_peers()
        
        # Assert
        # Should only check device2 since device1 is local
        self.mock_network_manager.send_request.assert_called_once()
        self.assertEqual(
            self.mock_network_manager.send_request.call_args[1]['peer'], 
            self.device2
        )
    
    def test_check_peer_now(self):
        """Test immediately checking a peer's health."""
        # Act
        result = self.health_checker.check_peer_now(self.device2)
        
        # Assert
        self.assertTrue(result)
        self.assertTrue(self.health_checker.health_status[self.device2.ip_address])
        self.assertIn(self.device2.ip_address, self.health_checker.last_check_time)
    
    def test_is_peer_healthy(self):
        """Test checking if a peer is healthy."""
        # Arrange
        self.health_checker.health_status = {
            "192.168.1.1": True,
            "192.168.1.2": False
        }
        
        # Act & Assert
        self.assertTrue(self.health_checker.is_peer_healthy("192.168.1.1"))
        self.assertFalse(self.health_checker.is_peer_healthy("192.168.1.2"))
        self.assertFalse(self.health_checker.is_peer_healthy("192.168.1.3"))  # Unknown peer
    
    def test_get_healthy_peers(self):
        """Test getting list of healthy peers."""
        # Arrange
        self.health_checker.health_status = {
            "192.168.1.1": True,
            "192.168.1.2": False
        }
        
        # Act
        healthy_peers = self.health_checker.get_healthy_peers()
        
        # Assert
        self.assertEqual(len(healthy_peers), 1)
        self.assertEqual(healthy_peers[0].name, "device1")
    
    def test_get_unhealthy_peers(self):
        """Test getting list of unhealthy peers."""
        # Arrange
        self.health_checker.health_status = {
            "192.168.1.1": True,
            "192.168.1.2": False
        }
        
        # Act
        unhealthy_peers = self.health_checker.get_unhealthy_peers()
        
        # Assert
        self.assertEqual(len(unhealthy_peers), 1)
        self.assertEqual(unhealthy_peers[0].name, "device2")
    
    def test_status_change_notification(self):
        """Test notification of status changes."""
        # Arrange
        callback = Mock()
        self.health_checker.register_status_change_callback(
            self.device2.ip_address, callback
        )
        
        # First check - status becomes healthy
        self.mock_network_manager.send_request.return_value = {"status": "healthy"}
        self.health_checker._check_peer(self.device2)
        
        # Assert callback was called with healthy status
        callback.assert_called_once_with(self.device2.ip_address, True)
        callback.reset_mock()
        
        # Second check - status becomes unhealthy
        self.mock_network_manager.send_request.return_value = {"error": "connection_failed"}
        self.health_checker._check_peer(self.device2)
        
        # Assert callback was called with unhealthy status
        callback.assert_called_once_with(self.device2.ip_address, False)
        
    def test_check_loop(self):
        """Test the main health check loop functionality."""
        # Mock _check_all_peers to track calls
        self.health_checker._check_all_peers = Mock()
        
        # Start health checking
        self.health_checker.start_checking()
        
        # Let it run for a bit
        time.sleep(0.3)  # Should allow for at least 2 check cycles
        
        # Stop health checking
        self.health_checker.stop_checking()
        
        # Assert _check_all_peers was called at least twice
        self.assertGreaterEqual(self.health_checker._check_all_peers.call_count, 2)
        
    def test_check_loop_error_handling(self):
        """Test error handling in the health check loop."""
        # Make _check_all_peers raise an exception
        self.health_checker._check_all_peers = Mock(side_effect=Exception("Test error"))
        
        # Start health checking
        self.health_checker.start_checking()
        
        # Let it run for a bit
        time.sleep(0.3)  # Should allow for at least 2 check cycles
        
        # Stop health checking
        self.health_checker.stop_checking()
        
        # Assert _check_all_peers was called at least twice (loop continues despite errors)
        self.assertGreaterEqual(self.health_checker._check_all_peers.call_count, 2)

if __name__ == '__main__':
    unittest.main()