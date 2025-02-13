# Branch: unified-main
# File: topology.py

from typing import Dict, List
from core.energy_types import PiDevice

class NetworkTopology:
    def __init__(self):
        self.devices: Dict[str, PiDevice] = {}
