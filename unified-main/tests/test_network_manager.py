# Branch: unified-main
# File: tests/test_network_manager.py

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError

from core.config import ConfigManager
from core.device_types import PiDevice
from network.network_manager import NetworkManager, NetworkError, TimeoutError, ConnectionFailedError

class TestNetworkManager(unittest.TestCase):
    """Test suite for the NetworkManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock ConfigManager
        self.mock_config = Mock(spec=ConfigManager)
        self.mock_config.retry_attempts = 3
        self.mock_config.timeout_seconds = 2
        self.mock_config.server_port = 5000
        
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
        
        # Set devices in config
        self.mock_config.devices = {
            "device1": self.device1,
            "device2": self.device2
        }
        
        # Mock get_local_device to return device1
        self.mock_config.get_local_device.return_value = self.device1
        
        # Create NetworkManager with mocked config
        self.network_manager = NetworkManager(self.mock_config)
        
        # Replace the real session with a mock
        self.mock_session = Mock()
        self.network_manager.session = self.mock_session
    
    @patch('requests.Session')
    def test_initialization(self, mock_session_class):
        """Test that NetworkManager initializes correctly."""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Act
        network_manager = NetworkManager(self.mock_config)
        
        # Assert
        self.assertEqual(network_manager.config, self.mock_config)
        self.assertEqual(
            set(network_manager.peer_status.keys()), 
            {"192.168.1.1", "192.168.1.2"}
        )
        self.assertFalse(all(network_manager.peer_status.values()))
    
    def test_send_request_success(self):
        """Test successful request sending."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "data": "test"}
        self.mock_session.get.return_value = mock_response
        
        # Act
        result = self.network_manager.send_request(
            peer=self.device2,
            endpoint="/test",
            method="GET"
        )
        
        # Assert
        self.mock_session.get.assert_called_once_with(
            "http://192.168.1.2:5000/test",
            timeout=2
        )
        self.assertEqual(result, {"status": "success", "data": "test"})
        self.assertTrue(self.network_manager.peer_status[self.device2.ip_address])
    
    def test_send_request_post(self):
        """Test POST request sending."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        self.mock_session.post.return_value = mock_response
        test_data = {"key": "value"}
        
        # Act
        result = self.network_manager.send_request(
            peer=self.device2,
            endpoint="/test",
            method="POST",
            data=test_data
        )
        
        # Assert
        self.mock_session.post.assert_called_once_with(
            "http://192.168.1.2:5000/test",
            json=test_data,
            timeout=2
        )
        self.assertEqual(result, {"status": "success"})
    
    def test_send_request_timeout(self):
        """Test handling of timeout errors."""
        # Arrange
        self.mock_session.get.side_effect = Timeout("Request timed out")
        
        # Act & Assert
        # Non-critical request should not raise an exception
        result = self.network_manager.send_request(
            peer=self.device2,
            endpoint="/test",
            critical=False
        )
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "timeout")
        self.assertFalse(self.network_manager.peer_status[self.device2.ip_address])
        
        # Critical request should raise an exception
        with self.assertRaises(TimeoutError):
            self.network_manager.send_request(
                peer=self.device2,
                endpoint="/test",
                critical=True
            )
    
    def test_send_request_connection_error(self):
        """Test handling of connection errors."""
        # Arrange
        self.mock_session.get.side_effect = ConnectionError("Connection failed")
        
        # Act & Assert
        # Non-critical request should not raise an exception
        result = self.network_manager.send_request(
            peer=self.device2,
            endpoint="/test",
            critical=False
        )
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "connection_failed")
        self.assertFalse(self.network_manager.peer_status[self.device2.ip_address])
        
        # Critical request should raise an exception
        with self.assertRaises(ConnectionFailedError):
            self.network_manager.send_request(
                peer=self.device2,
                endpoint="/test",
                critical=True
            )
    
    def test_broadcast(self):
        """Test broadcasting messages to multiple peers."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        self.mock_session.post.return_value = mock_response
        test_data = {"key": "value"}
        
        # Mock get_local_device to return device2
        self.mock_config.get_local_device.return_value = self.device2
        
        # Act
        results = self.network_manager.broadcast(
            endpoint="/test",
            data=test_data
        )
        
        # Assert
        # Should only send to device1 since device2 is local
        self.mock_session.post.assert_called_once_with(
            "http://192.168.1.1:5000/test",
            json=test_data,
            timeout=2
        )
        self.assertEqual(len(results), 1)
        self.assertIn(self.device1.ip_address, results)
        self.assertEqual(results[self.device1.ip_address], {"status": "success"})
    
    def test_get_peer_data(self):
        """Test getting data from a specific peer."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "data": "test"}
        self.mock_session.get.return_value = mock_response
        
        # Act
        result = self.network_manager.get_peer_data(
            peer=self.device2,
            endpoint="/data"
        )
        
        # Assert
        self.mock_session.get.assert_called_once_with(
            "http://192.168.1.2:5000/data",
            timeout=2
        )
        self.assertEqual(result, {"status": "success", "data": "test"})
    
    def test_sync_timestamp(self):
        """Test timestamp synchronization with peers."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "synced"}
        self.mock_session.post.return_value = mock_response
        
        # Act
        results = self.network_manager.sync_timestamp("2023-01-01T12:00:00")
        
        # Assert
        self.mock_session.post.assert_called()
        self.assertEqual(len(results), 1)
        self.assertTrue(all(results.values()))
    
    def test_run_health_checks(self):
        """Test running health checks on all peers."""
        # Create a more direct mock for testing
        self.network_manager.send_request = Mock(return_value={"status": "healthy"})
        
        # Act
        results = self.network_manager.run_health_checks()
        
        # Assert
        # Expect 1 result (device2) since device1 is local and skipped
        self.assertEqual(len(results), 1)
        self.assertTrue(all(results.values()))
    
    def test_get_online_peers(self):
        """Test getting list of online peers."""
        # Arrange
        self.network_manager.peer_status = {
            "192.168.1.1": True,
            "192.168.1.2": False
        }
        
        # Act
        online_peers = self.network_manager.get_online_peers()
        
        # Assert
        self.assertEqual(len(online_peers), 1)
        self.assertEqual(online_peers[0].name, "device1")
    
    def test_get_offline_peers(self):
        """Test getting list of offline peers."""
        # Arrange
        self.network_manager.peer_status = {
            "192.168.1.1": True,
            "192.168.1.2": False
        }
        
        # Act
        offline_peers = self.network_manager.get_offline_peers()
        
        # Assert
        self.assertEqual(len(offline_peers), 1)
        self.assertEqual(offline_peers[0].name, "device2")

if __name__ == '__main__':
    unittest.main()