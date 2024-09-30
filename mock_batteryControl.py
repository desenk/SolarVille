# mock_batteryControl.py
def update_battery_charge(power_generated, power_demand):
    # Mock update logic
    battery_charge = min(1.0, max(0.0, (power_generated - power_demand) / 100.0))
    print(f"Mock updated battery charge: {battery_charge * 100:.2f}%")
    return battery_charge

def read_battery_charge():
    # Mock read logic
    return 50.0  # Return a constant mock value for demonstration