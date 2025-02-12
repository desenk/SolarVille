# Branch: ProsumerJack
# File: hardware_manager.py

import time
from energy_types import ProsumerReading
from datetime import datetime
import logging
from dataAnalysis import get_current_readings, battery_charging, battery_supply

# set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class is used to manage the solar components of the system
class SolarMonitor:
    # scale_factor is used to adjust the solar energy readings
    def __init__(self, scale_factor=8000):
        self.scale_factor = scale_factor

    def get_readings(self):
        try:
            readings = get_current_readings()
            solar_power = readings['solar_power'] * self.scale_factor
            solar_energy = solar_power * 0.5 / 1000  # Convert to kWh for 30 minute interval

            return {
                'solar_power': solar_power,
                'solar_energy': solar_energy,
                'battery_voltage': readings['battery_voltage'],
                'battery_current': readings['battery_current'],
            }
        except Exception as e:
            logging.error(f"Failed to get solar data: {e}")
            return {
                'solar_power': 0,
                'solar_energy': 0,
                'battery_voltage': 0,
                'battery_current': 0,
            }

# class is used to manage the battery components of the system
class BatteryManager:
    def __init__(self, capacity=5.0, initial_soc=0.5):
        self.capacity = capacity
        self.soc = initial_soc
        self.depth_of_discharge = 0.8

    def charge(self, excess_energy):
        # Handle charging logic
        self.soc, sell_to_grid = battery_charging(
            excess_energy = excess_energy,
            battery_soc = self.soc,
            battery_capacity = self.capacity
        )
        return sell_to_grid
    
    def discharge(self, energy_needed):
        # Handle discharging logic
        self.soc,buy_from_grid = battery_supply(
            excess_energy = energy_needed,
            battery_soc = self.soc,
            battery_capacity = self.capacity,
            depth_of_discharge = self.depth_of_discharge
        )
        return buy_from_grid