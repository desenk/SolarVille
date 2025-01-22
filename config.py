# Branch: consumerJack
# File: config.py

import argparse
import netifaces # type: ignore
import logging

# Network Configuration
PI_1_IP = '10.126.56.181'  # IP of Pi 1 (prosumer)
PI_2_IP = '10.126.167.128'   # IP of Pi 2 (consumer)

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
    try:
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            if interface == 'lo':
                continue
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                ip = addrs[netifaces.AF_INET][0]['addr']
                if ip != '127.0.0.1':
                    logging.info(f"Network IP: {ip}")
                    return ip
    except Exception as e:
        logging.error(f"Error getting network IP: {e}")
    return None

def get_local_and_peer_ip():
    """Determine local and peer IP addresses based on network IP."""
    local_ip = get_network_ip()
    if local_ip:
        if local_ip == PI_1_IP:
            return PI_1_IP, PI_2_IP
        elif local_ip == PI_2_IP:
            return PI_2_IP, PI_1_IP
    return None, None

def validate_date(date_str):
    """Validate date string format (YYYY-MM-DD)."""
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def validate_timescale(timescale):
    """Validate timescale argument."""
    if timescale not in DEFAULT_TIMESCALES:
        raise argparse.ArgumentTypeError(
            f"Invalid timescale: {timescale}. Use {', '.join(DEFAULT_TIMESCALES.keys())}"
        )
    return timescale

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Smart Grid Simulation')
    
    parser.add_argument(
        '--file_path',
        type=str,
        required=True,
        help='Path to the CSV file containing energy data'
    )
    
    parser.add_argument(
        '--household',
        type=str,
        required=True,
        help='Household ID for the data'
    )
    
    parser.add_argument(
        '--start_date',
        type=validate_date,
        required=True,
        help='Start date for the simulation (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--timescale',
        type=validate_timescale,
        required=True,
        choices=['d', 'w', 'm', 'y'],
        help='Timescale: d for day, w for week, m for month, y for year'
    )
    
    parser.add_argument(
        '--speed',
        type=float,
        default=SIMULATION_SPEEDUP,
        help=f'Simulation speed factor (default: {SIMULATION_SPEEDUP})'
    )
    
    args = parser.parse_args()
    
    # Log the configuration
    logging.info(f"Configuration:")
    logging.info(f"  File path: {args.file_path}")
    logging.info(f"  Household: {args.household}")
    logging.info(f"  Start date: {args.start_date}")
    logging.info(f"  Timescale: {DEFAULT_TIMESCALES[args.timescale]}")
    logging.info(f"  Speed factor: {args.speed}")
    
    return args

# Initialize network configuration
LOCAL_IP, PEER_IP = get_local_and_peer_ip()
if LOCAL_IP and PEER_IP:
    logging.info(f"Local IP: {LOCAL_IP}")
    logging.info(f"Peer IP: {PEER_IP}")
else:
    logging.error("Failed to determine IP addresses")