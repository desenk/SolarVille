import pandas as pd # type: ignore
import numpy as np
import matplotlib.pyplot as plt # type: ignore
import matplotlib.dates as mdates # type: ignore
from datetime import datetime, timedelta
import calendar
import logging
import time

# Function to load and preprocess data
def load_data(file_path, household, start_date, timescale, chunk_size=10000):
    """
    Load and preprocess data from a CSV file.

    Args:
    file_path (str): Path to the CSV file.
    household (str): Household ID to filter the data.
    start_date (str): Start date for analysis in 'YYYY-MM-DD' format.
    timescale (str): Timescale for analysis ('d', 'w', 'm', 'y').
    chunk_size (int): Number of rows to process at a time.

    Returns:
    pandas.DataFrame: Processed data frame
    """
    start_time = time.time()
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = calculate_end_date(start_date, timescale)
    
    filtered_chunks = []
    chunks_with_data = 0
    total_chunks = 0
    
    # Process the CSV file in chunks
    for chunk in pd.read_csv(file_path, chunksize=chunk_size): # Read the CSV file in chunks
        total_chunks += 1 # Increment the total number of chunks
        chunk = chunk[chunk["LCLid"] == household] # Filter data for the specified household
        chunk['datetime'] = pd.to_datetime(chunk['tstp'].str.replace('.0000000', '')) # Convert 'tstp' to datetime format
        chunk = chunk[(chunk['datetime'] >= start_date_obj) & (chunk['datetime'] < end_date_obj)] # Filter data for the specified date range
        
        # Preprocess the data
        if not chunk.empty: # Check if the chunk has data
            chunks_with_data += 1 # Increment the number of chunks with data
            chunk['date'] = chunk['datetime'].dt.date # Extract date from datetime
            chunk['month'] = chunk['datetime'].dt.strftime("%B") # Extract month from datetime
            chunk['day_of_month'] = chunk['datetime'].dt.strftime("%d") # Extract day of the month from datetime
            chunk['time'] = chunk['datetime'].dt.strftime('%X') # Extract time from datetime
            chunk['weekday'] = chunk['datetime'].dt.strftime('%A') # Extract weekday from datetime
            chunk['day_seconds'] = (chunk['datetime'] - chunk['datetime'].dt.normalize()).dt.total_seconds() # Extract seconds from midnight

            # Convert weekday and month to categorical data for proper ordering
            chunk['weekday'] = pd.Categorical(chunk['weekday'], categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
            chunk['month'] = pd.Categorical(chunk['month'], categories=calendar.month_name[1:], ordered=True)

            # Process energy data
            chunk = chunk[chunk["energy(kWh/hh)"] != "Null"] # Remove rows with missing energy data
            chunk["energy"] = chunk["energy(kWh/hh)"].astype("float64") # Convert energy data to float
            chunk["cumulative_sum"] = chunk.groupby('date')["energy"].cumsum() # Calculate cumulative energy consumption per day
            
            filtered_chunks.append(chunk) # Append the processed chunk to the list
        else:
            logging.debug(f"No data found in chunk {total_chunks} for household {household} and date range {start_date} to {end_date_obj}")

    # Concatenate the filtered chunks into a single DataFrame
    if chunks_with_data > 0: # Check if any data was loaded
        logging.info(f"Data found in {chunks_with_data} out of {total_chunks} chunks for household {household}")
        df = pd.concat(filtered_chunks) # Concatenate the filtered chunks
        df.set_index("datetime", inplace=True) # Set the datetime column as the index
        logging.info(f"Data loaded in {time.time() - start_time:.2f} seconds. Total rows: {len(df)}")
        return df # Return the processed DataFrame
    else:
        logging.error(f"No data loaded for household {household} and date range {start_date} to {end_date_obj}")
        return pd.DataFrame() # Return an empty DataFrame

# Function to calculate the end date based on the timescale
def calculate_end_date(start_date, timescale):
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d") # Convert start date to datetime object
    if timescale == 'd':
        end_date_obj = start_date_obj + timedelta(days=1) # Add one day to the start date
    elif timescale == 'w': 
        end_date_obj = start_date_obj + timedelta(weeks=1) # Add one week to the start date
    elif timescale == 'm':
        end_date_obj = start_date_obj + timedelta(days=30) # Add 30 days to the start date
    elif timescale == 'y':
        end_date_obj = start_date_obj + timedelta(days=365) # Add 365 days to the start date
    else:
        raise ValueError("Invalid timescale. Use 'd' for day, 'w' for week, 'm' for month, or 'y' for year.")
    return end_date_obj.strftime("%Y-%m-%d %H:%M:%S") # Return the end date in string format

def simulate_generation(df, mean=0.5, std=0.2): # Function to simulate energy generation
    np.random.seed(42) # Set random seed for reproducibility
    df['generation'] = np.random.normal(mean, std, df.shape[0]) # Generate random data for energy generation
    df['generation'] = df['generation'].clip(lower=0) # Clip negative values to zero
    return df # Return the updated DataFrame

def update_plot_same(df, start_date, end_date, interval, queue, ready_event): # Function to update plot with same y-axis
    """
    Update plot with energy demand, generation, and net energy on the same axis.

    Args:
    df (pandas.DataFrame): Data frame containing energy data.
    start_date (str): Start date for plotting
    end_date (str): End date for plotting
    interval (str): Time interval for x-axis ticks
    queue (multiprocessing.Queue): Queue for recieving plot update signals
    ready_event (multiprocessing.Event): Event to signal plot initialisation
    """
    df_day = df[start_date:end_date] # Filter data for the specified date range
    df_day = df_day.reset_index() # Reset index

    fig, ax = plt.subplots(figsize=(15, 6)) # Create a figure and axis
    demand_line, = ax.plot([], [], label='Energy Demand (kWh)', color='red', marker='o', linestyle='-') # Plot for energy demand
    generation_line, = ax.plot([], [], label='Energy Generation (kWh)', color='green', marker='o', linestyle='-') # Plot for energy generation
    net_line, = ax.plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--', marker='o') # Plot for net energy
    ax.legend() # Add legend to the plot
    ax.set_xlabel('Time') # Set x-axis label
    ax.set_ylabel('Energy (kWh)') # Set y-axis label
    ax.set_title(f'Real-Time Energy Demand and Generation for Household on {start_date[:10]}') # Set title for the plot

    # Set x-axis formatting based on the interval
    if interval == 'd':
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif interval == 'w':
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    elif interval == 'm':
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    elif interval == 'y':
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    plt.xticks(rotation=45) # Rotate x-axis labels for better visibility
    plt.tight_layout() # Adjust layout for better appearance
    
    ready_event.set()  # Signal that the plot is initialized

    while True: # Update the plot in real-time
        timestamp = queue.get() # Get the timestamp from the queue
        if timestamp == "done": # Check if the simulation is complete
            break # Exit the loop

        # Update the plot with the new data point
        demand_line.set_data(df.index[:df.index.get_loc(timestamp)+1], df['energy'][:df.index.get_loc(timestamp)+1]) # Update energy demand data
        generation_line.set_data(df.index[:df.index.get_loc(timestamp)+1], df['generation'][:df.index.get_loc(timestamp)+1]) # Update energy generation data
        net_line.set_data(df.index[:df.index.get_loc(timestamp)+1], df['generation'][:df.index.get_loc(timestamp)+1] - df['energy'][:df.index.get_loc(timestamp)+1]) # Update net energy data
        
        ax.relim() # Recalculate limits
        ax.autoscale_view() # Autoscale the view
        plt.draw() # Redraw the plot
        plt.pause(0.01)  # Short pause to allow the plot to update

    plt.show() # Display the plot

def update_plot_separate(df, start_date, end_date, interval, queue, ready_event):
    df_day = df[start_date:end_date]
    df_day = df_day.reset_index()

    fig, axs = plt.subplots(3, 1, figsize=(15, 18), sharex=True)

    demand_line, = axs[0].plot([], [], label='Energy Demand (kWh)', color='red')
    generation_line, = axs[1].plot([], [], label='Energy Generation (kWh)', color='green')
    net_line, = axs[2].plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--')

    for ax in axs:
        ax.set_ylabel('Energy (kWh)')
        ax.legend()

    axs[0].set_title(f'Energy Demand for Household on {start_date[:10]}')
    axs[1].set_title(f'Energy Generation for Household on {start_date[:10]}')
    axs[2].set_title(f'Net Energy for Household on {start_date[:10]}')

    if interval == 'd':
        axs[2].xaxis.set_major_locator(mdates.HourLocator(interval=1))
        axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif interval == 'w':
        axs[2].xaxis.set_major_locator(mdates.DayLocator(interval=1))
        axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    elif interval == 'm':
        axs[2].xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    elif interval == 'y':
        axs[2].xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    plt.xticks(rotation=45)
    plt.tight_layout()
    ready_event.set()  # Signal that the plot is initialized

    plt.show(block=False)

    while True:
        timestamp = queue.get()
        if timestamp == "done":
            break

        index = df_day.index[df_day['datetime'] <= timestamp][-1]
        demand_line.set_data(df_day['datetime'][:index+1], df_day['energy'][:index+1])
        generation_line.set_data(df_day['datetime'][:index+1], df_day['generation'][:index+1])
        net_line.set_data(df_day['datetime'][:index+1], df_day['generation'][:index+1] - df_day['energy'][:index+1])
        
        for ax in axs:
            ax.relim()
            ax.autoscale_view()
        
        plt.draw()
        plt.pause(0.01)  # Short pause to allow the plot to update

    plt.show()