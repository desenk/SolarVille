import time
import board # type: ignore
import busio # type: ignore
from adafruit_ina219 import INA219 # type: ignore
import logging

# Flag to determine whether to use the mock ADC or the real hardware
MOCK_ADC = True

if not MOCK_ADC:
    # Create the I2C bus for hardware communication
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the INA219 instance for current and voltage monitoring
    ina219 = INA219(i2c)
else:
    # Mock INA219 class for testing without hardware
    class MockINA219:
        @property
        def bus_voltage(self):
            return 12.0  # Mock voltage in volts

        @property
        def current(self):
            return 1.0  # Mock current in mA

    ina219 = MockINA219()

# Define thresholds and initial states
battery_charge = 0.5  # Assume 50% initial charge
max_battery_charge = 1.0 # Maximum battery charge (100%)
min_battery_charge = 0.0 # Minimum battery charge (0%)

scaling_factor = 100  # Example factor to scale up the generation data

def read_battery_charge():
    """
    Read the current battery charge status.
    Returns the power (in watts) based on voltage and current readings.
    """
    global battery_charge
    bus_voltage = ina219.bus_voltage  # Voltage on V- (load side)
    current = ina219.current / 1000  # Current in A (from mA)
    
    # Calculate power (W = V * A)
    power = bus_voltage * current
    return power

def update_battery_charge(generation, demand):
    # Update the battery charge based on the energy generation and demand.
    global battery_charge, max_battery_charge, min_battery_charge
    
    if generation > demand: # If excess energy, charge the battery
        surplus_power = generation - demand # Calculate surplus power
        battery_charge += surplus_power / max_battery_charge # Charge the battery
        if battery_charge > max_battery_charge: # Check if battery is fully charged
            battery_charge = max_battery_charge # Set battery charge to max value
            # Note: Excess power handling should be done in the trading function
    elif generation < demand: # If deficit energy, discharge the battery
        deficit_power = demand - generation # Calculate deficit power
        battery_charge -= deficit_power / max_battery_charge # Discharge the battery
        if battery_charge < min_battery_charge: # Check if battery is empty
            battery_charge = min_battery_charge # Set battery charge to min value
    
    logging.info(f"Updated battery charge: {battery_charge * 100:.2f}%")
    return battery_charge # Return the updated battery charge

if __name__ == "__main__": # Run the code if the script is executed
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