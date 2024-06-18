import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import calendar

# Function to load and preprocess data
def load_data(file_path, household, start_date, timescale): 
    alldata = pd.read_csv(file_path) 
    df = alldata[alldata["LCLid"] == household].copy()

    # Process datetime info to pull out different components
    df['datetime'] = pd.to_datetime(df['tstp'].str.replace('.0000000', ''))
    df['date'] = df['datetime'].dt.date
    df['month'] = df['datetime'].dt.strftime("%B")
    df['day_of_month'] = df['datetime'].dt.strftime("%d")
    df['time'] = df['datetime'].dt.strftime('%X')
    df['weekday'] = df['datetime'].dt.strftime('%A')
    df['day_seconds'] = (df['datetime'] - df['datetime'].dt.normalize()).dt.total_seconds()

    df['weekday'] = pd.Categorical(df['weekday'], categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
    df['month'] = pd.Categorical(df['month'], categories=calendar.month_name[1:], ordered=True)

    df = df[df["energy(kWh/hh)"] != "Null"]
    df["energy"] = df["energy(kWh/hh)"].astype("float64")

    df["cumulative_sum"] = df.groupby('date')["energy"].cumsum()
    df.set_index("datetime", inplace=True)

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = calculate_end_date(start_date, timescale)
    end_date_obj = datetime.strptime(end_date_obj, "%Y-%m-%d %H:%M:%S")
    df = df[(df.index >= start_date_obj) & (df.index < end_date_obj)]

    return df

def calculate_end_date(start_date, timescale):
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

def simulate_generation(df, mean=0.5, std=0.2):
    np.random.seed(42)
    df['generation'] = np.random.normal(mean, std, df.shape[0])
    df['generation'] = df['generation'].clip(lower=0)
    return df

def update_plot_same(df, start_date, end_date, interval, queue):
    df_day = df[start_date:end_date]
    df_day = df_day.reset_index()

    fig, ax = plt.subplots(figsize=(15, 6))
    demand_line, = ax.plot([], [], label='Energy Demand (kWh)', color='red')
    generation_line, = ax.plot([], [], label='Energy Generation (kWh)', color='green')
    net_line, = ax.plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--')
    ax.legend()
    ax.set_xlabel('Time')
    ax.set_ylabel('Energy (kWh)')
    ax.set_title(f'Real-Time Energy Demand and Generation for Household on {start_date[:10]}')

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

    for i in range(len(df_day)):
        if i % 3 == 0:
            demand_line.set_data(df_day['datetime'][:i], df_day['energy'][:i])
            generation_line.set_data(df_day['datetime'][:i], df_day['generation'][:i])
            net_line.set_data(df_day['datetime'][:i], df_day['generation'][:i] - df_day['energy'][:i])
            ax.relim()
            ax.autoscale_view()
            print(f"Plotting at {df_day['datetime'][i]}")  # Debug print
            queue.put(df_day['datetime'][i])
            plt.pause(6)  # Increase pause duration to 6 seconds

    plt.show()
    queue.put("done")

def update_plot_separate(df, start_date, end_date, interval, queue):
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

    for i in range(len(df_day)):
        if i % 3 == 0:
            demand_line.set_data(df_day['datetime'][:i], df_day['energy'][:i])
            generation_line.set_data(df_day['datetime'][:i], df_day['generation'][:i])
            net_line.set_data(df_day['datetime'][:i], df_day['generation'][:i] - df_day['energy'][:i])
            for ax in axs:
                ax.relim()
                ax.autoscale_view()
            queue.put(df_day['datetime'][i])
            plt.pause(6)

    plt.show()
    queue.put("done")