import argparse
import time
import pandas as pd # type: ignore
from multiprocessing import Process, Queue, Event
import threading
import logging
import platform
import requests
from flask import request
from pricing import calculate_price
from dataAnalysis import load_data, calculate_end_date, update_plot_separate, update_plot_same
from config import LOCAL_IP, PEER_IP
from solarMonitor import get_current_readings
from battery_energy_management import battery_charging, battery_supply
from lcdControlTest import display_message

SOLAR_SCALE_FACTOR = 8000  # Adjust this value as needed
trade_amount = 0
battery_soc = 0.5

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_simulation_local():
    if not synchronize_start():
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
    
    global trade_amount
    global battery_soc
    

    df['generation'] = 0.0  # Initialize generation column
    df['balance'] = 0.0  # Initialize balance column
    df['currency'] = 0  # Initialize the currency column to 0
    df['battery_charge'] = 0.5  # Assume 50% initial charge
    
    end_date = calculate_end_date(args.start_date, args.timescale)
    logging.info(f"Data loaded in {time.time() - start_time:.2f} seconds")
    
    queue = Queue()
    ready_event = Event()
    plot_process = Process(target=plot_data, args=(df, args.start_date, end_date, args.timescale, args.separate, queue, ready_event))
    plot_process.start()
    
    # Wait for the plotting process to signal that it is ready
    ready_event.wait()
    logging.info("Plot initialized, starting simulation...")

    logging.info("Dataframe for generation, balance, currency and battery charge is created.")
    
    plot_update_interval = 6  # seconds
    last_plot_update = time.time()
    
    total_simulation_time = (df.index[-1] - df.index[0]).total_seconds()
    simulation_speed = 30 * 60 / 6  # 30 minutes of data in 6 seconds of simulation

    try:
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            simulated_elapsed_time = elapsed_time * simulation_speed
            
            if simulated_elapsed_time >= total_simulation_time:
                logging.info("Simulation completed.")
                break
            
            timestamp_index = int(simulated_elapsed_time / (30 * 60))  # 30-minute intervals
            if timestamp_index >= len(df.index):
                logging.info("Reached end of data. Simulation completed.")
                break
            
            timestamp = df.index[timestamp_index]
            current_data = df.loc[timestamp]
            
            if not current_data.empty:
                df = process_trading_and_lcd(df, timestamp, current_data)
                
                if current_time - last_plot_update >= plot_update_interval:
                    queue.put({
                        'timestamp': timestamp,
                        'generation': df.loc[timestamp, 'generation']
                    })
                    last_plot_update = current_time
            
            time.sleep(0.1)  # Small sleep to prevent CPU overuse

    except KeyboardInterrupt:
        logging.info("Simulation interrupted.")
    finally:
        queue.put("done")
        plot_process.join()

def synchronize_start():
    current_time = time.time()
    start_time = current_time + 10  # Start 20 seconds from now
    
    try:
        peers = [LOCAL_IP, PEER_IP]  # List of both IPs
        
        # Set start time on both Pis
        response = requests.post('http://localhost:5000/sync_start', json={"start_time": start_time, "peers": peers})
        peer_response = requests.post(f'http://{PEER_IP}:5000/sync_start', json={"start_time": start_time, "peers": peers})
        
        if response.status_code == 200 and peer_response.status_code == 200:
            logging.info(f"Simulation will start at {time.ctime(start_time)}")
            
            # Wait until it's time to start
            wait_time = start_time - time.time()
            if wait_time > 0:
                logging.info(f"Waiting for {wait_time:.2f} seconds before starting simulation")
                time.sleep(wait_time)
            
            # Start the simulation
            simulation_start_time = time.time()
            requests.post('http://localhost:5000/start_simulation', json={'start_time': simulation_start_time})
            requests.post(f'http://{PEER_IP}:5000/start_simulation', json={'start_time': simulation_start_time})
            
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

