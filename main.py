import argparse
import time
import pandas as pd
from multiprocessing import Process, Queue, Event
import threading
import logging
import platform
import requests
from flask import Flask, request, jsonify

# Conditionally import the correct modules based on the platform
if platform.system() == 'Darwin':  # MacOS
    from mock_batteryControl import update_battery_charge, read_battery_charge
    from mock_lcdControlTest import display_message
else:  # Raspberry Pi
    from batteryControl import update_battery_charge, read_battery_charge
    from lcdControlTest import display_message

from dataAnalysis import load_data, calculate_end_date, simulate_generation, update_plot_separate, update_plot_same
from trading import execute_trades, calculate_price

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Shared data for the example
energy_data = {
    "balance": 0,
    "currency": 100.0,
    "demand": 0,
    "generation": 0
}

@app.route('/start', methods=['POST'])
def start():
    start_simulation_local()
    return jsonify({"status": "Simulation started"})

@app.route('/get_data', methods=['GET'])
def get_data():
    global energy_data
    return jsonify(energy_data)

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    peers = request.json.get('peers', [])
    # Start simulation on self
    start_simulation_local()
    # Start simulation on peers
    for peer in peers:
        response = requests.post(f'http://{peer}:5000/start')
        if response.status_code != 200:
            logging.error(f"Failed to start simulation on peer {peer}")
    return jsonify({"status": "Simulation started on all peers"})

def start_simulation_local():
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

    peer_ip = '192.168.170.63'  # IP address of the Raspberry Pi #2

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
                if timestamp.minute % 5 == 0:  # Example: sync every 5 minutes
                    sync_state(df, peer_ip)

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
    requests.post(f'http://{peer_ip}:5000/update_demand', json={'demand': demand})
    requests.post(f'http://{peer_ip}:5000/update_generation', json={'generation': current_data['generation'].sum()})
    requests.post(f'http://{peer_ip}:5000/update_balance', json={'amount': df['balance'].sum()})

    return df, battery_charge

def sync_state(df, peer_ip):
    state = {
        'balance': df['balance'].sum(),
        'currency': df['currency'].sum(),
        'demand': df['demand'].sum(),
        'generation': df['generation'].sum()
    }
    requests.post(f'http://{peer_ip}:5000/sync', json=state)

@app.route('/update_balance', methods=['POST'])
def update_balance():
    global energy_data
    data = request.json
    energy_data['balance'] += data.get('amount', 0)
    return jsonify(energy_data)

@app.route('/update_demand', methods=['POST'])
def update_demand():
    global energy_data
    data = request.json
    energy_data['demand'] = data.get('demand', 0)
    return jsonify(energy_data)

@app.route('/update_generation', methods=['POST'])
def update_generation():
    global energy_data
    data = request.json
    energy_data['generation'] = data.get('generation', 0)
    return jsonify(energy_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Smart Grid Simulation')
    parser.add_argument('--file_path', type=str, required=True, help='Path to the CSV file')
    parser.add_argument('--household', type=str, required=True, help='Household ID for the data')
    parser.add_argument('--start_date', type=str, required=True, help='Start date for the simulation')
    parser.add_argument('--timescale', type=str, required=True, choices=['d', 'w', 'm', 'y'], help='Timescale: d for day, w for week, m for month, y for year')
    parser.add_argument('--separate', action='store_true', help='Flag to plot data in separate subplots')

    args = parser.parse_args()  # Parse the arguments
    app.run(host='0.0.0.0', port=5000)  # Start the Flask server