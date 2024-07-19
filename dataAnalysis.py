import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import calendar
import logging
import time

# Function to load and preprocess data
def load_data(file_path, household, start_date, timescale, chunk_size=10000):
    start_time = time.time()
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = calculate_end_date(start_date, timescale)
    
    filtered_chunks = []
    chunks_with_data = 0
    total_chunks = 0
    
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        total_chunks += 1
        chunk = chunk[chunk["LCLid"] == household]
        chunk['datetime'] = pd.to_datetime(chunk['tstp'].str.replace('.0000000', ''))
        chunk = chunk[(chunk['datetime'] >= start_date_obj) & (chunk['datetime'] < end_date_obj)]
        
        if not chunk.empty:
            chunks_with_data += 1
            chunk['date'] = chunk['datetime'].dt.date
            chunk['month'] = chunk['datetime'].dt.strftime("%B")
            chunk['day_of_month'] = chunk['datetime'].dt.strftime("%d")
            chunk['time'] = chunk['datetime'].dt.strftime('%X')
            chunk['weekday'] = chunk['datetime'].dt.strftime('%A')
            chunk['day_seconds'] = (chunk['datetime'] - chunk['datetime'].dt.normalize()).dt.total_seconds()

            chunk['weekday'] = pd.Categorical(chunk['weekday'], categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
            chunk['month'] = pd.Categorical(chunk['month'], categories=calendar.month_name[1:], ordered=True)

            chunk = chunk[chunk["energy(kWh/hh)"] != "Null"]
            chunk["energy"] = chunk["energy(kWh/hh)"].astype("float64")
            chunk["cumulative_sum"] = chunk.groupby('date')["energy"].cumsum()
            
            filtered_chunks.append(chunk)
        else:
            logging.debug(f"No data found in chunk {total_chunks} for household {household} and date range {start_date} to {end_date_obj}")

    if chunks_with_data > 0:
        logging.info(f"Data found in {chunks_with_data} out of {total_chunks} chunks for household {household}")
        df = pd.concat(filtered_chunks)
        df.set_index("datetime", inplace=True)
        logging.info(f"Data loaded in {time.time() - start_time:.2f} seconds. Total rows: {len(df)}")
        return df
    else:
        logging.error(f"No data loaded for household {household} and date range {start_date} to {end_date_obj}")
        return pd.DataFrame()

def calculate_end_date(start_date, timescale): # Function to calculate end date based on timescale
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    if timescale == 'd':
        end_date_obj = start_date_obj + timedelta(days=1)
    elif timescale == 'w': 
        end_date_obj = start_date_obj + timedelta(weeks=1)
    elif timescale == 'm':
        end_date_obj = start_date_obj + timedelta(days=30)
    elif timescale == 'y':
        end_date_obj = start_date_obj + timedelta(days=365)
    else:
        raise ValueError("Invalid timescale. Use 'd' for day, 'w' for week, 'm' for month, or 'y' for year.")
    return end_date_obj.strftime("%Y-%m-%d %H:%M:%S")

def simulate_generation(df, mean=0.5, std=0.2): # Function to simulate energy generation
    np.random.seed(42)
    df['generation'] = np.random.normal(mean, std, df.shape[0])
    df['generation'] = df['generation'].clip(lower=0)
    return df

def update_plot_same(df, start_date, end_date, interval, queue, ready_event): # Function to update plot with same y-axis
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

    plt.xticks(rotation=45)
    plt.tight_layout()
    ready_event.set()  # Signal that the plot is initialized

    # Force an initial plot update
    plt.draw() # Draw the plot
    plt.pause(0.1) # Pause for 0.1 seconds
    logging.info("Initial plot update forced")

    # Show the plot immediately without blocking
    plt.show(block=False)

    for i in range(len(df_day)): # Loop through the length of the dataframe
        start_plot_time = time.time() # Start time for plotting
        demand_line.set_data(df_day['datetime'][:i+1], df_day['energy'][:i+1]) # Set data for energy demand
        generation_line.set_data(df_day['datetime'][:i+1], df_day['generation'][:i+1]) # Set data for energy generation
        net_line.set_data(df_day['datetime'][:i+1], df_day['generation'][:i+1] - df_day['energy'][:i+1]) # Set data for net energy
        ax.relim() # Recalculate limits
        ax.autoscale_view() # Autoscale the view
        queue.put(df_day['datetime'][i]) # Put datetime value in the queue
        plt.pause(6)  # Increase pause duration to 6 seconds

    plt.show() # Show the plot
    queue.put("done") # Put "done" in the queue

def update_plot_separate(df, start_date, end_date, interval, queue, ready_event):
    df_day = df[start_date:end_date]
    df_day = df_day.reset_index()

    fig, axs = plt.subplots(3, 1, figsize=(15, 18), sharex=True)

    demand_line, = axs[0].plot([], [], label='Energy Demand (kWh)', color='red')
    generation_line, = axs[1].plot([], [], label='Energy Generation (kWh)', color='green')
    net_line, = axs[2].plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--')

    axs[0].set_ylabel('Energy (kWh)')
    axs[0].set_title(f'Energy Demand for Household on {start_date[:10]}')
    axs[0].legend()

    axs[1].set_ylabel('Energy (kWh)')
    axs[1].set_title(f'Energy Generation for Household on {start_date[:10]}')
    axs[1].legend()

    axs[2].set_ylabel('Energy (kWh)')
    axs[2].set_title(f'Net Energy for Household on {start_date[:10]}')
    axs[2].legend()

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

    # Force an initial plot update
    plt.draw()
    plt.pause(0.1)

    # Show the plot immediately without blocking
    plt.show(block=False)

    for I in range(len(df_day)):
        if I % 1 == 0:
            start_plot_time = time.time()
            demand_line.set_data(df_day['datetime'][:I], df_day['energy'][:I])
            generation_line.set_data(df_day['datetime'][:I], df_day['generation'][:I])
            net_line.set_data(df_day['datetime'][:I], df_day['generation'][:I] - df_day['energy'][:I])
            axs[0].relim()
            axs[0].autoscale_view()
            queue.put(df_day['datetime'][I])
            plt.pause(6)

    plt.show()
    queue.put("done")