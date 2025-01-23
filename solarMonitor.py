import sys
import time
import board  # type: ignore
import busio  # type: ignore
import adafruit_ina219  # type: ignore
import matplotlib.pyplot as plt
from datetime import datetime

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

def collect_data(mode):
    """Collect data based on the specified mode (prosumer or consumer)."""
    i2c = busio.I2C(board.SCL, board.SDA)

    if mode == "prosumer":
        # Setup sensors
        ina219_solar = setup_ina219(0x45, i2c)
        ina219_battery = setup_ina219(0x41, i2c)
        ina219_demand = setup_ina219(0x40, i2c)

        # Collect data
        solar_voltage, _, solar_current, solar_power = read_ina219(ina219_solar)
        battery_voltage, _, _, _ = read_ina219(ina219_battery)
        demand_voltage, _, demand_current, demand_power = read_ina219(ina219_demand)

        return {
            "solar": {"power": solar_power},
            "battery": {"soc": battery_voltage / 5.5 * 100},
            "demand": {"power": demand_power},
        }

    elif mode == "consumer":
        # Setup sensor
        ina219_demand = setup_ina219(0x44, i2c)

        # Collect data
        demand_voltage, _, demand_current, demand_power = read_ina219(ina219_demand)

        return {
            "demand": {"power": demand_power}
        }

    else:
        raise ValueError("Invalid mode. Use 'prosumer' or 'consumer'.")

def plot_data(data, mode):
    """Plot the collected data."""
    timestamps = [datetime.now().strftime("%H:%M:%S")]

    if mode == "prosumer":
        solar_power = [data["solar"]["power"]]
        battery_soc = [data["battery"]["soc"]]
        demand_power = [data["demand"]["power"]]

        plt.figure(figsize=(10, 5))

        # Solar power plot
        plt.subplot(3, 1, 1)
        plt.plot(timestamps, solar_power, marker='o', label="Solar Power (mW)")
        plt.ylabel("Power (mW)")
        plt.legend()
        plt.grid(True)

        # Battery SoC plot
        plt.subplot(3, 1, 2)
        plt.plot(timestamps, battery_soc, marker='o', label="Battery SoC (%)")
        plt.ylabel("SoC (%)")
        plt.legend()
        plt.grid(True)

        # Demand power plot
        plt.subplot(3, 1, 3)
        plt.plot(timestamps, demand_power, marker='o', label="Demand Power (mW)")
        plt.ylabel("Power (mW)")
        plt.xlabel("Timestamp")
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.show()

    elif mode == "consumer":
        demand_power = [data["demand"]["power"]]

        plt.figure(figsize=(6, 4))
        plt.plot(timestamps, demand_power, marker='o', label="Demand Power (mW)")
        plt.ylabel("Power (mW)")
        plt.xlabel("Timestamp")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <mode>")
        print("Modes: prosumer or consumer")
        sys.exit(1)

    mode = sys.argv[1].lower()

    try:
        data = collect_data(mode)
        plot_data(data, mode)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
