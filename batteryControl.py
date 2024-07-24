import time
import board
import busio 
from adafruit_ina219 import INA219
import logging

# Mock flag
MOCK_ADC = True

if not MOCK_ADC:
    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the INA219 instance
    ina219 = INA219(i2c)
else:
    # Mock INA219 readings
    class MockINA219:
        @property
        def bus_voltage(self):
            return 12.0  # Mock voltage

        @property
        def current(self):
            return 1.0  # Mock current in mA

    ina219 = MockINA219()

# Define thresholds and initial states
battery_charge = 0.5  # Assume 50% initial charge
max_battery_charge = 1.0
min_battery_charge = 0.0

scaling_factor = 1000  # Example factor to scale up the generation data

def read_battery_charge():
    # Calculate the battery status
    global battery_charge
    bus_voltage = ina219.bus_voltage  # Voltage on V- (load side)
    current = ina219.current / 1000  # Current in A (from mA)
    
    # Calculate power
    power = bus_voltage * current
    return power

def update_battery_charge(generation, demand):
    global battery_charge, max_battery_charge, min_battery_charge
    
    if generation > demand:
        surplus_power = generation - demand
        battery_charge += surplus_power / max_battery_charge
        if battery_charge > max_battery_charge:
            battery_charge = max_battery_charge
            # Note: Excess power handling should be done in the trading function
    elif generation < demand:
        deficit_power = demand - generation
        battery_charge -= deficit_power / max_battery_charge
        if battery_charge < min_battery_charge:
            battery_charge = min_battery_charge
    
    logging.info(f"Updated battery charge: {battery_charge * 100:.2f}%")
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