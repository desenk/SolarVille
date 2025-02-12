"""Energy-related data structures for the SolarVille system."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class EnergyReading:
    """Base energy reading containing common fields"""
    timestamp: datetime
    demand: float      # kWh - energy demanded in this timestep
    balance: float     # kWh - net energy balance (negative for consumers)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "demand": self.demand,
            "balance": self.balance
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EnergyReading':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            demand=data["demand"],
            balance=data["balance"]
        )

@dataclass
class ProsumerReading(EnergyReading):
    """Extended energy reading for prosumers with generation and storage data"""
    generation: float          # kWh - solar energy generated
    storage_level: float      # % - capacitor charge level (0-100)
    storage_power: float      # W - current capacitor power (positive = charging)
    solar_power: float        # W - current solar panel output

    def to_dict(self) -> Dict:
        base_dict = super().to_dict()
        base_dict.update({
            "generation": self.generation,
            "storage_level": self.storage_level,
            "storage_power": self.storage_power,
            "solar_power": self.solar_power
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProsumerReading':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            demand=data["demand"],
            balance=data["balance"],
            generation=data["generation"],
            storage_level=data["storage_level"],
            storage_power=data["storage_power"],
            solar_power=data["solar_power"]
        )