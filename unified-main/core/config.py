# Branch: unified-main
# File: config.py

"""Configuration management for SolarVille."""
import os
import yaml
import logging
from dataclasses import dataclass
from typing import Dict, Optional, List
from core.device_types import PiDevice
from core.constants import (
    DEFAULT_PORT, RETRY_ATTEMPTS, TIMEOUT_SECONDS,
    GRID_BUY_PRICE, GRID_SELL_PRICE,
    LCD_ROWS, LCD_COLS
)

class ConfigurationError(Exception):
    """Raised when there's an error in configuration"""
    pass

@dataclass
class SimulationConfig:
    """Simulation settings"""
    file_path: str = "data/block_0.csv"
    start_date: str = "2012-10-24"
    timescale: str = "d"
    simulation_speed: int = 300
    interval_seconds: int = 6
    log_level: str = "INFO"

@dataclass
class HardwareConfig:
    """Hardware settings automatically determined by device role"""
    mock_mode: bool = True
    lcd_enabled: bool = True
    lcd_rows: int = LCD_ROWS
    lcd_cols: int = LCD_COLS
    solar_enabled: bool = False
    storage_enabled: bool = False

    def configure_for_role(self, is_prosumer: bool) -> None:
        """Configure hardware based on device role"""
        if is_prosumer:
            self.solar_enabled = True
            self.storage_enabled = True
        else:
            self.solar_enabled = False
            self.storage_enabled = False

class ConfigManager:
    """Manages configuration loading and validation"""
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.simulation_config = SimulationConfig()
        self.hardware_config = HardwareConfig()
        self.devices: Dict[str, PiDevice] = {}
        
        # Use constants for these values
        self.server_port = DEFAULT_PORT
        self.retry_attempts = RETRY_ATTEMPTS
        self.timeout_seconds = TIMEOUT_SECONDS
        self.grid_buy_price = GRID_BUY_PRICE
        self.grid_sell_price = GRID_SELL_PRICE
        
    def load_config(self) -> None:
        """Load all configuration files"""
        try:
            self._load_simulation_config()
            self._load_network_topology()
            
            # Configure hardware based on local device role
            local_device = self.get_local_device()
            if local_device:
                self.hardware_config.configure_for_role(local_device.is_prosumer)
            else:
                raise ConfigurationError("Could not determine local device")
                
            logging.info("Configuration loaded successfully")
            self._log_configuration()
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _load_simulation_config(self) -> None:
        """Load simulation configuration"""
        sim_path = os.path.join(self.config_dir, "simulation.yml")
        try:
            with open(sim_path, 'r') as f:
                data = yaml.safe_load(f)
                
            # Update simulation config
            sim_data = data.get('simulation', {})
            self.simulation_config = SimulationConfig(**sim_data)
            
            # Update mock mode if specified
            if 'hardware' in data and 'mock_mode' in data['hardware']:
                self.hardware_config.mock_mode = data['hardware']['mock_mode']
                
        except FileNotFoundError:
            logging.warning(f"Simulation config not found at {sim_path}, using defaults")
        except Exception as e:
            raise ConfigurationError(f"Error loading simulation config: {e}")
    
    def _load_network_topology(self) -> None:
        """Load network topology configuration"""
        topology_path = os.path.join(self.config_dir, "network_topology.yml")
        try:
            with open(topology_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Load devices
            devices_data = data.get('devices', {})
            self.devices = {
                name: PiDevice.from_dict({**dev_data, 'name': name})
                for name, dev_data in devices_data.items()
            }
            
        except FileNotFoundError:
            raise ConfigurationError(f"Network topology config not found at {topology_path}")
        except Exception as e:
            raise ConfigurationError(f"Error loading network topology: {e}")
    
    def get_local_device(self) -> Optional[PiDevice]:
        """Get the local device based on hostname"""
        import socket
        hostname = socket.gethostname()
        for device in self.devices.values():
            if device.hostname == hostname:
                return device
        return None
    
    def get_prosumers(self) -> List[PiDevice]:
        """Get list of prosumer devices"""
        return [d for d in self.devices.values() if d.is_prosumer]
    
    def get_consumers(self) -> List[PiDevice]:
        """Get list of consumer devices"""
        return [d for d in self.devices.values() if not d.is_prosumer]
    
    def _log_configuration(self) -> None:
        """Log the current configuration"""
        logging.info("Current configuration:")
        logging.info(f"Simulation: {vars(self.simulation_config)}")
        logging.info(f"Hardware: {vars(self.hardware_config)}")
        local_device = self.get_local_device()
        if local_device:
            logging.info(f"Device Role: {'Prosumer' if local_device.is_prosumer else 'Consumer'}")
            logging.info(f"Device Info: {vars(local_device)}")

    def validate_config(self) -> None:
        """
        Validate the loaded configuration.
        Raises ConfigurationError if validation fails.
        """
        try:
            self._validate_devices()
            self._validate_simulation()
            self._validate_network()
            logging.info("Configuration validation successful")
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")

    def _validate_devices(self) -> None:
        """Validate device configuration"""
        if not self.devices:
            raise ConfigurationError("No devices configured")
        
        # Check if local device exists
        local_device = self.get_local_device()
        if not local_device:
            raise ConfigurationError("Local device not found in configuration")
        
        # Validate IP addresses
        for name, device in self.devices.items():
            if not self._is_valid_ip(device.ip_address):
                raise ConfigurationError(f"Invalid IP address for device {name}: {device.ip_address}")
            
            # Check for duplicate IPs
            ip_count = sum(1 for d in self.devices.values() if d.ip_address == device.ip_address)
            if ip_count > 1:
                raise ConfigurationError(f"Duplicate IP address found: {device.ip_address}")
        
        # Ensure at least one prosumer and one consumer
        if not self.get_prosumers():
            raise ConfigurationError("No prosumer devices configured")
        if not self.get_consumers():
            raise ConfigurationError("No consumer devices configured")

    def _validate_simulation(self) -> None:
        """Validate simulation configuration"""
        # Check time parameters
        if self.simulation_config.simulation_speed <= 0:
            raise ConfigurationError("Simulation speed must be positive")
        
        if self.simulation_config.interval_seconds <= 0:
            raise ConfigurationError("Interval seconds must be positive")
        
        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(self.simulation_config.start_date, "%Y-%m-%d")
        except ValueError:
            raise ConfigurationError("Invalid start date format, should be YYYY-MM-DD")
        
        # Check timescale
        if self.simulation_config.timescale not in ['d', 'w', 'm', 'y']:
            raise ConfigurationError("Invalid timescale, must be one of: d, w, m, y")
        
        # Check if data file exists
        if not os.path.exists(self.simulation_config.file_path):
            raise ConfigurationError(f"Data file not found: {self.simulation_config.file_path}")

    def _validate_network(self) -> None:
        """Validate network configuration"""
        if not (1024 <= self.server_port <= 65535):
            raise ConfigurationError(f"Invalid server port: {self.server_port}")
        
        if not (1 <= self.retry_attempts <= 10):
            raise ConfigurationError(f"Invalid retry attempts: {self.retry_attempts}")
        
        if not (1 <= self.timeout_seconds <= 30):
            raise ConfigurationError(f"Invalid timeout seconds: {self.timeout_seconds}")

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Check if string is valid IPv4 address"""
        import socket
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False