import argparse
import time
import pandas as pd  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
from solarMonitor import get_current_readings

# Global variables for real-time plotting
SOC_history = []
prosumer_power_history = []
consumer_power_history = []
time_history = []

# Initialize the plot
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))
line1, = ax1.plot([], [], label="Battery SoC", color="blue")
line2, = ax2.plot([], [], label="Prosumer Power Demand (mW)", color="green")
line3, = ax2.plot([], [], label="Consumer Power Demand (mW)", color="orange")
line4, = ax3.plot([], [], label="Generation (mW)", color="purple")

# Configure axes
ax1.set_xlabel("Time")
ax1.set_ylabel("SoC (%)")
ax1.set_title("Battery SoC Over Time")
ax1.grid(True)
ax1.legend()

ax2.set_xlabel("Time")
ax2.set_ylabel("Power (mW)")
ax2.set_title("Power Demands Over Time")
ax2.grid(True)
ax2.legend()

ax3.set_xlabel("Time")
ax3.set_ylabel("Generation (mW)")
ax3.set_title("Total Generation Over Time")
ax3.grid(True)
ax3.legend()

def update_plot(frame):
    """Update the plot with the latest data."""
    global SOC_history, prosumer_power_history, consumer_power_history, time_history

    # Read sensor data
    readings = get_current_readings()
    bus_voltage_battery = readings['battery_voltage']
    power_prosumer_demand = readings['power_prosumer_damand']
    power_consumer_demand = readings['power_consumer_damand']
    power_battery = readings['power_battery']

    # Calculate SoC and generation
    battery_soc = bus_voltage_battery / 5  # SoC calculation
    generation = power_battery + power_prosumer_demand + power_consumer_demand

    # Append data to history
    current_time = datetime(2025, 1, 1) + timedelta(seconds=frame)
    SOC_history.append(battery_soc * 100)  # Convert to percentage
    prosumer_power_history.append(power_prosumer_demand)
    consumer_power_history.append(power_consumer_demand)
    time_history.append(current_time)

    # Update lines
    line1.set_data(time_history, SOC_history)
    line2.set_data(time_history, prosumer_power_history)
    line3.set_data(time_history, consumer_power_history)
    line4.set_data(time_history, [p_bat + p_pros + p_cons for p_bat, p_pros, p_cons in zip(SOC_history, prosumer_power_history, consumer_power_history)])

    # Adjust axis limits
    ax1.set_xlim(time_history[0], time_history[-1])
    ax1.set_ylim(0, 100)

    ax2.set_xlim(time_history[0], time_history[-1])
    ax2.set_ylim(0, max(max(prosumer_power_history, default=0), max(consumer_power_history, default=0)) * 1.1)

    ax3.set_xlim(time_history[0], time_history[-1])
    ax3.set_ylim(0, max([p_bat + p_pros + p_cons for p_bat, p_pros, p_cons in zip(SOC_history, prosumer_power_history, consumer_power_history)], default=0) * 1.1)

    return line1, line2, line3, line4

def start_simulation_local(args):
    """Start the simulation and real-time plotting."""
    ani = FuncAnimation(fig, update_plot, interval=1000)  # Update every second
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Energy Simulation")
    args = parser.parse_args()

    # Start simulation
    start_simulation_local(args)
