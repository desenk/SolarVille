# Branch: unified-main
# File: main.py

#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# Core imports
from core.config import ConfigManager
from core.energy_types import PiDevice

# Hardware imports
from hardware.lcd_manager import LCDManager
from hardware.solar_manager import SolarMonitor
from hardware.capacitor_manager import CapacitorManager

# Network imports
from network.topology import NetworkTopology
from network.trading_integration import TradingIntegration
from network.discovery import PeerDiscovery
from network.health_check import HealthChecker
from network.server import app

# Simulation imports
from simulation.trading_manager import TradingManager
from simulation.visualisation_manager import VisualisationManager
from simulation.data_analysis import load_data

# Utils imports
from utils.logging import setup_logging
from utils.error_handling import ErrorHandler

class SolarVille:
    def __init__(self):
        """Initialize SolarVille system"""
        self.config = None
        self.device = None
        self.components = {}
        
    def initialize(self, config_path: str = None):
        """Initialize all system components"""
        try:
            # Load configuration
            self.config = ConfigManager(config_path)
            self.config.load_config()
            
            # Set up logging
            setup_logging(self.config.sim_config.log_level)
            
            # Initialize network topology
            self.topology = NetworkTopology()
            self.device = self.topology.get_local_device()
            
            # Initialize components based on device role
            self._initialize_components()
            
            logging.info("SolarVille initialization complete")
            return True
            
        except Exception as e:
            logging.error(f"Initialization failed: {e}")
            return False
            
    def _initialize_components(self):
        """Initialize components based on device role"""
        try:
            # Common components
            self.components.update({
                'lcd': LCDManager(mock_mode=self.config.sim_config.mock_mode),
                'health_checker': HealthChecker(),
                'error_handler': ErrorHandler(),
                'trading_manager': TradingManager(self.device.is_prosumer),
                'vis_manager': VisualisationManager(
                    self.config.sim_config.start_date,
                    self.config.sim_config.timescale
                )
            })
            
            # Prosumer-specific components
            if self.device.is_prosumer:
                self.components.update({
                    'solar_monitor': SolarMonitor(mock_mode=self.config.sim_config.mock_mode),
                    'capacitor_manager': CapacitorManager(mock_mode=self.config.sim_config.mock_mode)
                })
                
            logging.info(f"Initialized components for {'prosumer' if self.device.is_prosumer else 'consumer'}")
            
        except Exception as e:
            logging.error(f"Component initialization failed: {e}")
            raise
            
    def start(self):
        """Start the simulation"""
        try:
            logging.info("Starting simulation...")
            
            # Load energy data
            data = load_data(
                self.config.sim_config.file_path,
                self.config.sim_config.household
            )
            if data is None:
                raise ValueError("Failed to load energy data")
                
            # Start visualization
            self.components['vis_manager'].start(data)
            
            # Start main simulation loop
            self._run_simulation(data)
            
        except KeyboardInterrupt:
            logging.info("Simulation interrupted by user")
        except Exception as e:
            logging.error(f"Simulation error: {e}")
        finally:
            self.cleanup()
            
    def _run_simulation(self, data):
        """Main simulation loop"""
        pass  # To be implemented
        
    def cleanup(self):
        """Cleanup resources"""
        logging.info("Cleaning up...")
        for component in self.components.values():
            if hasattr(component, 'cleanup'):
                try:
                    component.cleanup()
                except Exception as e:
                    logging.error(f"Cleanup error: {e}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='SolarVille Smart Grid Simulation')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode')
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    # Create and initialize SolarVille
    solarville = SolarVille()
    if not solarville.initialize(args.config):
        sys.exit(1)
        
    # Start simulation
    solarville.start()

if __name__ == "__main__":
    main()