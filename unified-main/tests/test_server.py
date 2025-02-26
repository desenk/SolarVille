# Branch: unified-main
# File: tests/test_server.py

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import time
import threading
from datetime import datetime
import flask
from flask import Response

from core.config import ConfigManager
from core.device_types import PiDevice
from network.server import Server, ServerError

class TestServer(unittest.TestCase):
    """Test suite for the Server class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock ConfigManager
        self.mock_config = Mock(spec=ConfigManager)
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
        
        # Add devices to config
        self.mock_config.devices = {
            "device1": self.device1,
            "device2": self.device2
        }
        
        # Mock get_local_device to return device1
        self.mock_config.get_local_device.return_value = self.device1
        
        # Create server with mocked config
        self.server = Server(self.mock_config)
        
        # Test client for routes
        self.client = self.server.app.test_client()
        
        # Run app in test mode
        self.server.app.config['TESTING'] = True
    
    def test_initialization(self):
        """Test that Server initializes correctly."""
        # Assert
        self.assertEqual(self.server.config, self.mock_config)
        self.assertIsNotNone(self.server.app)
        self.assertEqual(self.server.peer_data, {})
        self.assertEqual(self.server.trade_data, {})
        self.assertEqual(self.server.simulation_data["status"], "not_started")
        self.assertFalse(self.server.is_running)
        self.assertIsNone(self.server.server_thread)
    
    def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        # Act
        response = self.client.get('/health')
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["device_name"], "device1")
        self.assertTrue(data["is_prosumer"])
    
    def test_peer_info_endpoint(self):
        """Test the peer info endpoint."""
        # Act
        response = self.client.get('/peer_info')
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["name"], "device1")
        self.assertTrue(data["is_prosumer"])
        self.assertEqual(data["hostname"], "prosumer-1")
    
    def test_energy_data_get_endpoint(self):
        """Test getting energy data."""
        # Arrange
        self.server.peer_data = {
            "192.168.1.2": {
                "timestamp": "2023-01-01T12:00:00",
                "demand": 1.5,
                "balance": -1.5
            }
        }
        
        # Act
        response = self.client.get('/energy_data')
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"], self.server.peer_data)
    
    def test_energy_data_post_endpoint(self):
        """Test posting energy data."""
        # Arrange
        energy_data = {
            "timestamp": "2023-01-01T12:00:00",
            "demand": 1.5,
            "balance": -1.5
        }
        
        # Act
        response = self.client.post(
            '/energy_data',
            json=energy_data,
            environ_base={'REMOTE_ADDR': '192.168.1.2'}
        )
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(self.server.peer_data["192.168.1.2"], energy_data)
    
    def test_energy_data_post_validation(self):
        """Test validation of posted energy data."""
        # Arrange
        invalid_data = {
            "timestamp": "2023-01-01T12:00:00",
            # Missing required fields
        }
        
        # Act
        response = self.client.post(
            '/energy_data',
            json=invalid_data,
            environ_base={'REMOTE_ADDR': '192.168.1.2'}
        )
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
    
    def test_trade_get_endpoint(self):
        """Test getting trade data."""
        # Arrange
        self.server.trade_data = {
            "192.168.1.2": [
                {
                    "timestamp": "2023-01-01T12:00:00",
                    "amount": 1.0,
                    "price": 0.15,
                    "recorded_at": "2023-01-01T12:00:01"
                }
            ]
        }
        
        # Act
        response = self.client.get('/trade')
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["trades"], self.server.trade_data)
    
    def test_trade_post_endpoint(self):
        """Test posting trade data."""
        # Arrange
        trade_data = {
            "timestamp": "2023-01-01T12:00:00",
            "amount": 1.0,
            "price": 0.15
        }
        
        # Act
        response = self.client.post(
            '/trade',
            json=trade_data,
            environ_base={'REMOTE_ADDR': '192.168.1.2'}
        )
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(self.server.trade_data["192.168.1.2"]), 1)
        self.assertEqual(self.server.trade_data["192.168.1.2"][0]["amount"], 1.0)
        self.assertEqual(self.server.trade_data["192.168.1.2"][0]["price"], 0.15)
    
    def test_trade_post_validation(self):
        """Test validation of posted trade data."""
        # Arrange
        invalid_data = {
            "timestamp": "2023-01-01T12:00:00",
            # Missing required fields
        }
        
        # Act
        response = self.client.post(
            '/trade',
            json=invalid_data,
            environ_base={'REMOTE_ADDR': '192.168.1.2'}
        )
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
    
    def test_simulation_get_endpoint(self):
        """Test getting simulation status."""
        # Arrange
        self.server.simulation_data = {
            "status": "in_progress",
            "current_timestamp": "2023-01-01T12:00:00",
            "start_time": "2023-01-01T11:00:00",
            "end_time": None
        }
        
        # Act
        response = self.client.get('/simulation')
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["simulation"], self.server.simulation_data)
    
    def test_simulation_post_endpoint(self):
        """Test updating simulation status."""
        # Arrange
        simulation_data = {
            "status": "in_progress",
            "timestamp": "2023-01-01T12:00:00"
        }
        
        # Act
        response = self.client.post('/simulation', json=simulation_data)
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(self.server.simulation_data["status"], "in_progress")
        self.assertEqual(self.server.simulation_data["current_timestamp"], "2023-01-01T12:00:00")
    
    def test_sync_endpoint(self):
        """Test timestamp synchronization endpoint."""
        # Arrange
        sync_data = {"timestamp": "2023-01-01T12:00:00"}
        
        # Act
        response = self.client.post('/sync', json=sync_data)
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "synced")
        self.assertEqual(self.server.simulation_data["current_timestamp"], "2023-01-01T12:00:00")
        self.assertEqual(self.server.simulation_data["status"], "in_progress")
    
    def test_sync_start_signal(self):
        """Test handling of START synchronization signal."""
        # Arrange
        sync_data = {"timestamp": "START"}
        
        # Act
        response = self.client.post('/sync', json=sync_data)
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "synced")
        self.assertEqual(self.server.simulation_data["current_timestamp"], "START")
        self.assertEqual(self.server.simulation_data["status"], "starting")
        self.assertIsNotNone(self.server.simulation_data["start_time"])
    
    def test_sync_end_signal(self):
        """Test handling of END synchronization signal."""
        # Arrange
        sync_data = {"timestamp": "END"}
        
        # Act
        response = self.client.post('/sync', json=sync_data)
        data = json.loads(response.data)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "synced")
        self.assertEqual(self.server.simulation_data["current_timestamp"], "END")
        self.assertEqual(self.server.simulation_data["status"], "completed")
        self.assertIsNotNone(self.server.simulation_data["end_time"])
    
    @patch('threading.Thread')
    def test_start_server(self, mock_thread):
        """Test starting the server."""
        # Mock thread to avoid actually starting a server
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Act
        self.server.start()
        
        # Assert
        self.assertTrue(self.server.is_running)
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    def test_stop_server(self):
        """Test stopping the server."""
        # Arrange
        self.server.is_running = True
        self.server.server_thread = Mock()
        
        # Act
        self.server.stop()
        
        # Assert
        self.assertFalse(self.server.is_running)
        self.server.server_thread.join.assert_called_once()
    
    def test_get_status(self):
        """Test getting server status."""
        # Arrange
        self.server.is_running = True
        self.server.peer_data = {"192.168.1.2": {}}
        self.server.trade_data = {"192.168.1.2": [{}]}
        self.server.simulation_data["status"] = "in_progress"
        
        # Act
        status = self.server.get_status()
        
        # Assert
        self.assertTrue(status["running"])
        self.assertEqual(status["peer_count"], 1)
        self.assertEqual(status["trade_count"], 1)
        self.assertEqual(status["simulation_status"], "in_progress")

if __name__ == '__main__':
    unittest.main()