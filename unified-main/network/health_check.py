# Branch: unified-main
# File: network/health_check.py

"""
Health checking service for the SolarVille system.
Monitors the health of peers in the network and tracks their status.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable

from core.config import ConfigManager
from core.device_types import PiDevice
from network.network_manager import NetworkManager

class HealthChecker:
    """
    Monitors the health of peers in the network.
    Regularly checks peer health and maintains status information.
    """
    
    def __init__(self, config: ConfigManager, network_manager: NetworkManager):
        """
        Initialize health checker.
        
        Args:
            config: Configuration manager
            network_manager: Network manager for communication
        """
        self.config = config
        self.network_manager = network_manager
        self.logger = logging.getLogger(__name__)
        
        # Health status of peers: IP address -> health status
        self.health_status: Dict[str, bool] = {}
        
        # Last check times for peers: IP address -> timestamp
        self.last_check_time: Dict[str, float] = {}
        
        # Health check thread
        self.check_thread: Optional[threading.Thread] = None
        self.checking_active = False
        
        # Check interval in seconds
        self.check_interval = 10
        
        # Status change callbacks: IP address -> list of callbacks
        self.status_change_callbacks: Dict[str, List[Callable[[str, bool], None]]] = {}
        
        self.logger.info("HealthChecker initialized")
    
    def start_checking(self) -> None:
        """Start the health checking process in a background thread."""
        if self.check_thread and self.check_thread.is_alive():
            self.logger.warning("Health checking already running")
            return
            
        self.checking_active = True
        self.check_thread = threading.Thread(
            target=self._check_loop,
            daemon=True
        )
        self.check_thread.start()
        self.logger.info("Health checking started")
    
    def stop_checking(self) -> None:
        """Stop the health checking process."""
        self.checking_active = False
        if self.check_thread:
            self.check_thread.join(timeout=5.0)
            if self.check_thread.is_alive():
                self.logger.warning("Health check thread did not terminate cleanly")
            self.check_thread = None
        self.logger.info("Health checking stopped")
    
    # This is an updated version of the _check_loop method for network/health_check.py

    def _check_loop(self) -> None:
        """Main health check loop that runs in a background thread."""
        error_count = 0
        max_consecutive_errors = 3
        
        while self.checking_active:
            try:
                # Check the health of all known peers
                self._check_all_peers()
                
                # Reset error counter on success
                error_count = 0
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                error_count += 1
                self.logger.error(f"Error in health check loop: {str(e)}")
                
                # Continue checking even after errors
                # Short sleep on error to allow more check attempts
                time.sleep(max(0.1, self.check_interval / 2))
                
                # Stop checking if too many consecutive errors
                if error_count >= max_consecutive_errors:
                    self.logger.critical(f"Stopping health checks after {error_count} consecutive errors")
                    self.checking_active = False
                    break
    
    def _check_all_peers(self) -> None:
        """Check the health of all known peers."""
        for peer_id, peer in self.config.devices.items():
            # Skip local device
            local_device = self.config.get_local_device()
            if local_device and peer.ip_address == local_device.ip_address:
                continue
                
            self._check_peer(peer)
    
    def _check_peer(self, peer: PiDevice) -> None:
        """
        Check the health of a specific peer.
        
        Args:
            peer: Peer device to check
        """
        try:
            # Record check time
            current_time = time.time()
            self.last_check_time[peer.ip_address] = current_time
            
            # Previous status (default to unknown/False)
            previous_status = self.health_status.get(peer.ip_address, False)
            
            # Send health check request
            response = self.network_manager.send_request(
                peer=peer,
                endpoint="/health",
                timeout=2.0,
                critical=False
            )
            
            # Update health status
            is_healthy = "error" not in response
            self.health_status[peer.ip_address] = is_healthy
            
            # Log status changes
            if previous_status != is_healthy:
                if is_healthy:
                    self.logger.info(f"Peer {peer.name} ({peer.ip_address}) is now healthy")
                else:
                    self.logger.warning(f"Peer {peer.name} ({peer.ip_address}) is now unhealthy")
                    
                # Call status change callbacks
                self._notify_status_change(peer.ip_address, is_healthy)
                
        except Exception as e:
            self.logger.debug(f"Error checking peer {peer.name} ({peer.ip_address}): {str(e)}")
            # Mark as unhealthy on error
            previous_status = self.health_status.get(peer.ip_address, False)
            self.health_status[peer.ip_address] = False
            
            # Notify of status change
            if previous_status:
                self.logger.warning(f"Peer {peer.name} ({peer.ip_address}) is now unhealthy")
                self._notify_status_change(peer.ip_address, False)
    
    def _notify_status_change(self, peer_ip: str, is_healthy: bool) -> None:
        """
        Notify callbacks of peer status change.
        
        Args:
            peer_ip: IP address of the peer
            is_healthy: Whether the peer is healthy
        """
        if peer_ip in self.status_change_callbacks:
            for callback in self.status_change_callbacks[peer_ip]:
                try:
                    callback(peer_ip, is_healthy)
                except Exception as e:
                    self.logger.error(f"Error in status change callback: {str(e)}")
    
    def register_status_change_callback(self, peer_ip: str, callback: Callable[[str, bool], None]) -> None:
        """
        Register a callback to be called when a peer's status changes.
        
        Args:
            peer_ip: IP address of the peer
            callback: Callback function taking peer_ip and is_healthy arguments
        """
        if peer_ip not in self.status_change_callbacks:
            self.status_change_callbacks[peer_ip] = []
            
        self.status_change_callbacks[peer_ip].append(callback)
    
    def check_peer_now(self, peer: PiDevice) -> bool:
        """
        Immediately check the health of a specific peer.
        
        Args:
            peer: Peer device to check
            
        Returns:
            True if peer is healthy, False otherwise
        """
        try:
            # Send health check request
            response = self.network_manager.send_request(
                peer=peer,
                endpoint="/health",
                timeout=2.0,
                critical=False
            )
            
            # Update health status
            is_healthy = "error" not in response
            previous_status = self.health_status.get(peer.ip_address, False)
            self.health_status[peer.ip_address] = is_healthy
            
            # Record check time
            self.last_check_time[peer.ip_address] = time.time()
            
            # Notify of status change
            if previous_status != is_healthy:
                self._notify_status_change(peer.ip_address, is_healthy)
                
            return is_healthy
            
        except Exception as e:
            self.logger.debug(f"Error checking peer {peer.name} ({peer.ip_address}): {str(e)}")
            # Mark as unhealthy on error
            previous_status = self.health_status.get(peer.ip_address, False)
            self.health_status[peer.ip_address] = False
            
            # Notify of status change
            if previous_status:
                self._notify_status_change(peer.ip_address, False)
                
            return False
    
    def is_peer_healthy(self, peer_ip: str) -> bool:
        """
        Check if a peer is healthy based on the last health check.
        
        Args:
            peer_ip: IP address of the peer
            
        Returns:
            True if peer is healthy, False otherwise
        """
        return self.health_status.get(peer_ip, False)
    
    def get_healthy_peers(self) -> List[PiDevice]:
        """
        Get list of healthy peers.
        
        Returns:
            List of healthy peers
        """
        healthy_peers = []
        for peer_id, peer in self.config.devices.items():
            if peer.ip_address in self.health_status and self.health_status[peer.ip_address]:
                healthy_peers.append(peer)
        return healthy_peers
    
    def get_unhealthy_peers(self) -> List[PiDevice]:
        """
        Get list of unhealthy peers.
        
        Returns:
            List of unhealthy peers
        """
        unhealthy_peers = []
        for peer_id, peer in self.config.devices.items():
            if peer.ip_address not in self.health_status or not self.health_status[peer.ip_address]:
                unhealthy_peers.append(peer)
        return unhealthy_peers