def process_trading_and_lcd(df, timestamp, current_data):
    try:
        readings = get_current_readings()
        solar_power = readings['solar_power'] * SOLAR_SCALE_FACTOR# unit: W
        # Assume the solar power remains the same in every half hour
        solar_energy = solar_power * 0.5 / 1000 # unit: kWh
    except Exception as e:
        logging.error(f"Failed to get solar data: {e}")
        solar_power = 0
        solar_energy = 0

    global trade_amount
    global battery_soc
    
    demand = current_data['energy'] # unit kWh

    sell_grid_price = calculate_price(solar_energy, demand)
    peer_price = calculate_price(solar_energy, demand)
    buy_grid_price = calculate_price(solar_energy, demand)
    
    # Log the calculated prices
    logging.info(f"Calculated prices - Sell Grid Price: {sell_grid_price:.2f} ￡/kWh, "
                 f"Peer Price: {peer_price:.2f} ￡/kWh, "
                 f"Buy Grid Price: {buy_grid_price:.2f} ￡/kWh")

    # Calculate balance unit kWh
    balance = solar_energy - demand
    
    # Update dataframe
    df.loc[timestamp, ['generation', 'demand', 'balance']] = [solar_energy, demand, balance]

    # Send updates to Flask server
    update_data_1 = {
        'demand': demand,
        'generation': solar_energy,
        'balance': balance,
        'battery SoC': battery_soc,
        'enable': 0  # Disable trading
    }
    make_api_call(f'http://{PEER_IP}:5000/update_peer_data', update_data_1)

    # Get peer data for trading
    peer_data_response = requests.get(f'http://{PEER_IP}:5000/get_peer_data')
    if peer_data_response.status_code == 200:
        peer_data = peer_data_response.json()
        
        # Get peer balance with error checking
        peer_balance = peer_data.get(PEER_IP, {}).get('balance')
        if peer_balance is None:
            logging.warning(f"No balance data available for peer {PEER_IP}")
        else:
            # Perform trading (now in kilo Watt-hours)
            if balance >= 0:
                # The household has excess energy
                if peer_balance >= 0:
                    battery_soc, sell_to_grid = battery_charging(excess_energy=balance, battery_soc=battery_soc, battery_capacity = 5)
                    # the other household has excess energy too, this household energy can sell to grid
                    df.loc[timestamp, ['balance', 'currency', 'battery_charge']] = [
                        df.loc[timestamp, 'balance'] - balance,  # update balance
                        df.loc[timestamp, 'currency'] + sell_to_grid * sell_grid_price,  # update currency
                        battery_soc  # update battery_charge
                    ]

                    logging.info(f"Sold {balance*1000:.2f} Wh to the grid at {sell_grid_price:.2f} ￡/kWh")
                elif peer_balance < 0:
                    # the other household needs energy
                    if balance > abs(peer_balance):
                        # energy is enough to supply the other household
                        trade_amount = abs(peer_balance)
                        remaining_balance = balance - trade_amount
                        battery_soc, sell_to_grid = battery_charging(excess_energy=remaining_balance, battery_soc=battery_soc, battery_capacity = 5)
                        df.loc[timestamp, ['balance', 'currency', 'battery_charge']] = [
                            df.loc[timestamp, 'balance'] - balance,  # update balance 
                            df.loc[timestamp, 'currency'] + (trade_amount * peer_price) + (sell_to_grid * sell_grid_price), # update currency
                            battery_soc  # update battery_charge
                        ]
                        logging.info(f"Sold {trade_amount*1000:.2f} Wh to peer at {peer_price:.2f} ￡/kWh and the remaining {sell_to_grid*1000:.2f} Wh to the grid at {sell_grid_price:.2f} ￡/kWh")
                    else:
                        # energy can only supply part of the need of the other household
                        trade_amount = balance
                        df.loc[timestamp, ['balance', 'currency', 'battery_charge']] = [
                            df.loc[timestamp, 'balance'] - balance,  # update balance
                            df.loc[timestamp, 'currency'] + trade_amount * peer_price, # update currency
                            battery_soc  # update battery_charge
                        ]
                        logging.info(f"Sold {trade_amount*1000:.2f} Wh to peer at {peer_price:.2f} ￡/kWh")
            elif balance < 0:
                #test if the program can run to this point
                logging.info(f"need electricity")
                # the household needs energy
                battery_soc, buy_from_grid = battery_supply(excess_energy = balance, battery_soc = battery_soc, battery_capacity = 5, depth_of_discharge=0.8)
                
                logging.info(f"Updating DataFrame at timestamp: {timestamp}, Current balance: {df.loc[timestamp, 'balance']},"
                             f" Current currency: {df.loc[timestamp, 'currency']},"
                             f"buy_from_grid: {buy_from_grid},buy_grid_price:{buy_grid_price}")
                df.loc[timestamp, ['balance', 'currency', 'battery_charge']] = [
                    df.loc[timestamp, 'balance'] - balance,  # update balance
                    df.loc[timestamp, 'currency'] - buy_from_grid * buy_grid_price, # update currency
                    battery_soc  # update battery_charge
                ]
                logging.info(f"Bought {buy_from_grid*1000:.2f} Wh from grid at {buy_grid_price:.2f} ￡/kWh")
    else:
        logging.error("Failed to get peer data for trading")

    # Update LCD display
    display_message(f"Bat:{battery_soc*100:.0f}% Gen:{solar_power:.0f}W")
    
    logging.info(
        f"At {timestamp} - Generation: {solar_power:.6f}W, "
        f"Demand: {demand:.2f}kWh, Battery: {battery_soc*100:.2f}%, "
        f"Balance: {df.loc[timestamp, 'balance']:.6f}kWh, "
        f"Currency: {df.loc[timestamp, 'currency']:.2f}, "
        f"LCD updated"
    )
    # Send updates to Flask server
    update_data_2 = {
        'battery_charge': battery_soc,
        'trade_amount': trade_amount,
        'buy_grid_price':buy_grid_price,
        'peer_price':peer_price,
        'enable': 1  # Enable trading
    }
    make_api_call(f'http://{PEER_IP}:5000/update_trade_data', update_data_2)
    

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
    df['generation'] = 0.0  # Initialize generation column
    df['balance'] = 0.0  # Initialize balance column
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
