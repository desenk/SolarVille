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

def update_plot_same(df, start_date, end_date, interval, queue, ready_event):
    fig, ax = plt.subplots(figsize=(15, 6))
    demand_line, = ax.plot([], [], label='Energy Demand (kWh)', color='red', marker='o', linestyle='-')
    #generation_line, = ax.plot([], [], label='Energy Generation (kWh)', color='green', marker='o', linestyle='-')
    net_line, = ax.plot([], [], label='Net Energy', color='blue', linestyle='--', marker='o')
    ax.legend()
    ax.set_xlabel('Time')
    ax.set_ylabel('Energy')
    ax.set_title(f'Real-Time Energy Demand for Consumer Household on {start_date[:10]}')

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

    times = []
    demands = []
    #generations = []
    nets = []

    while True:
        data = queue.get()
        if data == "done":
            break

        timestamp = data['timestamp']
        #generation = data['generation']
        
        # Get demand from the dataframe
        demand = df.loc[timestamp, 'energy']
        
        times.append(timestamp)
        demands.append(demand)
        #generations.append(generation)
        #nets.append(generation - demand)
        nets.append( - demand)

        demand_line.set_data(times, demands)
        #generation_line.set_data(times, generations)
        net_line.set_data(times, nets)
        
        ax.relim()
        ax.autoscale_view()
        plt.draw()
        plt.pause(0.01)

    plt.show()

def update_plot_separate(df, start_date, end_date, interval, queue, ready_event):
    df_day = df[start_date:end_date]
    df_day = df_day.reset_index()

    fig, axs = plt.subplots(3, 1, figsize=(15, 18), sharex=True)

    demand_line, = axs[0].plot([], [], label='Energy Demand (kWh)', color='red')
    #generation_line, = axs[1].plot([], [], label='Energy Generation (kWh)', color='green')
    net_line, = axs[2].plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--')

    for ax in axs:
        ax.set_ylabel('Energy (kWh)')
        ax.legend()

    axs[0].set_title(f'Energy Demand for Household on {start_date[:10]}')
    #axs[1].set_title(f'Energy Generation for Household on {start_date[:10]}')
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
        #generation_line.set_data(df_day['datetime'][:index+1], df_day['generation'][:index+1])
        #net_line.set_data(df_day['datetime'][:index+1], df_day['generation'][:index+1] - df_day['energy'][:index+1])
        net_line.set_data(df_day['datetime'][:index+1],  - df_day['energy'][:index+1])

        for ax in axs:
            ax.relim()
            ax.autoscale_view()
        
        plt.draw()
        plt.pause(0.01)  # Short pause to allow the plot to update

    plt.show()
