import time
import board # type: ignore
import busio # type: ignore
from adafruit_ina219 import INA219 # type: ignore

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create the INA219 instance
ina219 = INA219(i2c)

# Define thresholds and initial states
battery_charge = 0.5  # Assume 50% initial charge
max_battery_charge = 1.0
min_battery_charge = 0.0

scaling_factor = 1000  # Example factor to scale up the generation data

def read_battery_charge():
    # calculate the battery status
    global battery_charge
    return battery_charge

def update_battery_charge(power_generated, power_demand):
    global battery_charge
    if power_generated > power_demand:
        surplus_power = power_generated - power_demand
        battery_charge += surplus_power / max_battery_charge
        if battery_charge > max_battery_charge:
            battery_charge = max_battery_charge
    elif power_generated < power_demand:
        deficit_power = power_demand - power_generated
        battery_charge -= deficit_power / max_battery_charge
        if battery_charge < min_battery_charge:
            battery_charge = min_battery_charge
    return battery_charge

if __name__ == "__main__":
    while True:
        # Get and scale data
        bus_voltage = ina219.bus_voltage  # Voltage on V- (load side)
        current = ina219.current / 1000   # Current in A (from mA)
        
        # Calculate power
        power = bus_voltage * current
        power_generated = power * scaling_factor
        
        # Simulated demand (example value, replace with actual demand logic)
        power_demand = 5.0  # Example value in watts
        
        # Update battery charge based on power generation and demand
        battery_charge = update_battery_charge(power_generated, power_demand)
        
        # Display data
        print(f"Bus Voltage: {bus_voltage:.2f} V")
        print(f"Current: {current:.2f} A")
        print(f"Power: {power:.2f} W")
        print(f"Battery Charge: {battery_charge * 100:.2f}%")
        
        time.sleep(1)  # Delay for 1 second
    