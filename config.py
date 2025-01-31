# Branch: ProsumerJack
# File: config.py
import argparse
import logging
import os

# Environment detection
IS_TEST = os.getenv('SOLARVILLE_ENV') == 'testing'
IS_DEV = os.getenv('SOLARVILLE_ENV') == 'development'

# Configure logging level based on environment
if IS_TEST:
    logging.basicConfig(level=logging.WARNING)  # Reduce logging in tests
else:
    logging.basicConfig(level=logging.INFO)

# Try to import netifaces, use mock values if not available or in test mode
try:
    if IS_TEST:
        raise ImportError("Skip netifaces in test mode")
    import netifaces  # type: ignore
    MOCK_NETWORK = False
except ImportError:
    MOCK_NETWORK = True
    if not IS_TEST:  # Only log warning if not in test mode
        logging.warning("netifaces not available, using mock network configuration")

# Network Configuration
PI_1_IP = '10.126.56.181'  # IP of Pi 1 (prosumer)
PI_2_IP = '10.126.167.128'  # IP of Pi 2 (consumer)

# Simulation Configuration
SIMULATION_SPEEDUP = 300    # Factor to speed up simulation (300 = 15min data every 3s)
DEFAULT_TIMESCALES = {
    'd': 'day',
    'w': 'week',
    'm': 'month',
    'y': 'year'
}

# Energy Trading Configuration
GRID_BUY_PRICE = 0.25      # £/kWh
GRID_SELL_PRICE = 0.05     # £/kWh

def get_network_ip():
    """Get the non-loopback IP address of the machine."""
    if MOCK_NETWORK or IS_TEST:
        return '127.0.0.1'
        
    try:
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            if interface == 'lo':
                continue
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                ip = addrs[netifaces.AF_INET][0]['addr']
                if ip != '127.0.0.1':
                    return ip
    except Exception as e:
        if not IS_TEST:  # Only log in non-test environment
            logging.error(f"Error getting network IP: {e}")
    return None

def get_local_and_peer_ip():
    """Determine local and peer IP addresses based on network IP."""
    if IS_TEST:
        return '127.0.0.1', '127.0.0.1'
        
    local_ip = get_network_ip()
    if local_ip:
        if local_ip == PI_1_IP:
            return PI_1_IP, PI_2_IP
        elif local_ip == PI_2_IP:
            return PI_2_IP, PI_1_IP
    
    if not IS_TEST:  # Only log in non-test environment
        logging.error("Failed to determine IP addresses")
    return None, None