# core/config.py
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