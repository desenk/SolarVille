# Branch: unified-main
# File: network/peer_discovery.py

"""
Peer discovery service for SolarVille system.
Handles discovering, verifying, and monitoring peers in the network.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Set
import socket

from core.config import ConfigManager
from core.device_types import PiDevice
from network.network_manager import NetworkManager
from network.network_errors import NetworkError

class PeerDiscovery:
    """
    Manages peer discovery, verification, and monitoring.
    Maintains an up-to-date list of available peers in the network.
    """
    
    def __init__(self, config: ConfigManager, network_manager: NetworkManager):
        """
        Initialize peer discovery service.
        
        Args:
            config: Configuration manager
            network_manager: Network manager for communication
        """
        self.config = config
        self.network_manager = network_manager
        self.logger = logging.getLogger(__name__)
        
        # Known peers from configuration
        self.known_peers: Dict[str, PiDevice] = self.config.devices
        
        # Dynamic list of discovered peers (may include peers not in config)
        self.discovered_peers: Dict[str, PiDevice] = {}
        
        # Peer availability status
        self.peer_status: Dict[str, bool] = {}
        
        # Discovery thread
        self.discovery_thread: Optional[threading.Thread] = None
        self.discovery_active = False
        
        # Discovery interval in seconds
        self.discovery_interval = 30
        
        self.logger.info("PeerDiscovery initialized")
    
    def start_discovery(self) -> None:
        """Start the peer discovery process in a background thread."""
        if self.discovery_thread and self.discovery_thread.is_alive():
            self.logger.warning("Discovery already running")
            return
            
        self.discovery_active = True
        self.discovery_thread = threading.Thread(
            target=self._discovery_loop,
            daemon=True
        )
        self.discovery_thread.start()
        self.logger.info("Peer discovery started")
    
    def stop_discovery(self) -> None:
        """Stop the peer discovery process."""
        self.discovery_active = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=5.0)
            if self.discovery_thread.is_alive():
                self.logger.warning("Discovery thread did not terminate cleanly")
            self.discovery_thread = None
        self.logger.info("Peer discovery stopped")
    
    def _discovery_loop(self) -> None:
        """Main discovery loop that runs in a background thread."""
        error_count = 0
        max_consecutive_errors = 3
        
        while self.discovery_active:
            try:
                # 1. Check known peers from config
                self._check_known_peers()
                
                # 2. Discover new peers on the network (can find peers not in config)
                self._discover_local_network_peers()
                
                # 3. Verify all discovered peers
                self._verify_all_peers()
                
                # 4. Update peer status based on verification
                self._update_peer_availability()
                
                # Reset error counter on success
                error_count = 0
                
                # Sleep before next discovery cycle
                time.sleep(self.discovery_interval)
                
            except Exception as e:
                error_count += 1
                self.logger.error(f"Error in discovery loop: {str(e)}")
                
                # Continue discovery even after errors
                # Short sleep on error to allow more discovery attempts
                time.sleep(max(0.1, self.discovery_interval / 2))
                
                # Stop discovery if too many consecutive errors
                if error_count >= max_consecutive_errors:
                    self.logger.critical(f"Stopping discovery after {error_count} consecutive errors")
                    self.discovery_active = False
                    break
    
    def _check_known_peers(self) -> None:
        """Check status of all known peers from configuration."""
        for peer_id, peer in self.known_peers.items():
            # Skip local device
            local_device = self.config.get_local_device()
            if local_device and peer.ip_address == local_device.ip_address:
                continue
                
            try:
                # Use network manager to check if peer is online
                response = self.network_manager.send_request(
                    peer=peer,
                    endpoint="/health",
                    timeout=2.0
                )
                
                is_online = "error" not in response
                self.peer_status[peer.ip_address] = is_online
                
                if is_online:
                    self.logger.debug(f"Known peer {peer.name} ({peer.ip_address}) is online")
                    # If peer wasn't in discovered peers, add it
                    if peer.ip_address not in self.discovered_peers:
                        self.discovered_peers[peer.ip_address] = peer
                else:
                    self.logger.debug(f"Known peer {peer.name} ({peer.ip_address}) is offline")
                    
            except Exception as e:
                self.logger.debug(f"Error checking known peer {peer.name}: {str(e)}")
                self.peer_status[peer.ip_address] = False
    
    def _discover_local_network_peers(self) -> None:
        """
        Discover peers on the local network using network scanning.
        This can find peers not listed in the configuration.
        """
        try:
            # Get IP address parts for subnet scanning
            local_device = self.config.get_local_device()
            if not local_device:
                self.logger.warning("Cannot discover peers: local device unknown")
                return
                
            # Get local IP components for subnet determination
            ip_parts = local_device.ip_address.split('.')
            if len(ip_parts) != 4:
                self.logger.warning(f"Invalid IP format: {local_device.ip_address}")
                return
                
            # Scan the local subnet (assuming /24 for simplicity)
            subnet_prefix = '.'.join(ip_parts[0:3])
            
            # Only scan a few addresses to avoid excessive traffic
            # In a real implementation, this would be more sophisticated
            for i in range(1, 10):  # Just scan 10 addresses as an example
                target_ip = f"{subnet_prefix}.{i}"
                
                # Skip self
                if target_ip == local_device.ip_address:
                    continue
                    
                # Skip already known peers
                if target_ip in self.discovered_peers:
                    continue
                    
                self._check_potential_peer(target_ip)
                
        except Exception as e:
            self.logger.error(f"Error during local network peer discovery: {str(e)}")
    
    def _check_potential_peer(self, ip_address: str) -> None:
        """
        Check if an IP address belongs to a SolarVille peer.
        
        Args:
            ip_address: IP address to check
        """
        try:
            # Create a temporary PiDevice for the check
            temp_device = PiDevice(
                name=f"unknown-{ip_address}",
                ip_address=ip_address,
                is_prosumer=False,  # Default to consumer until verified
                hostname="unknown"
            )
            
            # Try to connect to the health endpoint
            response = self.network_manager.send_request(
                peer=temp_device,
                endpoint="/health",
                timeout=1.0
            )
            
            if "error" not in response:
                # This appears to be a SolarVille peer
                self.logger.info(f"Discovered new peer at {ip_address}")
                
                # Try to get peer info
                peer_info = self.network_manager.send_request(
                    peer=temp_device,
                    endpoint="/peer_info",
                    timeout=1.0
                )
                
                if "error" not in peer_info:
                    # Create a proper PiDevice from peer info
                    discovered_device = PiDevice(
                        name=peer_info.get("name", f"unknown-{ip_address}"),
                        ip_address=ip_address,
                        is_prosumer=peer_info.get("is_prosumer", False),
                        hostname=peer_info.get("hostname", "unknown")
                    )
                    
                    self.discovered_peers[ip_address] = discovered_device
                    self.peer_status[ip_address] = True
                else:
                    # Add with minimal info
                    self.discovered_peers[ip_address] = temp_device
                    self.peer_status[ip_address] = True
                    
        except Exception as e:
            self.logger.debug(f"Error checking potential peer at {ip_address}: {str(e)}")
    
    def _verify_all_peers(self) -> None:
        """Verify all discovered peers."""
        for ip, peer in list(self.discovered_peers.items()):
            try:
                response = self.network_manager.send_request(
                    peer=peer,
                    endpoint="/health",
                    timeout=2.0
                )
                
                is_online = "error" not in response
                self.peer_status[ip] = is_online
                
                if not is_online:
                    self.logger.debug(f"Peer {peer.name} ({ip}) failed verification")
                    
            except Exception as e:
                self.logger.debug(f"Error verifying peer {peer.name} ({ip}): {str(e)}")
                self.peer_status[ip] = False
    
    def _update_peer_availability(self) -> None:
        """Update the availability status of all peers."""
        online_count = sum(1 for status in self.peer_status.values() if status)
        offline_count = len(self.peer_status) - online_count
        
        self.logger.info(f"Peer status: {online_count} online, {offline_count} offline")
        
        # Remove peers that have been offline for too long
        # This is a placeholder - in a real implementation we might
        # want to keep them around longer or have a more sophisticated
        # algorithm for removing peers
            
    def get_available_peers(self) -> List[PiDevice]:
        """
        Get list of all available peers.
        
        Returns:
            List of available peers
        """
        available_peers = []
        for ip, peer in self.discovered_peers.items():
            if self.peer_status.get(ip, False):
                available_peers.append(peer)
        return available_peers
    
    def get_available_prosumers(self) -> List[PiDevice]:
        """
        Get list of available prosumer peers.
        
        Returns:
            List of available prosumer peers
        """
        return [p for p in self.get_available_peers() if p.is_prosumer]
    
    def get_available_consumers(self) -> List[PiDevice]:
        """
        Get list of available consumer peers.
        
        Returns:
            List of available consumer peers
        """
        return [p for p in self.get_available_peers() if not p.is_prosumer]
    
    def is_peer_available(self, peer_id: str) -> bool:
        """
        Check if a specific peer is available.
        
        Args:
            peer_id: Peer ID to check
            
        Returns:
            True if peer is available, False otherwise
        """
        # Check by name
        for peer in self.discovered_peers.values():
            if peer.name == peer_id and self.peer_status.get(peer.ip_address, False):
                return True
                
        # Check by IP
        return self.peer_status.get(peer_id, False)