def calculate_price(supply, demand):
    base_price = 0.10  # Base price per kWh in pounds
    if demand > 0 and supply > 0:
        price = base_price * (demand / supply)
    else:
        price = base_price
    return max(price, 0.01)  # Ensure the price is never below 0.01
