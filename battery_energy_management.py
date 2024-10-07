# Be aware that battery_soc is a percentage number between 0-1; when you represent it with extra %, multiply it by 100

# Step 1: When generation is larger than demand
def battery_charging(excess_energy, battery_soc, battery_capacity):
    
    available_capacity = battery_capacity * (1 - battery_soc)  # Energy the battery can hold
    
    if available_capacity > 0:
        # If the battery can fully store the excess energy
        if available_capacity >= excess_energy:
            battery_soc += excess_energy / battery_capacity
            sell_to_grid = 0
        else:
        # If the battery cannot store all the excess energy, fill the battery and output the rest to sell
            battery_soc = 1.0 #100%
            sell_to_grid = excess_energy - available_capacity
    else:
        battery_soc = 1.0 #100%
        sell_to_grid = excess_energy

    # Return the battery status and sell information
    return battery_soc, sell_to_grid  

# Step 2: When generation is smaller than demand; 
# be aware that excess_energy is now a negative number
def battery_supply(excess_energy, battery_soc, battery_capacity, depth_of_discharge):
    available_capacity = (battery_soc - (1-depth_of_discharge)) * battery_capacity # Energy the battery can supply
    
    if available_capacity > 0:
        # If the battery has enough charge
        if available_capacity >= abs(excess_energy):
            battery_soc -= abs(excess_energy) / battery_capacity # Discharge the battery
            buy_from_grid = 0
        else:
            # If the battery does not have enough charge, deplete it first and then buy from the grid
            battery_soc = 1-depth_of_discharge
            buy_from_grid = abs(excess_energy) - available_capacity
    else:
        battery_soc = 1 - depth_of_discharge
        buy_from_grid = abs(excess_energy)    
    # Return the battery status and buy information
    return battery_soc, buy_from_grid
