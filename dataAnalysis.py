import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import calendar
import logging
import time

def update_plot_same(df, start_date, end_date, interval, queue, ready_event):
    fig, ax = plt.subplots(figsize=(15, 6))
    
    demand_line, = ax.plot([], [], label='Energy Demand (kWh)', color='red', marker='o', linestyle='-')
    generation_line, = ax.plot([], [], label='Energy Generation (W)', color='green', marker='o', linestyle='-')
    net_line, = ax.plot([], [], label='Net Energy', color='blue', linestyle='--', marker='o')
    
    ax.legend()
    ax.set_xlabel('Time')  
    ax.set_ylabel('Energy')
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

    ready_event.set()  # Signal that the plot is initialized

    times = []
    demands = []
    generations = []
    nets = []

    while True:
        while not queue.empty():
            data = queue.get()
            if data == "done":
                break

            timestamp = data['timestamp']
            generation = data['generation']
            
            # Get demand from the dataframe
            demand = df.loc[timestamp, 'energy']
            
            times.append(timestamp)  
            demands.append(demand)
            generations.append(generation)
            nets.append(generation - demand)

        demand_line.set_data(times, demands) 
        generation_line.set_data(times, generations)
        net_line.set_data(times, nets)
        
        ax.relim()
        ax.autoscale_view()
        plt.draw()
        plt.pause(0.01)  

        if data == "done":
            break

    plt.show()