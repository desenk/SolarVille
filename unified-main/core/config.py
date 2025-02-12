from dataclasses import dataclass
from typing import Optional
import argparse
import yaml

@dataclass
class SimulationConfig:
    file_path: str = "data/block_0.csv"
    start_date: str = "2012-10-24"
    timescale: str = "d"
    simulation_speed: int = 300
    timeout: int = 5

class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/default.yml"
        self.sim_config = SimulationConfig()
        self.network_config = {}
