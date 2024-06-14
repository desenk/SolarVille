import time
import board
import busio
from adafruit_ina219 import INA219

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create the INA219 instance
ina219 = INA219(i2c)

# Define thresholds and initial states
battery_charge = 0.5  # Assume 50% initial charge
max_battery_charge = 1.0
min_battery_charge = 0.0

scaling_factor = 1000  # Example factor to scale up the generation data

while True:
    # Get and scale data
    bus_voltage = ina219.bus_voltage  # Voltage on V- (load side)
    current = ina219.current / 1000   # Current in A (from mA)
    
    # Calculate power
    power = bus_voltage * current
    
    # Scale up data
    scaled_voltage = bus_voltage * scaling_factor
    scaled_current = current * scaling_factor
    scaled_power = scaled_voltage * scaled_current

    power_generated = scaled_power
    
    # Simulated demand (example value, replace with actual demand logic)
    power_demand = 5.0  # Example value in watts
    
    # Charging and discharging logic
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

    # Display data
    print(f"Bus Voltage: {bus_voltage:.2f} V")
    print(f"Current: {current:.2f} A")
    print(f"Power: {power:.2f} W")
    print(f"Scaled Bus Voltage: {scaled_voltage:.2f} V")
    print(f"Scaled Current: {scaled_current:.2f} A")
    print(f"Scaled Power: {scaled_power:.2f} W")
    print(f"Battery Charge: {battery_charge * 100:.2f}%")
    
    time.sleep(1)  # Delay for 1 second