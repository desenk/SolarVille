# Branch: unified-main
# File: network/topology.py

"""
Network topology manager for SolarVille system.
Manages the network topology including device discovery and communication paths.
"""

import logging
import socket
from typing import Dict, List, Optional, Set

from core.config import ConfigManager
from core.device_types import PiDevice

class TopologyError(Exception):
    """Base exception for topology-related errors"""
    pass

class NetworkTopology:
    """
    Manages the network topology of the SolarVille system.
    Tracks devices, their roles, and communication paths.
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize network topology.
        
        Args:
            config: Configuration manager containing device information
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize from configuration
        self.devices: Dict[str, PiDevice] = self.config.devices.copy()
        
        # Keep track of local device
        self.local_device = self._determine_local_device()
        
        # Communication graph (which peers can communicate with each other)
        # For now, we assume a fully connected topology
        self.communication_paths: Dict[str, Set[str]] = {}
        self._initialize_communication_paths()
        
        self.logger.info("NetworkTopology initialized")
    
# This is an updated version of the _determine_local_device method for network/topology.py

    def _determine_local_device(self) -> Optional[PiDevice]:
        """
        Determine the local device based on hostname.
        
        Returns:
            Local device or None if not found
        """
        # Safely check if devices attribute exists (needed for tests)
        if not hasattr(self, 'devices') or not self.devices:
            self.logger.warning("No devices available to determine local device")
            return None
            
        local_hostname = socket.gethostname()
        
        for device_id, device in self.devices.items():
            if device.hostname == local_hostname:
                self.logger.info(f"Local device determined: {device.name} ({device.ip_address})")
                return device
                
        # If hostname doesn't match, try to match IP
        try:
            local_ip = socket.gethostbyname(local_hostname)
            for device_id, device in self.devices.items():
                if device.ip_address == local_ip:
                    self.logger.info(f"Local device determined by IP: {device.name} ({device.ip_address})")
                    return device
        except Exception as e:
            self.logger.warning(f"Error resolving local IP: {str(e)}")
        
        self.logger.warning("Could not determine local device")
        return None
    
    def _initialize_communication_paths(self) -> None:
        """Initialize communication paths between devices."""
        # For now, we assume all devices can communicate with each other
        # In a more sophisticated implementation, we might consider network
        # topology, firewalls, etc.
        for device_id, device in self.devices.items():
            peers = set()
            for peer_id, peer in self.devices.items():
                if peer_id != device_id:  # Skip self
                    peers.add(peer_id)
            self.communication_paths[device_id] = peers
    
    def get_local_device(self) -> Optional[PiDevice]:
        """
        Get the local device.
        
        Returns:
            Local device or None if not determined
        """
        return self.local_device
    
    def get_device_by_ip(self, ip_address: str) -> Optional[PiDevice]:
        """
        Get a device by IP address.
        
        Args:
            ip_address: IP address to look up
            
        Returns:
            Device or None if not found
        """
        for device in self.devices.values():
            if device.ip_address == ip_address:
                return device
        return None
    
    def get_device_by_name(self, name: str) -> Optional[PiDevice]:
        """
        Get a device by name.
        
        Args:
            name: Device name to look up
            
        Returns:
            Device or None if not found
        """
        return self.devices.get(name)
    
    def get_prosumers(self) -> List[PiDevice]:
        """
        Get all prosumer devices.
        
        Returns:
            List of prosumer devices
        """
        return [d for d in self.devices.values() if d.is_prosumer]
    
    def get_consumers(self) -> List[PiDevice]:
        """
        Get all consumer devices.
        
        Returns:
            List of consumer devices
        """
        return [d for d in self.devices.values() if not d.is_prosumer]
    
    def get_peers(self) -> List[PiDevice]:
        """
        Get all peers (excluding local device).
        
        Returns:
            List of peer devices
        """
        if not self.local_device:
            return list(self.devices.values())
            
        return [d for d in self.devices.values() if d.name != self.local_device.name]
    
    def can_communicate(self, source: str, target: str) -> bool:
        """
        Check if two devices can communicate.
        
        Args:
            source: Source device ID
            target: Target device ID
            
        Returns:
            True if communication is possible, False otherwise
        """
        if source not in self.communication_paths:
            return False
            
        return target in self.communication_paths[source]
    
    def add_device(self, device: PiDevice) -> None:
        """
        Add a new device to the topology.
        
        Args:
            device: Device to add
        """
        if device.name in self.devices:
            self.logger.warning(f"Device {device.name} already exists, updating")
            
        self.devices[device.name] = device
        
        # Update communication paths
        if device.name not in self.communication_paths:
            self.communication_paths[device.name] = set()
            
        # Assume new device can communicate with all other devices
        for peer_id in self.devices.keys():
            if peer_id != device.name:
                self.communication_paths[device.name].add(peer_id)
                self.communication_paths[peer_id].add(device.name)
                
        self.logger.info(f"Added device {device.name} ({device.ip_address}) to topology")
    
    def remove_device(self, device_id: str) -> None:
        """
        Remove a device from the topology.
        
        Args:
            device_id: ID of the device to remove
        """
        if device_id not in self.devices:
            self.logger.warning(f"Device {device_id} does not exist")
            return
            
        # Remove from devices
        del self.devices[device_id]
        
        # Remove from communication paths
        if device_id in self.communication_paths:
            del self.communication_paths[device_id]
            
        # Remove from other devices' communication paths
        for paths in self.communication_paths.values():
            if device_id in paths:
                paths.remove(device_id)
                
        self.logger.info(f"Removed device {device_id} from topology")
    
    def get_shortest_path(self, source: str, target: str) -> List[str]:
        """
        Find the shortest communication path between two devices.
        
        Args:
            source: Source device ID
            target: Target device ID
            
        Returns:
            List of device IDs forming the shortest path
            
        Raises:
            TopologyError: If no path exists
        """
        # For now, we assume direct communication is possible between all devices
        # In a more sophisticated implementation, we would use a proper
        # pathfinding algorithm (e.g., Dijkstra's)
        
        if source == target:
            return [source]
            
        if source not in self.devices:
            raise TopologyError(f"Source device {source} not found")
            
        if target not in self.devices:
            raise TopologyError(f"Target device {target} not found")
            
        if not self.can_communicate(source, target):
            raise TopologyError(f"No communication path from {source} to {target}")
            
        return [source, target]
    
    def visualize(self) -> Dict:
        """
        Generate a visualization of the network topology.
        
        Returns:
            Dictionary representation of the topology suitable for visualization
        """
        nodes = []
        links = []
        
        # Add nodes
        for device_id, device in self.devices.items():
            node = {
                "id": device_id,
                "name": device.name,
                "ip": device.ip_address,
                "type": "prosumer" if device.is_prosumer else "consumer",
                "is_local": self.local_device and device.name == self.local_device.name
            }
            nodes.append(node)
            
        # Add links
        for source, targets in self.communication_paths.items():
            for target in targets:
                # Avoid duplicate links (undirected graph)
                if source < target:
                    links.append({
                        "source": source,
                        "target": target
                    })
                    
        return {
            "nodes": nodes,
            "links": links
        }