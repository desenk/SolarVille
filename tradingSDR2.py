def execute_trades(df, timestamp):
    sellers = df[df['balance'] > 0].copy()
    buyers = df[df['balance'] < 0].copy()
    
    total_supply = sellers['balance'].sum()
    total_demand = abs(buyers['balance'].sum())
    
    if total_supply == 0 or total_demand == 0:
        # If there's no supply or demand, skip trading
        return df, 0.0
    
    price = calculate_price(total_supply, total_demand)
    
    for buyer_index, buyer in buyers.iterrows():
        for seller_index, seller in sellers.iterrows():
            if seller['balance'] == 0:
                continue
            trade_amount = min(seller['balance'], abs(buyer['balance']))
            trade_value = trade_amount * price
            
            # Update balances
            df.at[seller_index, 'balance'] -= trade_amount
            df.at[buyer_index, 'balance'] += trade_amount
            df.at[seller_index, 'currency'] = float(df.at[seller_index, 'currency']) + trade_value
            df.at[buyer_index, 'currency'] = float(df.at[buyer_index, 'currency']) - trade_value
            
            if df.at[buyer_index, 'balance'] == 0:
                break
    
    return df, price

def calculate_price(supply, demand):
    p_min = 0.10    # Minimum electricity trading price for prosumers
    p_max = 1.0     # Maximum electricty trading price for consumers
    base_price = (p_min + p_max)/2   # Base price per kWh in pounds
    sdr = supply/demand
    print(f"Calculating price: supply = {supply:.2f}, demand = {demand:.2f}, SDR = {sdr:.2f}")  # Debug print
    if demand > 0 and supply > 0:
        if sdr >= 2 :
            price = p_min
        elif sdr < 2 and sdr > 0.5:
            price = base_price * (1 / sdr)
        elif sdr <= 0.5:
            price = p_max
    else:
        price = base_price
    price = max(price, 0)  # Ensure the price is non-negative
    print(f"Calculated price: {price:.2f}")  # Debug print
    return price