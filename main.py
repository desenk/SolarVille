import argparse
import time
import pandas as pd # type: ignore
from multiprocessing import Process, Queue, Event
import threading
import logging
import platform
import requests
from io import StringIO
from pricing import calculate_price
from dataAnalysis import load_data, calculate_end_date, update_plot_separate, update_plot_same
from config import LOCAL_IP, PEER_IP
from battery_energy_management import battery_charging, battery_supply
from lcdControlTest import display_message

SOLAR_SCALE_FACTOR = 4000  # Adjust this value as needed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_simulation_local(args):

    df = load_data(args.file_path, args.household, args.start_date, args.timescale)
    if df.empty:
        logging.error("No data loaded. Exiting simulation.")
        return
    
    
    df['balance'] = 0.0  # Initialize balance column
    df['currency'] = 0  # Initialize the currency column to 0
    
    end_date = calculate_end_date(args.start_date, args.timescale)
    total_simulation_time = (df.index[-1] - df.index[0]).total_seconds()
    simulation_speed = 30 * 60 / 6  # 30 minutes of data in 6 seconds of simulation
    logging.info(f"Data loaded in {time.time() - start_time:.2f} seconds")
    
    queue = Queue()
    ready_event = Event()
    plot_process = Process(target=update_plot_same, args=(df, args.start_date, end_date, args.timescale, queue, ready_event))
    plot_process.start()
    
    # Wait for the plotting process to signal that it is ready
    ready_event.wait()
    logging.info("Plot initialized, starting simulation...")

    logging.info("Dataframe for balance, currency and battery charge is created.")
    
    start_time = time.time()

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
                df = process_trading_and_lcd(df, timestamp, current_data, queue)

            time.sleep(1)  # Small sleep to prevent CPU overuse

    except KeyboardInterrupt:
        logging.info("Simulation interrupted.")
    finally:
        queue.put("done")
        plot_process.join()


# reading the dataframe
def fetch_dataframe():
    try:
        logging.info(f"Attempting to fetch DataFrame from peer {PEER_IP}...")
        # Replace the URL with the Flask endpoint where the DataFrame is hosted
        response = requests.get(f'http://{LOCAL_IP}:5000/get_dataframe', timeout=3)
        if response.status_code == 200:
            # Convert the CSV data back to DataFrame
            df = pd.read_csv(StringIO(response.text))
            return df
        else:
            logging.error("Failed to fetch DataFrame from peer. Status code: " + str(response.status_code))
            return None
    except requests.Timeout:
        logging.error("Request timed out while fetching DataFrame.")
        return None
    except Exception as e:
        logging.error(f"Error fetching DataFrame: {e}")
        return None
    
def process_trading_and_lcd(df, timestamp, current_data, queue):

    trade_amount = 0
    demand = current_data['energy'] # unit kWh
    
    # Calculate balance unit: kWh
    balance = - demand
    
    # Update dataframe
    df.loc[timestamp, [ 'demand', 'balance']] = [demand, balance]

    # Put data in queue for plotting
    queue.put({
        'timestamp': timestamp,
        'balance': balance
    })
    print(demand, balance)
    # Send updates to Flask server
    update_data_1 = {
        #'demand': demand,
        #'balance': balance
        'demand': 1,
        'balance': -1
    }
    make_api_call(f'http://{PEER_IP}:5000/update_peer_data', update_data_1)
    
    retry_count = 0
    
    while True:
        logging.info(f"Retry attempt {retry_count + 1}")
        # Fetch DataFrame from the server
        df = fetch_dataframe()
    
        if df is not None:
            # Check the Enable value for the current timestamp
            enable = df.loc[timestamp, 'Enable']
        
            # Start the trading for consumer after the prosumer provides trade amount
            if enable == 1:
                peer_data_response = requests.get(f'http://{LOCAL_IP}:5000/get_peer_data')
                if peer_data_response.status_code == 200:
                    peer_data = peer_data_response.json()
                    
                    peer_price = peer_data.get('peer_price')
                    buy_grid_price = peer_data.get('buy_grid_price')
                    trade_amount = peer_data.get('trade_amount', 0)# unit: kWh

                    if trade_amount is None:
                        logging.warning(f"No trading data available for peer {PEER_IP}")
                    
                    # Perform trading (now in kilo Watt-hours) 
                    buy_from_grid = abs(balance) - trade_amount
                    df.loc[timestamp, ['balance', 'currency', 'trade_amount']] = [
                        df.loc[timestamp, 'balance'] - balance,  # update balance
                        df.loc[timestamp, 'currency'] - trade_amount * peer_price - buy_from_grid * buy_grid_price,  # update currency
                        trade_amount  # update trade_amountge
                    ]
                        
                    logging.info(f"Bought {trade_amount*1000:.2f} Wh from peer at {peer_price:.2f} ￡/kWh" # unit
                                f"and the remaining {buy_from_grid*1000:.2f} Wh to the grid at {buy_grid_price:.2f} ￡/kWh") # unit
                    break
                else:
                    logging.error("Failed to get peer data for trading.")
            else:
                logging.info("Disabled, wait for trading amount. Retrying ")    
        else:
            logging.error("Failed to get peer data for trading")

        retry_count += 1

        # Update LCD display
        display_message(f"Dem:{demand*1000:.0f}Wh Tra:{trade_amount*1000:.0f}Wh") # unit
        
        logging.info(
            f"At {timestamp} , "
            f"Demand: {demand*1000:.2f}Wh, " # unit
            f"Balance: {df.loc[timestamp, 'balance']:.6f}Wh, "
            f"Currency: {df.loc[timestamp, 'currency']:.2f}￡, "
            f"LCD updated"
        )
        
    return df

def make_api_call(url, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
            print("Data sent successfully!")
            else:
            print(f"Failed to send data. Status code: {response.status_code}")
        
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logging.error(f"Max retries reached for {url}")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Smart Grid Simulation')
    parser.add_argument('--file_path', type=str, required=True, help='Path to the CSV file')
    parser.add_argument('--household', type=str, required=True, help='Household ID for the data')
    parser.add_argument('--start_date', type=str, required=True, help='Start date for the simulation')
    parser.add_argument('--timescale', type=str, required=True, choices=['d', 'w', 'm', 'y'], help='Timescale: d for day, w for week, m for month, y for year')


    args = parser.parse_args()  # Parse the arguments
    

    from server import app
    server_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    server_thread.start()
    
    time.sleep(2)  # Give the server a moment to start
    
    simulation_thread = threading.Thread(target=start_simulation_local, args=(args,))
    simulation_thread.start()
    
    simulation_thread.join()
    server_thread.join()
