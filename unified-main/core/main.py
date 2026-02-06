# Branch: unified-main
# File: main.py

#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# Core imports
from core.config import ConfigManager
from core.device_types import PiDevice

# Hardware imports
from hardware.lcd_manager import LCDManager
from hardware.solar_manager import SolarMonitor
from hardware.capacitor_manager import CapacitorManager

# Network imports
from network.trading_integration import TradingIntegration
from network.discovery import PeerDiscovery
from network.health_check import HealthChecker
from network.server import Server

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
        
    def initialize(self, config_path: str = None, device_name: str = None):
        """Initialize all system components"""
        try:
            # Load configuration
            self.config = ConfigManager(config_path)
            self.config.load_config()

            # Set up logging
            setup_logging(self.config.sim_config.log_level)

            # Get local device
            if device_name:
                # Use specified device
                if device_name in self.config.devices:
                    self.device = self.config.devices[device_name]
                    logging.info(f"Using specified device: {device_name}")
                else:
                    raise ValueError(f"Device '{device_name}' not found in config. Available: {list(self.config.devices.keys())}")
            else:
                # Auto-detect device
                self.device = self.config.get_local_device()

            if not self.device:
                raise ValueError("Could not determine local device")

            logging.info(f"Running as: {self.device.name} ({'prosumer' if self.device.is_prosumer else 'consumer'})")

            # Initialize components based on device role
            self._initialize_components()

            logging.info("SolarVille initialization complete")
            return True

        except Exception as e:
            logging.error(f"Initialization failed: {e}", exc_info=True)
            return False
            
    def _initialize_components(self):
        """Initialize components based on device role"""
        try:
            from network.network_manager import NetworkManager

            # Initialize network manager
            network_manager = NetworkManager(self.config)

            # Common components
            self.components.update({
                'network_manager': network_manager,
                'lcd': LCDManager(mock_mode=self.config.sim_config.mock_mode),
                'health_checker': HealthChecker(self.config, network_manager),
                'error_handler': ErrorHandler(),
                'trading_manager': TradingManager(self.config, network_manager),
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
            logging.error(f"Component initialization failed: {e}", exc_info=True)
            raise
            
    def start(self):
        """Start the simulation"""
        try:
            logging.info("Starting simulation...")

            # Get simulation config
            sim_config = self.config.sim_config

            # Load energy data with filtering
            logging.info(f"Loading data for household: {getattr(sim_config, 'household', 'MAC000002')}")

            # Calculate end date
            from simulation.data_analysis import calculate_end_date
            end_date = calculate_end_date(sim_config.start_date, sim_config.timescale)

            data = load_data(
                file_path=sim_config.file_path,
                household=getattr(sim_config, 'household', 'MAC000002'),
                start_date=sim_config.start_date,
                end_date=end_date.strftime("%Y-%m-%d")
            )

            if data is None or data.empty:
                raise ValueError("Failed to load energy data or no data in range")

            logging.info(f"Loaded {len(data)} data points")

            # Start visualization (optional)
            # self.components['vis_manager'].start(data)

            # Start main simulation loop
            self._run_simulation(data)

        except KeyboardInterrupt:
            logging.info("Simulation interrupted by user")
        except Exception as e:
            logging.error(f"Simulation error: {e}", exc_info=True)
        finally:
            self.cleanup()

    def _run_simulation(self, data):
        """
        Main simulation loop - iterates through energy data and simulates behavior.

        Args:
            data: DataFrame with datetime index and 'energy' column
        """
        import time
        import asyncio
        from core.energy_types import EnergyReading, ProsumerReading
        from simulation.data_analysis import calculate_sleep_time

        logging.info("Starting simulation loop")
        logging.info(f"Device: {self.device.name} ({'prosumer' if self.device.is_prosumer else 'consumer'})")

        sim_config = self.config.sim_config
        sleep_time = calculate_sleep_time(
            sim_config.simulation_speed,
            sim_config.interval_seconds
        )

        logging.info(f"Simulation speed: {sim_config.simulation_speed}x")
        logging.info(f"Sleep time between readings: {sleep_time:.2f}s")

        # Start trading manager
        trading_manager = self.components['trading_manager']

        # Run simulation
        try:
            # Iterate through data
            for idx, (timestamp, row) in enumerate(data.iterrows()):
                # Get energy consumption (ensure it's a float)
                energy_demand = float(row['energy'])  # kWh

                # Create reading based on device type
                if self.device.is_prosumer:
                    # Get solar and storage data from hardware (or mock)
                    solar_manager = self.components.get('solar_monitor')
                    capacitor_manager = self.components.get('capacitor_manager')

                    # Get readings from hardware managers
                    solar_data = solar_manager.get_readings()
                    solar_energy = solar_data['solar_energy']  # kWh
                    solar_power = solar_data['solar_power']    # W

                    storage_level = capacitor_manager.get_soc() * 100  # Convert to percentage

                    # Calculate storage power (positive = charging, negative = discharging)
                    balance = solar_energy - energy_demand
                    if balance > 0:
                        # Surplus - try to charge
                        stored = capacitor_manager.charge(balance)
                        storage_power = stored * 2000  # Rough W conversion
                        balance -= stored
                    elif balance < 0:
                        # Deficit - try to discharge
                        discharged = capacitor_manager.discharge(abs(balance))
                        storage_power = -discharged * 2000  # Negative for discharge
                        balance += discharged
                    else:
                        storage_power = 0

                    reading = ProsumerReading(
                        timestamp=timestamp,
                        demand=energy_demand,
                        generation=solar_energy,
                        balance=balance,  # Final balance after storage
                        storage_level=storage_level,
                        storage_power=storage_power,
                        solar_power=solar_power
                    )

                    # Trading logic for prosumer
                    if reading.balance > 0.1:  # Surplus > 0.1 kWh
                        logging.info(f"Prosumer surplus: {reading.balance:.3f} kWh - creating trade offer")
                        # TODO: Create trade offer

                else:
                    # Consumer reading
                    reading = EnergyReading(
                        timestamp=timestamp,
                        demand=energy_demand,
                        balance=-energy_demand
                    )

                    # Trading logic for consumer
                    if reading.balance < -0.1:  # Deficit > 0.1 kWh
                        logging.info(f"Consumer deficit: {abs(reading.balance):.3f} kWh - creating trade request")
                        # TODO: Create trade request

                # Log current state every few readings
                if idx % 1 == 0:
                    log_msg = f"[{timestamp}] Demand: {reading.demand:.3f} kWh, Balance: {reading.balance:+.3f} kWh"
                    if self.device.is_prosumer:
                        log_msg += f", Gen: {reading.generation:.3f} kWh, SOC: {reading.storage_level:.1f}%"
                    print(log_msg, flush=True)  # Print to stdout
                    logging.info(log_msg)

                # Update LCD (if not mock mode)
                lcd = self.components.get('lcd')
                if lcd and not sim_config.mock_mode:
                    # TODO: Update LCD with current reading
                    pass

                # Update visualization
                # vis_manager = self.components.get('vis_manager')
                # if vis_manager:
                #     vis_manager.update(reading)

                # Sleep to maintain simulation speed
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logging.info("Simulation interrupted by user")
        finally:
            logging.info("Simulation loop completed")
        
    def cleanup(self):
        """Cleanup resources"""
        logging.info("Cleaning up...")
        for component in self.components.values():
            if hasattr(component, 'cleanup'):
                try:
                    component.cleanup()
                except Exception as e:
                    logging.error(f"Cleanup error: {e}")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='SolarVille Smart Grid Simulation')
    parser.add_argument('--config', type=str, default='config', help='Path to configuration directory')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode (required on non-Pi hardware)')
    parser.add_argument('--device', type=str, help='Device name to simulate (e.g., pi1, pi2). Overrides hostname matching.')
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()

    # Create and initialize SolarVille
    solarville = SolarVille()
    if not solarville.initialize(args.config, args.device):
        sys.exit(1)

    # Start simulation
    solarville.start()

if __name__ == "__main__":
    main()