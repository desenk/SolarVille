import argparse
import time
import pandas as pd
from multiprocessing import Process, Queue
from batteryControl import update_battery_charge, read_battery_charge
from lcdControlTest import display_message
from dataAnalysis import load_data, calculate_end_date, simulate_generation, update_plot_separate, update_plot_same
from trading import execute_trades, calculate_price

def plot_data(df, start_date, end_date, timescale, separate, queue):
    if separate:
        update_plot_separate(df, start_date, end_date, timescale)
    else:
        update_plot_same(df, start_date, end_date, timescale)
    queue.put("done")

def main(args):
    df = load_data(args.file_path, args.household, args.start_date, args.timescale)
    df = simulate_generation(df, mean=0.5, std=0.2)
    
    end_date = calculate_end_date(args.start_date, args.timescale)
    end_date_obj = pd.to_datetime(end_date)
    
    queue = Queue()
    plot_process = Process(target=plot_data, args=(df, args.start_date, end_date, args.timescale, args.separate, queue))
    plot_process.start()
    
    timestamp = pd.to_datetime(args.start_date)

    df['balance'] = df['generation'] - df['energy']  # Calculate the balance for each row
    df['currency'] = 100.0  # Initialize the currency column to 100
    df['battery_charge'] = 0.5  # Assume 50% initial charge

    try:
        while timestamp <= end_date_obj:
            current_data = df[df.index == timestamp]
            
            if not current_data.empty:
                demand = current_data['energy'].sum()  # Calculate the total energy demand at the current timestamp
                df.loc[df.index == timestamp, 'demand'] = demand  # Add the demand column to the DataFrame
                df.loc[df.index == timestamp, 'battery_charge'] = update_battery_charge(current_data['generation'].sum(), demand)  # Update the battery charge based on the initial generation and demand

                display_message(f"Gen: {current_data['generation'].sum():.2f}W\nDem: {demand:.2f}W\nBat: {current_data['battery_charge'].mean() * 100:.2f}%")

                df, price = execute_trades(df, timestamp)
                print(f"Trading executed. Price: {price}")
            
            # Move to the next timestamp
            timestamp += pd.Timedelta(hours=1)  # Adjust the increment based on your simulation needs
            time.sleep(1)  # Simulate a time step

            # Check if plotting is done
            if not queue.empty():
                break

    except KeyboardInterrupt:
        print("Simulation interrupted.")
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
    main(args)