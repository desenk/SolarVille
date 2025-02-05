import sys
import time
import board  # type: ignore
import busio  # type: ignore
import adafruit_ina219  # type: ignore
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from datetime import datetime

# Global variables for real-time plotting
SOC_history = []
prosumer_power_history = []
consumer_power_history = []
generation_history = []
time_history = []
smooth_SOC_history = []
smooth_prosumer_power_history = []
smooth_generation_history = []

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
ax3.set_title("Generation Over Time")
ax3.grid(True)
ax3.legend()

def setup_ina219(address, i2c):
    """Setup an INA219 sensor with a specific I2C address."""
    sensor = adafruit_ina219.INA219(i2c, addr=address)
    sensor.set_calibration_16V_400mA()
    sensor.bus_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
    sensor.shunt_adc_resolution = adafruit_ina219.ADCResolution.ADCRES_12BIT_32S
    return sensor

def read_ina219(sensor):
    """Read values from an INA219 sensor."""
    bus_voltage = sensor.bus_voltage
    shunt_voltage = sensor.shunt_voltage
    current = sensor.current / 1000  # Convert to A
    power = bus_voltage * current * 1000  # Calculate power in mW
    return bus_voltage, shunt_voltage, current, power

def collect_data(mode, i2c):
    """Collect data based on the specified mode (prosumer or consumer)."""
    if mode == "prosumer":
        # Setup sensors
        ina219_solar = setup_ina219(0x45, i2c)
        ina219_battery = setup_ina219(0x41, i2c)
        ina219_demand = setup_ina219(0x40, i2c)

        # Collect data
        solar_voltage, _, solar_current, solar_power = read_ina219(ina219_solar)
        battery_voltage, _, _, _ = read_ina219(ina219_battery)
        _, _, _, demand_power = read_ina219(ina219_demand)

        return {
            "solar_power": solar_power,
            "battery_voltage": battery_voltage,
            "demand_power": demand_power,
        }

    elif mode == "consumer":
        # Setup sensor
        ina219_demand = setup_ina219(0x44, i2c)

        # Collect data
        _, _, _, demand_power = read_ina219(ina219_demand)

        return {
            "demand_power": demand_power,
        }

    else:
        raise ValueError("Invalid mode. Use 'prosumer' or 'consumer'.")

def smooth_data(data, window_size=5):
    if len(data) < window_size:
        return np.mean(data)  # 若数据点不足，返回均值
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')[-1]
    
def update_plot(frame):
    """Update the plot with the latest data."""
    global SOC_history, prosumer_power_history, consumer_power_history, time_history

    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA)

    # Detect mode from command-line arguments
    mode = sys.argv[1].lower()

    try:
        data = collect_data(mode, i2c)
    except Exception as e:
        print(f"Error collecting data: {e}")
        return

    # Process data based on mode
    current_time = datetime.now()
    time_history.append(current_time)

    if mode == "prosumer":
        solar_power = data["solar_power"]
        battery_soc = data["battery_voltage"] / 5.5 * 100  # Calculate SoC (%)
        demand_power = data["demand_power"]

        # Append data to history
        SOC_history.append(battery_soc)
        prosumer_power_history.append(demand_power)
        consumer_power_history.append(0)  # No consumer power in prosumer mode
        generation_history.append(solar_power)

        smooth_SOC_history.append(smooth_data(SOC_history))
        smooth_prosumer_power_history.append(smooth_data(prosumer_power_history))
        smooth_generation_history.append(smooth_data(generation_history))

        # Update lines
        line1.set_data(time_history, smooth_SOC_history)
        line2.set_data(time_history, smooth_prosumer_power_history)
        line3.set_data(time_history, consumer_power_history)
        line4.set_data(time_history, smooth_generation_history)

    elif mode == "consumer":
        demand_power = data["demand_power"]

        # Append data to history
        consumer_power_history.append(smooth_data(demand_power))
        SOC_history.append(0)  # No battery SoC in consumer mode
        prosumer_power_history.append(0)  # No prosumer power in consumer mode
        generation_history.append(0) # No generation in consumer mode

        # Update lines
        line3.set_data(time_history, consumer_power_history)

    # Adjust axis limits
    ax1.set_xlim(time_history[0], time_history[-1])
    ax1.set_ylim(0, 100)
    ax2.set_xlim(time_history[0], time_history[-1])
    ax2.set_ylim(0, max(prosumer_power_history + consumer_power_history) * 1.5)
    ax3.set_xlim(time_history[0], time_history[-1])
    ax3.set_ylim(0, max(generation_history) * 1.5)
       
    return line1, line2, line3, line4

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <mode>")
        print("Modes: prosumer or consumer")
        sys.exit(1)

    # Start real-time plot
    ani = FuncAnimation(fig, update_plot, interval=1000)  # Update every second
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
