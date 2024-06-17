def execute_trades(df, timestamp):
    sellers = df[df['balance'] > 0].copy()
    buyers = df[df['balance'] < 0].copy()
    
    total_supply = sellers['balance'].sum()
    total_demand = abs(buyers['balance'].sum())
    
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
            df.at[seller_index, 'currency'] += trade_value
            df.at[buyer_index, 'currency'] -= trade_value
            
            if df.at[buyer_index, 'balance'] == 0:
                break
    
    return df, price

def calculate_price(supply, demand):
    base_price = 0.10  # Base price per kWh in pounds
    if demand > supply:
        price = base_price * (1 + (demand - supply) / supply)
    else:
        price = base_price * (1 - (supply - demand) / demand)
    return price