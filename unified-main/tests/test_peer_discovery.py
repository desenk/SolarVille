# Branch: unified-main
# File: tests/test_peer_discovery.py

import unittest
from unittest.mock import Mock, patch, call
import time
import threading

from core.config import ConfigManager
from core.device_types import PiDevice
from network.network_manager import NetworkManager
from network.peer_discovery import PeerDiscovery

class TestPeerDiscovery(unittest.TestCase):
    """Test suite for the PeerDiscovery class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
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
        
        # Mock get_local_device to return device1
        self.mock_config.get_local_device.return_value = self.device1
        
        # Create PeerDiscovery with mocked dependencies
        self.peer_discovery = PeerDiscovery(self.mock_config, self.mock_network_manager)
        
        # Reduce discovery interval for faster tests
        self.peer_discovery.discovery_interval = 0.1
    
    def test_initialization(self):
        """Test that PeerDiscovery initializes correctly."""
        # Assert
        self.assertEqual(self.peer_discovery.config, self.mock_config)
        self.assertEqual(self.peer_discovery.network_manager, self.mock_network_manager)
        self.assertEqual(self.peer_discovery.known_peers, self.mock_config.devices)
        self.assertEqual(self.peer_discovery.discovered_peers, {})
        self.assertEqual(self.peer_discovery.peer_status, {})
        self.assertFalse(self.peer_discovery.discovery_active)
        self.assertIsNone(self.peer_discovery.discovery_thread)
    
    def test_start_discovery(self):
        """Test starting peer discovery process."""
        # Act
        self.peer_discovery.start_discovery()
        
        # Assert
        self.assertTrue(self.peer_discovery.discovery_active)
        self.assertIsNotNone(self.peer_discovery.discovery_thread)
        self.assertTrue(self.peer_discovery.discovery_thread.is_alive())
        
        # Cleanup
        self.peer_discovery.stop_discovery()
    
    def test_stop_discovery(self):
        """Test stopping peer discovery process."""
        # Arrange
        self.peer_discovery.start_discovery()
        self.assertTrue(self.peer_discovery.discovery_active)
        
        # Act
        self.peer_discovery.stop_discovery()
        
        # Assert
        self.assertFalse(self.peer_discovery.discovery_active)
        self.assertIsNone(self.peer_discovery.discovery_thread)
    
    def test_check_known_peers(self):
        """Test checking known peers."""
        # Arrange
        # Mock response for healthy peer
        self.mock_network_manager.send_request.return_value = {"status": "healthy"}
        
        # Act
        self.peer_discovery._check_known_peers()
        
        # Assert
        # Should check device2 only (since device1 is local)
        self.mock_network_manager.send_request.assert_called_once_with(
            peer=self.device2,
            endpoint="/health",
            timeout=2.0
        )
        self.assertTrue(self.peer_discovery.peer_status.get(self.device2.ip_address, False))
        self.assertIn(self.device2.ip_address, self.peer_discovery.discovered_peers)
    
    def test_check_known_peers_unhealthy(self):
        """Test checking known peers that are unhealthy."""
        # Arrange
        # Mock unhealthy response
        self.mock_network_manager.send_request.return_value = {"error": "connection_failed"}
        
        # Act
        self.peer_discovery._check_known_peers()
        
        # Assert
        self.assertFalse(self.peer_discovery.peer_status.get(self.device2.ip_address, True))
    
    def test_check_potential_peer(self):
        """Test checking a potential peer."""
        # Arrange
        # Mock responses for health and peer info
        mock_responses = [
            {"status": "healthy"},  # Health check
            {"name": "device3", "is_prosumer": True, "hostname": "prosumer-2"}  # Peer info
        ]
        self.mock_network_manager.send_request.side_effect = mock_responses
        
        # Act
        self.peer_discovery._check_potential_peer("192.168.1.3")
        
        # Assert
        self.assertEqual(len(self.mock_network_manager.send_request.call_args_list), 2)
        self.assertIn("192.168.1.3", self.peer_discovery.discovered_peers)
        self.assertEqual(self.peer_discovery.discovered_peers["192.168.1.3"].name, "device3")
        self.assertTrue(self.peer_discovery.discovered_peers["192.168.1.3"].is_prosumer)
        self.assertTrue(self.peer_discovery.peer_status.get("192.168.1.3", False))
    
    def test_check_potential_peer_minimal_info(self):
        """Test checking a potential peer with minimal info."""
        # Arrange
        # Mock response for health check
        self.mock_network_manager.send_request.side_effect = [
            {"status": "healthy"},  # Health check
            {"error": "not_implemented"}  # Peer info fails
        ]
        
        # Act
        self.peer_discovery._check_potential_peer("192.168.1.3")
        
        # Assert
        self.assertIn("192.168.1.3", self.peer_discovery.discovered_peers)
        self.assertTrue(self.peer_discovery.peer_status.get("192.168.1.3", False))
        # Should have a default name based on IP
        self.assertTrue(self.peer_discovery.discovered_peers["192.168.1.3"].name.startswith("unknown"))
    
    def test_check_potential_peer_error(self):
        """Test handling errors when checking a potential peer."""
        # Arrange
        self.mock_network_manager.send_request.side_effect = Exception("Test error")
        
        # Act
        self.peer_discovery._check_potential_peer("192.168.1.3")
        
        # Assert
        self.assertNotIn("192.168.1.3", self.peer_discovery.discovered_peers)
        self.assertFalse(self.peer_discovery.peer_status.get("192.168.1.3", False))
    
    def test_verify_all_peers(self):
        """Test verifying all discovered peers."""
        # Arrange
        # Add some discovered peers
        self.peer_discovery.discovered_peers = {
            "192.168.1.2": self.device2,
            "192.168.1.3": PiDevice(
                name="device3",
                ip_address="192.168.1.3",
                is_prosumer=True,
                hostname="prosumer-2"
            )
        }
        
        # Mock healthy responses for both peers
        self.mock_network_manager.send_request.return_value = {"status": "healthy"}
        
        # Act
        self.peer_discovery._verify_all_peers()
        
        # Assert
        self.assertEqual(self.mock_network_manager.send_request.call_count, 2)
        self.assertTrue(all(self.peer_discovery.peer_status.values()))
    
    def test_verify_all_peers_mixed_results(self):
        """Test verifying peers with mixed health results."""
        # Arrange
        # Add some discovered peers
        self.peer_discovery.discovered_peers = {
            "192.168.1.2": self.device2,
            "192.168.1.3": PiDevice(
                name="device3",
                ip_address="192.168.1.3",
                is_prosumer=True,
                hostname="prosumer-2"
            )
        }
        
        # Mock responses: healthy for device2, unhealthy for device3
        self.mock_network_manager.send_request.side_effect = [
            {"status": "healthy"},  # device2
            {"error": "connection_failed"}  # device3
        ]
        
        # Act
        self.peer_discovery._verify_all_peers()
        
        # Assert
        self.assertTrue(self.peer_discovery.peer_status.get("192.168.1.2", False))
        self.assertFalse(self.peer_discovery.peer_status.get("192.168.1.3", True))
    
    def test_discovery_loop_integration(self):
        """Test the integration of discovery loop steps."""
        # Mock the component methods
        self.peer_discovery._check_known_peers = Mock()
        self.peer_discovery._discover_local_network_peers = Mock()
        self.peer_discovery._verify_all_peers = Mock()
        self.peer_discovery._update_peer_availability = Mock()
        
        # Start discovery
        self.peer_discovery.start_discovery()
        
        # Let it run for a bit
        time.sleep(0.3)  # Should allow for at least 2 discovery cycles
        
        # Stop discovery
        self.peer_discovery.stop_discovery()
        
        # Assert each component was called at least twice
        self.assertGreaterEqual(self.peer_discovery._check_known_peers.call_count, 2)
        self.assertGreaterEqual(self.peer_discovery._discover_local_network_peers.call_count, 2)
        self.assertGreaterEqual(self.peer_discovery._verify_all_peers.call_count, 2)
        self.assertGreaterEqual(self.peer_discovery._update_peer_availability.call_count, 2)
    
    def test_discovery_loop_error_handling(self):
        """Test error handling in the discovery loop."""
        # Make _check_known_peers raise an exception
        self.peer_discovery._check_known_peers = Mock(side_effect=Exception("Test error"))
        self.peer_discovery._discover_local_network_peers = Mock()
        
        # Start discovery
        self.peer_discovery.start_discovery()
        
        # Let it run for a bit
        time.sleep(0.3)  # Should allow for at least 2 discovery cycles
        
        # Stop discovery
        self.peer_discovery.stop_discovery()
        
        # Assert _check_known_peers was called multiple times despite errors
        self.assertGreaterEqual(self.peer_discovery._check_known_peers.call_count, 2)
        
        # _discover_local_network_peers should never be called due to early error
        self.peer_discovery._discover_local_network_peers.assert_not_called()
    
    def test_get_available_peers(self):
        """Test getting available peers."""
        # Arrange
        self.peer_discovery.discovered_peers = {
            "192.168.1.2": self.device2,
            "192.168.1.3": PiDevice(
                name="device3",
                ip_address="192.168.1.3",
                is_prosumer=True,
                hostname="prosumer-2"
            )
        }
        self.peer_discovery.peer_status = {
            "192.168.1.2": True,
            "192.168.1.3": False
        }
        
        # Act
        available_peers = self.peer_discovery.get_available_peers()
        
        # Assert
        self.assertEqual(len(available_peers), 1)
        self.assertEqual(available_peers[0].name, "device2")
    
    def test_get_available_prosumers(self):
        """Test getting available prosumer peers."""
        # Arrange
        self.peer_discovery.discovered_peers = {
            "192.168.1.2": self.device2,  # Consumer
            "192.168.1.3": PiDevice(
                name="device3",
                ip_address="192.168.1.3",
                is_prosumer=True,
                hostname="prosumer-2"
            )
        }
        self.peer_discovery.peer_status = {
            "192.168.1.2": True,
            "192.168.1.3": True
        }
        
        # Act
        available_prosumers = self.peer_discovery.get_available_prosumers()
        
        # Assert
        self.assertEqual(len(available_prosumers), 1)
        self.assertEqual(available_prosumers[0].name, "device3")
        self.assertTrue(available_prosumers[0].is_prosumer)
    
    def test_get_available_consumers(self):
        """Test getting available consumer peers."""
        # Arrange
        self.peer_discovery.discovered_peers = {
            "192.168.1.2": self.device2,  # Consumer
            "192.168.1.3": PiDevice(
                name="device3",
                ip_address="192.168.1.3",
                is_prosumer=True,
                hostname="prosumer-2"
            )
        }
        self.peer_discovery.peer_status = {
            "192.168.1.2": True,
            "192.168.1.3": True
        }
        
        # Act
        available_consumers = self.peer_discovery.get_available_consumers()
        
        # Assert
        self.assertEqual(len(available_consumers), 1)
        self.assertEqual(available_consumers[0].name, "device2")
        self.assertFalse(available_consumers[0].is_prosumer)
    
    def test_is_peer_available(self):
        """Test checking if a specific peer is available."""
        # Arrange
        self.peer_discovery.discovered_peers = {
            "192.168.1.2": self.device2
        }
        self.peer_discovery.peer_status = {
            "192.168.1.2": True
        }
        
        # Act & Assert
        self.assertTrue(self.peer_discovery.is_peer_available("device2"))  # By name
        self.assertTrue(self.peer_discovery.is_peer_available("192.168.1.2"))  # By IP
        self.assertFalse(self.peer_discovery.is_peer_available("device3"))  # Unknown name
        self.assertFalse(self.peer_discovery.is_peer_available("192.168.1.3"))  # Unknown IP

if __name__ == '__main__':
    unittest.main()