# Branch: unified-main
# File: tests/test_network_topology.py

import unittest
from unittest.mock import Mock, patch
import socket

from core.config import ConfigManager
from core.device_types import PiDevice
from network.topology import NetworkTopology, TopologyError

class TestNetworkTopology(unittest.TestCase):
    """Test suite for the NetworkTopology class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock ConfigManager
        self.mock_config = Mock(spec=ConfigManager)
        
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
        self.device3 = PiDevice(
            name="device3",
            ip_address="192.168.1.3",
            is_prosumer=True,
            hostname="prosumer-2"
        )
        
        # Add devices to config
        self.mock_config.devices = {
            "device1": self.device1,
            "device2": self.device2,
            "device3": self.device3
        }
        
        # Mock _determine_local_device to avoid socket operations
        with patch.object(NetworkTopology, '_determine_local_device', return_value=self.device1):
            self.topology = NetworkTopology(self.mock_config)
    
    # Modified test methods for NetworkTopology
    @patch('socket.gethostname')
    def test_determine_local_device_by_hostname(self, mock_gethostname):
        """Test determining local device by hostname."""
        # Create a temporary topology with necessary attributes
        self.devices = {
            "device1": self.device1,
            "device2": self.device2,
            "device3": self.device3
        }
        self.logger = Mock()
        mock_gethostname.return_value = "prosumer-1"
        
        # Now call the method on self since we've added the needed attributes
        device = NetworkTopology._determine_local_device(self)
        
        # Assert
        self.assertEqual(device, self.device1)
    
    @patch('socket.gethostname')
    @patch('socket.gethostbyname')
    def test_determine_local_device_by_ip(self, mock_gethostbyname, mock_gethostname):
        """Test determining local device by IP address."""
        # Add the needed attributes
        self.devices = {
            "device1": self.device1, 
            "device2": self.device2,
            "device3": self.device3
        }
        self.logger = Mock()  # Add a mock logger
        
        # Now call the method with correct mock setup
        mock_gethostname.return_value = "unknown-host"
        mock_gethostbyname.return_value = "192.168.1.1"
        
        device = NetworkTopology._determine_local_device(self)
        
        # Assert
        self.assertEqual(device, self.device1)
    
    @patch('socket.gethostname')
    @patch('socket.gethostbyname')
    def test_determine_local_device_not_found(self, mock_gethostbyname, mock_gethostname):
        """Test handling when local device cannot be determined."""
        self.logger = Mock()
        # Arrange
        mock_gethostname.return_value = "unknown-host"
        mock_gethostbyname.return_value = "192.168.1.100"  # Unknown IP
        
        # Act
        device = NetworkTopology._determine_local_device(self)
        
        # Assert
        self.assertIsNone(device)
    
    def test_initialization(self):
        """Test that NetworkTopology initializes correctly."""
        # Assert
        self.assertEqual(self.topology.config, self.mock_config)
        self.assertEqual(self.topology.devices, self.mock_config.devices)
        self.assertEqual(self.topology.local_device, self.device1)
        self.assertEqual(len(self.topology.communication_paths), 3)
    
    def test_initialize_communication_paths(self):
        """Test initialization of communication paths."""
        # Assert
        self.assertEqual(self.topology.communication_paths["device1"], {"device2", "device3"})
        self.assertEqual(self.topology.communication_paths["device2"], {"device1", "device3"})
        self.assertEqual(self.topology.communication_paths["device3"], {"device1", "device2"})
    
    def test_get_local_device(self):
        """Test getting the local device."""
        # Act
        local_device = self.topology.get_local_device()
        
        # Assert
        self.assertEqual(local_device, self.device1)
    
    def test_get_device_by_ip(self):
        """Test getting a device by IP address."""
        # Act
        device = self.topology.get_device_by_ip("192.168.1.2")
        
        # Assert
        self.assertEqual(device, self.device2)
        self.assertIsNone(self.topology.get_device_by_ip("192.168.1.100"))  # Unknown IP
    
    def test_get_device_by_name(self):
        """Test getting a device by name."""
        # Act
        device = self.topology.get_device_by_name("device3")
        
        # Assert
        self.assertEqual(device, self.device3)
        self.assertIsNone(self.topology.get_device_by_name("device4"))  # Unknown device
    
    def test_get_prosumers(self):
        """Test getting all prosumer devices."""
        # Act
        prosumers = self.topology.get_prosumers()
        
        # Assert
        self.assertEqual(len(prosumers), 2)
        self.assertIn(self.device1, prosumers)
        self.assertIn(self.device3, prosumers)
    
    def test_get_consumers(self):
        """Test getting all consumer devices."""
        # Act
        consumers = self.topology.get_consumers()
        
        # Assert
        self.assertEqual(len(consumers), 1)
        self.assertIn(self.device2, consumers)
    
    def test_get_peers(self):
        """Test getting all peers (excluding local device)."""
        # Act
        peers = self.topology.get_peers()
        
        # Assert
        self.assertEqual(len(peers), 2)
        self.assertIn(self.device2, peers)
        self.assertIn(self.device3, peers)
    
    def test_can_communicate(self):
        """Test checking if two devices can communicate."""
        # Act & Assert
        self.assertTrue(self.topology.can_communicate("device1", "device2"))
        self.assertTrue(self.topology.can_communicate("device2", "device3"))
        self.assertFalse(self.topology.can_communicate("device1", "device4"))  # Unknown device
    
    def test_add_device(self):
        """Test adding a new device to the topology."""
        # Arrange
        new_device = PiDevice(
            name="device4",
            ip_address="192.168.1.4",
            is_prosumer=False,
            hostname="consumer-2"
        )
        
        # Act
        self.topology.add_device(new_device)
        
        # Assert
        self.assertIn("device4", self.topology.devices)
        self.assertEqual(self.topology.devices["device4"], new_device)
        self.assertIn("device4", self.topology.communication_paths)
        self.assertEqual(self.topology.communication_paths["device4"], {"device1", "device2", "device3"})
        for path in self.topology.communication_paths.values():
            if path != self.topology.communication_paths["device4"]:
                self.assertIn("device4", path)
    
    def test_remove_device(self):
        """Test removing a device from the topology."""
        # Act
        self.topology.remove_device("device2")
        
        # Assert
        self.assertNotIn("device2", self.topology.devices)
        self.assertNotIn("device2", self.topology.communication_paths)
        for path in self.topology.communication_paths.values():
            self.assertNotIn("device2", path)
    
    def test_get_shortest_path(self):
        """Test finding the shortest path between devices."""
        # Act & Assert
        # For direct communication
        self.assertEqual(self.topology.get_shortest_path("device1", "device2"), ["device1", "device2"])
        
        # For self
        self.assertEqual(self.topology.get_shortest_path("device1", "device1"), ["device1"])
        
        # For unknown device
        with self.assertRaises(TopologyError):
            self.topology.get_shortest_path("device1", "device4")
    
    def test_visualize(self):
        """Test generating a visualization of the network topology."""
        # Act
        visualization = self.topology.visualize()
        
        # Assert
        self.assertIn("nodes", visualization)
        self.assertIn("links", visualization)
        self.assertEqual(len(visualization["nodes"]), 3)
        self.assertEqual(len(visualization["links"]), 3)  # 3 possible links between 3 nodes

if __name__ == '__main__':
    unittest.main()