#!/bin/bash

# Create main directories
mkdir -p unified-main/{core,hardware,network,simulation,utils,config}

# Create core files
cat > unified-main/core/energy_types.py << 'EOF'
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class EnergyReading:
    timestamp: datetime
    demand: float      # kWh
    balance: float     # kWh (negative for consumers)

@dataclass
class PiDevice:
    name: str
    ip_address: str
    is_prosumer: bool
    hostname: str
    location: Optional[str] = None
EOF

cat > unified-main/core/config.py << 'EOF'
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
EOF

cat > unified-main/core/constants.py << 'EOF'
# Network Constants
DEFAULT_PORT = 5000
RETRY_ATTEMPTS = 3
TIMEOUT_SECONDS = 5

# Energy Constants
GRID_BUY_PRICE = 0.25  # £/kWh
GRID_SELL_PRICE = 0.05  # £/kWh

# Hardware Constants
LCD_ROWS = 2
LCD_COLS = 16
EOF

# Create hardware files
cat > unified-main/hardware/lcd_manager.py << 'EOF'
import logging
from typing import Optional

class LCDManager:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._initialize_display()
EOF

cat > unified-main/hardware/solar_manager.py << 'EOF'
import logging
from typing import Dict

class SolarMonitor:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._initialize_sensors()
EOF

cat > unified-main/hardware/capacitor_manager.py << 'EOF'
import logging

class CapacitorManager:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._initialize_capacitors()
EOF

# Create network files
cat > unified-main/network/server.py << 'EOF'
from flask import Flask, request, jsonify
import logging
from threading import Event

app = Flask(__name__)
EOF

cat > unified-main/network/trading_integration.py << 'EOF'
import requests
import logging
from typing import Optional, Dict

class TradingIntegration:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.session = requests.Session()
EOF

cat > unified-main/network/topology.py << 'EOF'
from typing import Dict, List
from core.energy_types import PiDevice

class NetworkTopology:
    def __init__(self):
        self.devices: Dict[str, PiDevice] = {}
EOF

cat > unified-main/network/discovery.py << 'EOF'
import logging
from typing import List
from core.energy_types import PiDevice

class PeerDiscovery:
    def __init__(self):
        self.known_peers: List[PiDevice] = []
EOF

cat > unified-main/network/health_check.py << 'EOF'
import logging
import requests
from typing import Dict

class HealthChecker:
    def __init__(self):
        self.health_status: Dict[str, bool] = {}
EOF

# Create simulation files
cat > unified-main/simulation/trading_manager.py << 'EOF'
import logging
from typing import Optional
from core.energy_types import EnergyReading

class TradingManager:
    def __init__(self, is_prosumer: bool):
        self.is_prosumer = is_prosumer
EOF

cat > unified-main/simulation/visualisation_manager.py << 'EOF'
from multiprocessing import Process, Queue, Event
import logging

class VisualisationManager:
    def __init__(self, start_date: str, timescale: str):
        self.queue = Queue()
        self.ready_event = Event()
EOF

cat > unified-main/simulation/data_analysis.py << 'EOF'
import pandas as pd
import logging
from typing import Optional

def load_data(file_path: str, household: str) -> Optional[pd.DataFrame]:
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        return None
EOF

# Create utils files
cat > unified-main/utils/error_handling.py << 'EOF'
import logging
from typing import Optional

class ErrorHandler:
    @staticmethod
    def handle_error(error: Exception, context: str) -> None:
        logging.error(f"Error in {context}: {str(error)}")
EOF

cat > unified-main/utils/logging.py << 'EOF'
import logging
from typing import Optional

def setup_logging(log_level: Optional[str] = None) -> None:
    level = getattr(logging, log_level or 'INFO')
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
EOF

# Create config files
cat > unified-main/config/network_topology.yml << 'EOF'
devices:
  pi1:
    name: pi1
    ip_address: 10.126.56.181
    is_prosumer: true
    hostname: prosumer-pi-1
    location: Lab Bench 1
  pi2:
    name: pi2
    ip_address: 10.126.167.128
    is_prosumer: false
    hostname: consumer-pi-1
    location: Lab Bench 2
EOF

cat > unified-main/config/simulation.yml << 'EOF'
simulation:
  file_path: data/block_0.csv
  start_date: 2012-10-24
  timescale: d
  simulation_speed: 300
  timeout: 5

hardware:
  mock_mode: true
  lcd_enabled: true
  solar_enabled: true
EOF

echo "Directory structure created successfully!"