import argparse
import time
import pandas as pd # type: ignore
from multiprocessing import Process, Queue, Event
import threading
import logging
import platform
import requests
from flask import request
from trading import calculate_price
from dataAnalysis import load_data, calculate_end_date, simulate_generation, update_plot_separate, update_plot_same

max_battery_charge = 1.0
min_battery_charge = 0.0

# Conditionally import the correct modules based on the platform
if platform.system() == 'Darwin':  # MacOS
    from mock_batteryControl import update_battery_charge, read_battery_charge
    from mock_lcdControlTest import display_message
else:  # Raspberry Pi
    from batteryControl import update_battery_charge, read_battery_charge
    from lcdControlTest import display_message

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_simulation_local():
    peer_ip = '192.168.245.64'  # IP address of Pi #2
    if not synchronize_start(peer_ip):
        logging.error('Failed to start simulation')
        return
    
    # Wait for the simulation to start
    response = requests.get('http://localhost:5000/wait_for_start')
    if response.status_code != 200:
        logging.error('Failed to start simulation')
        return
    
    start_time = time.time()

    df = load_data(args.file_path, args.household, args.start_date, args.timescale)
    if df.empty:
        logging.error("No data loaded. Exiting simulation.")
        return
    df = simulate_generation(df, mean=0.5, std=0.2)
    end_date = calculate_end_date(args.start_date, args.timescale)
    logging.info(f"Data loaded in {time.time() - start_time:.2f} seconds")
    
    queue = Queue()
    ready_event = Event()
    plot_process = Process(target=plot_data, args=(df, args.start_date, end_date, args.timescale, args.separate, queue, ready_event))
    plot_process.start()
    
    # Wait for the plotting process to signal that it is ready
    ready_event.wait()
    logging.info("Plot initialized, starting simulation...")

    df['balance'] = df['generation'] - df['energy']  # Calculate the balance for each row
    df['currency'] = 100.0  # Initialize the currency column to 100
    df['battery_charge'] = 0.5  # Assume 50% initial charge
    logging.info("Dataframe for balance, currency and battery charge is created.")
    
    try:
        for timestamp in df.index:
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Calculate the expected elapsed time based on the simulation speed
            expected_elapsed_time = (timestamp - df.index[0]).total_seconds() * (6 / 3600)  # 6 seconds per hour
            
            # If we're ahead of schedule, wait
            if elapsed_time < expected_elapsed_time:
                time.sleep(expected_elapsed_time - elapsed_time)
            
            current_data = df.loc[timestamp]
            
            if not current_data.empty:
                df = process_trading_and_lcd(df, timestamp, current_data, current_data['battery_charge'], peer_ip)
                
                # Update the plot
                queue.put(timestamp)

    except KeyboardInterrupt:
        logging.info("Simulation interrupted.")
    finally:
        queue.put("done")
        plot_process.join()

import random
import numpy as np

def synchronize_start(peer_ip):
    current_time = time.time()
    start_time = current_time + 20  # Start 20 seconds from now
    
    try:
        local_ip = '192.168.233.200'  # IP address of Pi #1
        peers = [local_ip, peer_ip]  # List of both IPs
        
        # Set start time on both Pis
        response = requests.post('http://localhost:5000/sync_start', json={"start_time": start_time, "peers": peers})
        peer_response = requests.post(f'http://{peer_ip}:5000/sync_start', json={"start_time": start_time, "peers": peers})
        
        if response.status_code == 200 and peer_response.status_code == 200:
            logging.info(f"Simulation will start at {time.ctime(start_time)}")
            
            # Set a fixed seed for random number generation
            random.seed(42)
            np.random.seed(42)
            
            # Wait until it's time to start
            wait_time = start_time - time.time()
            if wait_time > 0:
                logging.info(f"Waiting for {wait_time:.2f} seconds before starting simulation")
                time.sleep(wait_time)
            
            # Start the simulation
            simulation_start_time = time.time()
            requests.post('http://localhost:5000/start_simulation', json={'start_time': simulation_start_time})
            requests.post(f'http://{peer_ip}:5000/start_simulation', json={'start_time': simulation_start_time})
            
            logging.info("Starting simulation now")
            return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error during synchronization: {e}")
    
    logging.error("Failed to start simulation")
    return False

