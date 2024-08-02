import time
import math
import logging

logging.basicConfig(level=logging.INFO)

NOMINAL_VOLTAGE = 3.7  # V
MAX_VOLTAGE = 4.25  # V
MIN_VOLTAGE = 2.5  # V
CAPACITY = 2.6  # Ah

last_update_time = time.time()
battery_voltage = NOMINAL_VOLTAGE
total_charge_in = 0
total_energy_in = 0

def update_battery_charge(solar_current, solar_power, demand):
    global battery_voltage, last_update_time, total_charge_in, total_energy_in
    
    current_time = time.time()
    time_delta = current_time - last_update_time
    last_update_time = current_time

    # Calculate net current (charging current - demand current)
    demand_current = demand / battery_voltage
    net_current = solar_current - demand_current

    # Update battery voltage
    voltage_change = (net_current * time_delta) / CAPACITY
    battery_voltage += voltage_change
    battery_voltage = max(min(battery_voltage, MAX_VOLTAGE), MIN_VOLTAGE)

    # Calculate state of charge (SoC)
    soc = (battery_voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)

    # Update total charge and energy input
    if solar_current > 0:
        total_charge_in += solar_current * time_delta / 3600  # Convert to Ah
        total_energy_in += solar_power * time_delta / 3600  # Convert to Wh

    # Calculate charging efficiency
    if total_energy_in > 0:
        energy_stored = CAPACITY * (battery_voltage - MIN_VOLTAGE)
        efficiency = energy_stored / total_energy_in
    else:
        efficiency = 0

    logging.info(f"Updated battery - SoC: {soc*100:.2f}%, Voltage: {battery_voltage:.2f}V, "
                 f"Solar Current: {solar_current*1000:.2f}mA, Efficiency: {efficiency:.2f}")

    return soc, efficiency

def read_battery_charge():
    global battery_voltage
    soc = (battery_voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)
    return soc * 100  # Return SoC as percentage