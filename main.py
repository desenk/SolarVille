import argparse
import time
import pandas as pd
from multiprocessing import Process, Queue, Event
import logging
from batteryControl import update_battery_charge, read_battery_charge
from lcdControlTest import display_message
from dataAnalysis import load_data, calculate_end_date, simulate_generation, update_plot_separate, update_plot_same
from trading import execute_trades, calculate_price

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def plot_data(df, start_date, end_date, timescale, separate, queue, ready_event):
    if separate:
        update_plot_separate(df, start_date, end_date, timescale, queue, ready_event)
    else:
        update_plot_same(df, start_date, end_date, timescale, queue, ready_event)

def main(args):
    logging.info("Loading data, please wait...")
    start_time = time.time()
    df = load_data(args.file_path, args.household, args.start_date, args.timescale)
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

    try:
        while True:
            timestamp = queue.get()
            if timestamp == "done":
                break

            current_data = df[df.index == timestamp]
            
            if not current_data.empty:
                demand = current_data['energy'].sum()  # Calculate the total energy demand at the current timestamp
                df.loc[df.index == timestamp, 'demand'] = demand  # Add the demand column to the DataFrame
                battery_charge = update_battery_charge(current_data['generation'].sum(), demand)  # Update the battery charge based on the initial generation and demand
                df.loc[df.index == timestamp, 'battery_charge'] = battery_charge

                logging.info(f"Trading at {timestamp}")
                logging.info(f"Generation: {current_data['generation'].sum():.2f}W, Demand: {demand:.2f}W, Battery: {battery_charge * 100:.2f}%")

                df, price = execute_trades(df, timestamp)
                logging.info(f"Trading executed. Price: {price:.2f}")
                logging.info(f"Updated Balance: {df['balance'].sum():.2f}")

                display_message(f"Gen: {current_data['generation'].sum():.2f}W\nDem: {demand:.2f}W\nBat: {battery_charge * 100:.2f}%")
                logging.info(f"LCD updated at {timestamp}")

    except KeyboardInterrupt:
        logging.info("Simulation interrupted.")
    finally:
        plot_process.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Smart Grid Simulation')
    parser.add_argument('--file_path', type=str, required=True, help='Path to the CSV file')
    parser.add_argument('--household', type=str, required=True, help='Household ID for the data')
    parser.add_argument('--start_date', type=str, required=True, help='Start date for the simulation')
    parser.add_argument('--timescale', type=str, required=True, choices=['d', 'w', 'm', 'y'], help='Timescale: d for day, w for week, m for month, y for year')
    parser.add_argument('--separate', action='store_true', help='Flag to plot data in separate subplots')

    args = parser.parse_args()  # Parse the arguments
    main(args)  # Call the main function with the parsed arguments