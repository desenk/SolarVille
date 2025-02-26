# Branch: unified-main
# File: tests/test_network_manager.py

import unittest
from unittest.mock import Mock, patch
import requests
from datetime import datetime
import asyncio
from core.config import ConfigManager, SimulationConfig
from core.device_types import PiDevice
from network.network_manager import (
    NetworkManager,
    NetworkError,
    RequestTimeoutError,
    PeerUnavailableError
)

class TestNetworkManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Mock config
        self.config = Mock(spec=ConfigManager)
        self.config.devices = {
            'pi1': PiDevice(
                name='pi1',
                ip_address='10.0.0.1',
                is_prosumer=True,
                hostname='prosumer-1'
            ),
            'pi2': PiDevice(
                name='pi2',
                ip_address='10.0.0.2',
                is_prosumer=False,
                hostname='consumer-1'
            )
        }
        
        # Configure mocked methods
        self.config.get_prosumers.return_value = [
            device for device in self.config.devices.values() 
            if device.is_prosumer
        ]
        self.config.get_consumers.return_value = [
            device for device in self.config.devices.values() 
            if not device.is_prosumer
        ]
        
        # Create NetworkManager instance
        self.network_manager = NetworkManager(self.config)
        
        # Setup test data
        self.test_data = {'test': 'data'}
        self.test_peer = self.config.devices['pi1']

    def tearDown(self):
        """Clean up after each test"""
        asyncio.run(self.network_manager.cleanup())

    @patch('requests.Session')
    def test_successful_request(self, mock_session):
        """Test successful network request"""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success'}
        mock_session.return_value.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        
        # Make request
        response = asyncio.run(self.network_manager.send_request(
            self.test_peer,
            '/test'
        ))
        
        # Verify
        self.assertEqual(response, {'status': 'success'})
        self.assertTrue(self.network_manager.is_peer_available(self.test_peer))

    @patch('requests.Session')
    def test_retry_on_timeout(self, mock_session):
        """Test retry mechanism on timeout"""
        # Setup mock to timeout twice then succeed
        mock_session.return_value.get.side_effect = [
            requests.Timeout(),
            requests.Timeout(),
            Mock(json=lambda: {'status': 'success'})
        ]
        
        # Make request
        response = asyncio.run(self.network_manager.send_request(
            self.test_peer,
            '/test',
            retry_count=3
        ))
        
        # Verify
        self.assertEqual(response, {'status': 'success'})
        self.assertEqual(mock_session.return_value.get.call_count, 3)

    @patch('requests.Session')
    def test_max_retries_exceeded(self, mock_session):
        """Test exception when max retries are exceeded"""
        # Setup mock to always timeout
        mock_session.return_value.get.side_effect = requests.Timeout()
        
        # Verify exception is raised
        with self.assertRaises(RequestTimeoutError):
            asyncio.run(self.network_manager.send_request(
                self.test_peer,
                '/test',
                retry_count=3
            ))
        
        # Verify peer is marked as unavailable
        self.assertFalse(self.network_manager.is_peer_available(self.test_peer))

    def test_broadcast_request(self):
        """Test broadcasting to multiple peers"""
        async def mock_send_request(peer, endpoint, method='GET', data=None):
            return {'peer': peer.ip_address, 'status': 'success'}
            
        # Patch send_request method
        self.network_manager.send_request = mock_send_request
        
        # Make broadcast request
        responses = asyncio.run(self.network_manager.broadcast(
            '/test',
            self.test_data,
            include_prosumers=True,
            include_consumers=True
        ))
        
        # Verify all peers received broadcast
        self.assertEqual(len(responses), len(self.config.devices))
        for ip in responses:
            self.assertEqual(responses[ip]['status'], 'success')

    @patch('requests.Session')
    def test_peer_status_tracking(self, mock_session):
        """Test peer status tracking"""
        # Mock successful request
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success'}
        mock_session.return_value.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        
        # Make successful request
        asyncio.run(self.network_manager.send_request(self.test_peer, '/test'))
        self.assertTrue(self.network_manager.is_peer_available(self.test_peer))
        
        # Mock failed request
        mock_session.return_value.get.side_effect = requests.Timeout()
        
        # Make failed request
        with self.assertRaises(RequestTimeoutError):
            asyncio.run(self.network_manager.send_request(self.test_peer, '/test'))
        self.assertFalse(self.network_manager.is_peer_available(self.test_peer))

    @patch('requests.Session')
    def test_cleanup(self, mock_session):
        """Test cleanup method"""
        asyncio.run(self.network_manager.cleanup())
        mock_session.return_value.close.assert_called_once()

    def test_get_available_peers(self):
        """Test getting available peers"""
        # Mark some peers as available
        self.network_manager._peers_status = {
            '10.0.0.1': True,
            '10.0.0.2': False
        }
        
        # Get available peers
        available_peers = self.network_manager.get_available_peers()
        
        # Verify
        self.assertEqual(len(available_peers), 1)
        self.assertIn('10.0.0.1', [p.ip_address for p in available_peers.values()])

if __name__ == '__main__':
    unittest.main()