import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import calendar

# df is dataframe which is loaded from the csv file and is used to manipulate the data

# Function to load and preprocess data
def load_data(file_path, household, start_date, timescale): # Takes in the file path and the household ID
    alldata = pd.read_csv(file_path) # Load the data from the CSV file
    df = alldata[alldata["LCLid"] == household].copy() # Filter the data for the specific household

    # Process datetime info to pull out different components
    df['datetime'] = pd.to_datetime(df['tstp'].str.replace('.0000000', '')) # Convert the timestamp to datetime format
    df['date'] = df['datetime'].dt.date # Extract the date
    df['month'] = df['datetime'].dt.strftime("%B") # Extract the month
    df['day_of_month'] = df['datetime'].dt.strftime("%d") # Extract the day of the month
    df['time'] = df['datetime'].dt.strftime('%X') # Extract the time
    df['weekday'] = df['datetime'].dt.strftime('%A') # Extract the day of the week
    df['day_seconds'] = (df['datetime'] - df['datetime'].dt.normalize()).dt.total_seconds() # Extract the time of day in seconds

    # Order the weekdays and months correctly
    df['weekday'] = pd.Categorical(df['weekday'], categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
    df['month'] = pd.Categorical(df['month'], categories=calendar.month_name[1:], ordered=True) # Use calendar.month_name to get the full month names

    # Set energy consumption data to numeric type
    df = df[df["energy(kWh/hh)"] != "Null"] # Remove rows with missing energy data
    df["energy"] = df["energy(kWh/hh)"].astype("float64") # Convert energy data to numeric type to allow for calculations

    # Calculate the cumulative energy use over time for each date
    df["cumulative_sum"] = df.groupby('date')["energy"].cumsum() # Calculate the cumulative sum of energy use for each date
    df.set_index("datetime", inplace=True) # Set the datetime column as the index for the DataFrame

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d") # Convert the start date to a datetime object for calculations
    end_date_obj = calculate_end_date(start_date, timescale) # Calculate the end date based on the timescale flag
    end_date_obj = datetime.strptime(end_date_obj, "%Y-%m-%d %H:%M:%S") # Convert the end date to a datetime object for calculations
    df = df[(df.index >= start_date_obj) & (df.index < end_date_obj)] # Filter the DataFrame based on the start and end dates

    return df # Return the processed DataFrame

# Function to calculate the end date based on the timescale flag
def calculate_end_date(start_date, timescale): # Takes in the start date and the timescale flag from command line
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d") # Convert the start date to a datetime object for calculations
    # Calculate the end date based on the timescale flag
    if timescale == 'd':
        end_date_obj = start_date_obj + timedelta(days=1) # Add 1 day to the start date
    elif timescale == 'w': 
        end_date_obj = start_date_obj + timedelta(weeks=1) # Add 1 week to the start date
    elif timescale == 'm':
        end_date_obj = start_date_obj + timedelta(days=30) # Add 30 days to the start date
    elif timescale == 'y':
        end_date_obj = start_date_obj + timedelta(days=365) # Add 365 days to the start date
    else:
        # Raise an error if the timescale is invalid
        raise ValueError("Invalid timescale. Use 'd' for day, 'w' for week, 'm' for month, or 'y' for year.")
    return end_date_obj.strftime("%Y-%m-%d %H:%M:%S") # Return the end date in the correct format

# Function to simulate energy generation data
def simulate_generation(df, mean=0.5, std=0.2): # Takes in the DataFrame and the mean and standard deviation for the generation data
    np.random.seed(42)  # Set seed for reproducibility
    df['generation'] = np.random.normal(mean, std, df.shape[0]) # Generate random generation data
    df['generation'] = df['generation'].clip(lower=0)  # Ensure no negative values
    return df # Return the DataFrame with the generation data

# Function to update the plot in real-time for a single plot
def update_plot_same(df, start_date, end_date, interval=3): # Takes in the DataFrame, start date, end date, and interval for updating the plot
    df_day = df[start_date:end_date] # Filter the DataFrame for the specified date range
    df_day = df_day.reset_index() # Reset the index for the filtered DataFrame

    fig, ax = plt.subplots(figsize=(15, 6)) # Create a single plot for the energy data
    demand_line, = ax.plot([], [], label='Energy Demand (kWh)', color='red') # Plot for energy demand
    generation_line, = ax.plot([], [], label='Energy Generation (kWh)', color='green') # Plot for energy generation
    net_line, = ax.plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--') # Plot for net energy
    ax.legend() # Add a legend to the plot
    ax.set_xlabel('Time') # Set the x-axis label
    ax.set_ylabel('Energy (kWh)') # Set the y-axis label
    ax.set_title(f'Real-Time Energy Demand and Generation for Household on {start_date[:10]}') # Set the title of the plot

# Set the x-axis format based on the interval
    if interval == 'd':
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1)) # Set the major locator to hours
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) # Set the major formatter to hours and minutes
    elif interval == 'w':
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1)) # Set the major locator to days
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) # Set the major formatter to year-month-day
    elif interval == 'm':
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1)) # Set the major locator to weekdays
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) # Set the major formatter to year-month-day
    elif interval == 'y':
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1)) # Set the major locator to months
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')) # Set the major formatter to year-month

    plt.xticks(rotation=45) # Rotate the x-axis labels for better visibility
    plt.tight_layout() # Adjust the layout of the plot

    # Update the plot in real-time
    for i in range(len(df_day)):
        if i % 3 == 0:  # Update the plot every 3 data points to simulate real-time
            demand_line.set_data(df_day['datetime'][:i], df_day['energy'][:i]) # Update the energy demand plot
            generation_line.set_data(df_day['datetime'][:i], df_day['generation'][:i]) # Update the energy generation plot
            net_line.set_data(df_day['datetime'][:i], df_day['generation'][:i] - df_day['energy'][:i]) # Update the net energy plot
            ax.relim() # Recalculate the limits of the axes
            ax.autoscale_view() # Autoscale the view
            plt.pause(0.1)  # Adjust the pause duration to control the speed of updates

    plt.show() # Display the plot

# Function to update the plot in real-time for separate subplots
def update_plot_separate(df, start_date, end_date, interval=3): # Takes in the DataFrame, start date, end date, and interval for updating the plot
    df_day = df[start_date:end_date] # Filter the DataFrame for the specified date range
    df_day = df_day.reset_index() # Reset the index for the filtered DataFrame

    fig, axs = plt.subplots(3, 1, figsize=(15, 18), sharex=True) # Create separate subplots for the energy data
    
    demand_line, = axs[0].plot([], [], label='Energy Demand (kWh)', color='red') # Plot for energy demand
    generation_line, = axs[1].plot([], [], label='Energy Generation (kWh)', color='green') # Plot for energy generation
    net_line, = axs[2].plot([], [], label='Net Energy (kWh)', color='blue', linestyle='--') # Plot for net energy 
    
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
        if i % 3 == 0:  # Update the plot every 3 data points to simulate real-time
            demand_line.set_data(df_day['datetime'][:i], df_day['energy'][:i])
            generation_line.set_data(df_day['datetime'][:i], df_day['generation'][:i])
            net_line.set_data(df_day['datetime'][:i], df_day['generation'][:i] - df_day['energy'][:i])
            for ax in axs:
                ax.relim()
                ax.autoscale_view()
            plt.pause(0.8)  # Adjust the pause duration to control the speed of updates
    plt.show()