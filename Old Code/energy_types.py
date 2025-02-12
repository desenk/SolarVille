# Branch: ProsumerJack
# File: energy_types.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class EnergyReading:
    # Base class for energy readings - used by both consumer and prosumer
    timestamp: datetime
    demand: float      # kWh - energy demanded in this timestep
    balance: float     # kWh - net energy balance (may be negative)

@dataclass
class ProsumerReading(EnergyReading):
    # Extended class for prosumer readings - includes generation and battery data
    generation: float      # kWh - solar energy generated
    battery_soc: float     # 0-1 percentage - battery state of charge
    solar_power: float     # W - instantaneous power from solar
    battery_voltage: float # V - battery voltage

@dataclass
class TradeData:
    # Class for storing trade information
    amount: float         # kWh - amount of energy to trade
    price: float         # £/kWh - price per unit
    grid_buy_price: float = 0.25   # Default grid buying price
    grid_sell_price: float = 0.05  # Default grid selling price