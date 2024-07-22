import argparse
import time
import pandas as pd
from multiprocessing import Process, Queue, Event
import threading
import logging
import platform
import requests
from flask import request

# Conditionally import the correct modules based on the platform
if platform.system() == 'Darwin':  # MacOS
    from mock_batteryControl import update_battery_charge, read_battery_charge
    from mock_lcdControlTest import display_message
else:  # Raspberry Pi
    from batteryControl import update_battery_charge, read_battery_charge
    from lcdControlTest import display_message

from dataAnalysis import load_data, calculate_end_date, simulate_generation, update_plot_separate, update_plot_same
from trading import execute_trades, calculate_price

peer_ip = '192.168.233.24' # IP address of Pi #2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def synchronize_start(peer_ip):
    current_time = time.time()
    start_time = current_time + 10  # Start 10 seconds from now
    
    # Set start time on this Pi
    response = requests.post(f'http://localhost:5000/sync_start', json={"start_time": start_time})
    
    # Set start time on peer Pi
    peer_response = requests.post(f'http://{peer_ip}:5000/sync_start', json={"start_time": start_time})
    
    if response.status_code == 200 and peer_response.status_code == 200:
        logging.info(f"Simulation will start at {time.ctime(start_time)}")
        wait_time = start_time - time.time()
        if wait_time > 0:
            time.sleep(wait_time)
    else:
        logging.error("Failed to synchronize start times")

def start_simulation_local():
    synchronize_start(peer_ip)
    logging.info("Loading data, please wait...")
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
        while True:
            timestamp = queue.get()
            if timestamp == "done":
                break

            current_data = df[df.index == timestamp]
            
            if not current_data.empty:
                start_update_time = time.time()
                trading_thread = threading.Thread(target=process_trading_and_lcd, args=(df, timestamp, current_data, current_data['battery_charge'].iloc[0], peer_ip))
                trading_thread.start()
                trading_thread.join()

                logging.info(f"Update completed in {time.time() - start_update_time:.2f} seconds")
                
                # Periodically sync state
                if timestamp.second % 6 == 0:  # Example: sync every 5 minutes
                    logging.info(f"Syncing state with peer {peer_ip}")
                    sync_state(df, peer_ip)
                    logging.info(f"State synced with peer {peer_ip}")

    except KeyboardInterrupt:
        logging.info("Simulation interrupted.")
    finally:
        plot_process.join()

def plot_data(df, start_date, end_date, timescale, separate, queue, ready_event):
    if separate:
        update_plot_separate(df, start_date, end_date, timescale, queue, ready_event)
    else:
        update_plot_same(df, start_date, end_date, timescale, queue, ready_event)

def process_trading_and_lcd(df, timestamp, current_data, battery_charge, peer_ip):
    demand = current_data['energy'].sum()
    df.loc[df.index == timestamp, 'demand'] = demand
    battery_charge = update_battery_charge(current_data['generation'].sum(), demand)
    df.loc[df.index == timestamp, 'battery_charge'] = battery_charge

    df, price = execute_trades(df, timestamp)
    display_message(f"Gen: {current_data['generation'].sum():.2f}W\nDem: {demand:.2f}W\nBat: {battery_charge * 100:.2f}%")
    
    logging.info(
        f"At {timestamp} - Generation: {current_data['generation'].sum():.2f}W, "
        f"Demand: {demand:.2f}W, Battery: {battery_charge * 100:.2f}%, "
        f"Price: {price:.2f}, Updated Balance: {df['balance'].sum():.2f}, "
        f"LCD updated"
    )

    # Send updates to Flask server
    update_demand = make_api_call(f'http://{peer_ip}:5000/update_demand', {'demand': demand})
    update_generation = make_api_call(f'http://{peer_ip}:5000/update_generation', {'generation': current_data['generation'].sum()})
    update_balance = make_api_call(f'http://{peer_ip}:5000/update_balance', {'amount': df['balance'].sum()})

    if update_demand is None or update_generation is None or update_balance is None:
        logging.error(f"Failed to update peer {peer_ip} with latest data")

    return df, battery_charge

def sync_state(df, peer_ip):
    state = {
        'balance': df['balance'].sum(),
        'currency': df['currency'].sum(),
        'demand': df['demand'].sum(),
        'generation': df['generation'].sum()
    }
    response = make_api_call(f'http://{peer_ip}:5000/sync', state)
    if response is None:
        logging.error(f"Failed to sync state with peer {peer_ip}")

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