def plot_data(df, start_date, end_date, timescale, separate, queue, ready_event):
    if separate:
        update_plot_separate(df, start_date, end_date, timescale, queue, ready_event)
    else:
        update_plot_same(df, start_date, end_date, timescale, queue, ready_event)

def process_trading_and_lcd(df, timestamp, current_data, battery_charge, peer_ip):
    demand = current_data['energy']
    generation = current_data['generation']
    balance = generation - demand
    df.loc[timestamp, 'demand'] = demand
    df.loc[timestamp, 'generation'] = generation
    df.loc[timestamp, 'balance'] = balance
    
    battery_charge = update_battery_charge(generation, demand)
    df.loc[timestamp, 'battery_charge'] = battery_charge

    # Send updates to Flask server
    update_data = {
        'demand': demand,
        'generation': generation,
        'balance': balance,
        'battery_charge': battery_charge
    }
    make_api_call(f'http://{peer_ip}:5000/update_peer_data', update_data)

    # Get peer data for trading
    peer_data_response = requests.get(f'http://{peer_ip}:5000/get_peer_data')
    if peer_data_response.status_code == 200:
        peer_data = peer_data_response.json()
        
        # Get peer balance with error checking
        peer_balance = peer_data.get(peer_ip, {}).get('balance')
        if peer_balance is None:
            logging.warning(f"No balance data available for peer {peer_ip}")
        else:
            # Perform trading
            if balance > 0 and peer_balance < 0:
                # This household has excess energy to sell
                trade_amount = min(balance, abs(peer_balance))
                price = calculate_price(balance, abs(peer_balance))
                df.loc[timestamp, 'balance'] -= trade_amount
                df.loc[timestamp, 'currency'] += trade_amount * price
                logging.info(f"Sold {trade_amount:.2f} kWh at {price:.2f} $/kWh")
            elif balance < 0 and peer_balance > 0:
                # This household needs to buy energy
                trade_amount = min(abs(balance), peer_balance)
                price = calculate_price(peer_balance, abs(balance))
                df.loc[timestamp, 'balance'] += trade_amount
                df.loc[timestamp, 'currency'] -= trade_amount * price
                logging.info(f"Bought {trade_amount:.2f} kWh at {price:.2f} $/kWh")
    else:
        logging.error("Failed to get peer data for trading")

    # Update LCD display
    display_message(f"Gen: {generation:.2f}W\nDem: {demand:.2f}W\nBat: {battery_charge * 100:.2f}%")
    
    logging.info(
        f"At {timestamp} - Generation: {generation:.2f}W, "
        f"Demand: {demand:.2f}W, Battery: {battery_charge * 100:.2f}%, "
        f"Balance: {df.loc[timestamp, 'balance']:.2f}, "
        f"Currency: {df.loc[timestamp, 'currency']:.2f}, "
        f"LCD updated"
    )

    return df

def make_api_call(url, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=5)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logging.error(f"Max retries reached for {url}")
    return None

def initialize_simulation():
    global df, end_date
    logging.info("Loading data, please wait...")
    start_time = time.time()
    df = load_data(args.file_path, args.household, args.start_date, args.timescale)
    if df.empty:
        logging.error("No data loaded. Exiting simulation.")
        return
    df = simulate_generation(df, mean=0.5, std=0.2)
    end_date = calculate_end_date(args.start_date, args.timescale)
    logging.info(f"Data loaded in {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Smart Grid Simulation')
    parser.add_argument('--file_path', type=str, required=True, help='Path to the CSV file')
    parser.add_argument('--household', type=str, required=True, help='Household ID for the data')
    parser.add_argument('--start_date', type=str, required=True, help='Start date for the simulation')
    parser.add_argument('--timescale', type=str, required=True, choices=['d', 'w', 'm', 'y'], help='Timescale: d for day, w for week, m for month, y for year')
    parser.add_argument('--separate', action='store_true', help='Flag to plot data in separate subplots')

    args = parser.parse_args()  # Parse the arguments
    initialize_simulation()

    from server import app
    server_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    server_thread.start()
    
    time.sleep(2)  # Give the server a moment to start
    
    simulation_thread = threading.Thread(target=start_simulation_local)
    simulation_thread.start()
    
    simulation_thread.join()
    server_thread.join()