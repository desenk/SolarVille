# 上一个版本是ADMM_MULTI_SUM_PEAK.py，这个版本引入了随机波动的ev到家和离开的时间，使模拟更接近真实情况
# 可扩展至n+1个家庭的版本
# 简介： 本代码使用ADMM优化，优化目标是最小化每个时间节点与电网交易的绝对值的最大值的和，
# 通过约束peak这个变量必须大于import（正值）和大于负的export（转换为正值），再最小化sum(peak)来实现
# 不包括0-1变量，需要限制家庭1不能同时从电网买卖电，不能同时从家庭2买卖电，电池不能同时充放电，所以只分别设置了一个参数，通过正负来判断是卖电买电，是充电还是放电
import cvxpy as cp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Define prosumer and consumer household configurations
prosumer_household_config = {
    #"MAC003252": {"solar": True, "battery": True, "ev": False, "demand": True, "solar_rated_power": 2},
    "MAC003305": {"solar": True, "battery": False, "ev": False, "demand": True, "solar_rated_power": 2},
    "MAC003394": {"solar": True, "battery": True, "ev": True, "demand": True, "solar_rated_power": 2},
    "MAC003428": {"solar": True, "battery": True, "ev": True, "demand": True, "solar_rated_power": 2},
    #"MAC003863": {"solar": True, "battery": True, "ev": False, "demand": True, "solar_rated_power": 2}
}
consumer_household_config = {
    #"MAC003223": {"solar": False, "battery": False, "ev": True, "demand": True},
    "MAC003281": {"solar": False, "battery": False, "ev": True, "demand": True},
    #"MAC003348": {"solar": False, "battery": False, "ev": False, "demand": True},
    #"MAC003553": {"solar": False, "battery": False, "ev": False, "demand": True},
    "MAC003874": {"solar": False, "battery": False, "ev": False, "demand": True}
}

# Function to read household consumption data
def read_household_consumption_data(file_path, start_date, end_date, household_config):
    household_data = pd.read_csv(file_path)
    household_data['tstp'] = pd.to_datetime(household_data['tstp'], format='%d/%m/%Y %H:%M')
    household_data = household_data.set_index('tstp')
    filtered_data = household_data.loc[start_date:end_date]
    
    consumption_data = {}
    for household_id in household_config.keys():
        consumption_data[household_id] = filtered_data[filtered_data['LCLid'] == household_id]['energy(kWh/hh)'].astype(float).values
    return consumption_data

# Function to read solar generation data
def read_solar_generation_data(file_path, start_date, end_date, household_config):
    solar_data = pd.read_csv(file_path, encoding='utf-8', skiprows=3)
    solar_data['time'] = pd.to_datetime(solar_data['time'], format='%d/%m/%Y %H:%M')
    solar_data = solar_data.set_index('time')
    solar_data = solar_data.loc[start_date:end_date]
    
    if solar_data.empty:
        raise ValueError("No data available in the specified time range.")
    
    solar_half_hour = solar_data.resample('30min').fillna(method='bfill')
    last_time = solar_half_hour.index[-1] + pd.Timedelta(minutes=30)
    solar_half_hour = solar_half_hour.reindex(solar_half_hour.index.union([last_time])).fillna(method='ffill')
    
    solar_gen_data = {}
    for household_id, config in household_config.items():
        if config['solar']:
            solar_gen_data[household_id] = solar_half_hour['electricity'].values * config['solar_rated_power']
        else:
            solar_gen_data[household_id] = None
    return solar_gen_data

# Define the date range for the data
start_date = "2013-06-01"
end_date = "2013-06-02"
gen_start_date = "2019-06-01"
gen_end_date = "2019-06-02"

# Read household consumption data for all households
all_consumption_data = {}
for household_id in prosumer_household_config.keys():
    all_consumption_data[household_id] = read_household_consumption_data(
        'E:/APE/MSc Project/solarData/block_0_household.csv', start_date, end_date, {household_id: prosumer_household_config[household_id]}
    )[household_id]

for household_id in consumer_household_config.keys():
    all_consumption_data[household_id] = read_household_consumption_data(
        'E:/APE/MSc Project/solarData/block_0_household.csv', start_date, end_date, {household_id: consumer_household_config[household_id]}
    )[household_id]

# Read solar generation data for prosumer households
all_solar_gen_data = {}
for household_id in prosumer_household_config.keys():
    all_solar_gen_data[household_id] = read_solar_generation_data(
        'E:/APE/MSc Project/solarData/ninja_pv_51.4893_-0.1441_uncorrected_1kW_0.1systemLoss_33Tilt_178Azimuth.csv', gen_start_date, gen_end_date, {household_id: prosumer_household_config[household_id]}
    )[household_id]
# for household_id in consumer_household_config.keys():
#     all_solar_gen_data[household_id] = read_solar_generation_data(
#         'E:/APE/MSc Project/solarData/ninja_pv_51.4893_-0.1441_uncorrected_1kW_0.1systemLoss_33Tilt_178Azimuth.csv', gen_start_date, gen_end_date, {household_id: consumer_household_config[household_id]}
#     )[household_id]

# Determine the length of the data
data_length = len(all_consumption_data[next(iter(prosumer_household_config.keys()))])
print("consumption Data length:", data_length)
print("solar gen Data length:", len(all_solar_gen_data[next(iter(prosumer_household_config.keys()))]))

# 初始化每个家庭的电池参数和电车参数，并为有电车的家庭添加随机波动
battery_params = {}
ev_params = {}
all_household_config = {**prosumer_household_config, **consumer_household_config}
for household_id, config in all_household_config.items():
    if config['battery']:
        battery_params[household_id] = {
            "capacity": 10,  # 电池容量 unit:kWh
            "initial_charge": 5,  # 初始电池电量 unit:kWh
            "max_charge_rate": 3,  # 每小时最大充电速率 unit:kW
            "max_discharge_rate": 3  # 每小时最大放电速率 unit:kW
        }
    if config['ev']:
        # 为电动车设置好数据
        ev_params[household_id] = {
            "full_capacity": 75,  # 电车电池容量 unit:kWh
            "initial_charge": 60,  # 初始电量 unit:% 
            "full_charge": 75,  # 目标电量 unit:% 
            "max_charge_rate": 7  # 每小时最大充电量 unit:kW
        }

# 电池充电和放电变量
battery_charge = {household_id: cp.Variable(data_length) for household_id in battery_params.keys()}

# 更新电池约束，只有拥有电池的家庭才会有约束
battery_constraints = {}
for household_id, params in battery_params.items():
    battery_constraints[household_id] = [
        battery_charge[household_id] <= params["max_charge_rate"] / 2,  # Maximum charge rate per half hour
        battery_charge[household_id] >= -params["max_discharge_rate"] / 2,  # Maximum discharge rate per half hour
        cp.cumsum(battery_charge[household_id]) + params["initial_charge"] <= params["capacity"],
        cp.cumsum(battery_charge[household_id]) + params["initial_charge"] >= 0
    ]

# 电车充电变量
ev_load = {household_id: cp.Variable(data_length, nonneg=True) for household_id in ev_params.keys()}  # 每小时充电量 unit:kWh
ev_soc = {household_id: cp.Variable(data_length, nonneg=True) for household_id in ev_params.keys()}  # 每小时电车的SOC unit:% 

# 初始化每个家庭的电车参数，并为有电车的家庭添加随机波动
ev_constraints = {}
ev_arrival = {}
ev_departure = {}
for household_id, config in all_household_config.items():
    if config['ev']:
        
        # 计算电动汽车到家和离开家的时间点，为每个家庭生成随机的偏移（-2 到 +2），确保每个家庭的波动独立
        base_arrival_step = 37 # 18:30
        base_departure_step = 16 # 08:00        
        numeric_id = int(household_id.replace("MAC", "")) # 提取数字部分作为种子
        # 计算总天数
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")       
        num_days = (end - start).days + 1

        # 为整个时间范围计算基础到达/离开时间点
        base_arrival = [base_arrival_step + i * 48 for i in range(num_days)]  # 每48步为一天
        base_departure = [base_departure_step + i * 48 for i in range(num_days)]

        # 为每一天生成独立的随机偏移
        daily_arrival_offsets = []
        daily_departure_offsets = []
        for day in range(num_days):
            # 使用 household_id 和 day 组合生成种子，确保每一天的随机性独立且可重复
            day_seed = numeric_id+day
            np.random.seed(abs(day_seed))  # 使用哈希值作为种子
            arrival_offset = np.random.randint(-2, 3)  # -2, -1, 0, 1, 2
            departure_offset = np.random.randint(-2, 3)  # -2, -1, 0, 1, 2
            daily_arrival_offsets.append(arrival_offset)
            daily_departure_offsets.append(departure_offset)

        # 应用随机偏移并限制范围
        adjusted_arrival = []
        adjusted_departure = []
        for day in range(num_days):
            # 计算每天的到达和离开时间
            day_arrival = base_arrival[day] + daily_arrival_offsets[day]
            day_departure = base_departure[day] + daily_departure_offsets[day]

            adjusted_arrival.append(day_arrival)
            adjusted_departure.append(day_departure)

        # 存储波动后的到达和离开时间
        ev_arrival[household_id] = adjusted_arrival
        ev_departure[household_id] = adjusted_departure

        # 为每个家庭添加ev_constraints
        ev_constraints[household_id] = []
        for t in range(data_length):
            # 第一天从00:00到离开家之间，电车充电
            if t <= ev_departure[household_id][0]:
                ev_constraints[household_id].append(ev_load[household_id][t] <= ev_params[household_id]["max_charge_rate"] / 2)
            # 从每一次到家和下一次离开家之间，电车充电
            elif any(arrival < t <= departure for arrival, departure in zip(ev_arrival[household_id], ev_departure[household_id][1:])):
                ev_constraints[household_id].append(ev_load[household_id][t] <= ev_params[household_id]["max_charge_rate"] / 2)
            else:
                ev_constraints[household_id].append(ev_load[household_id][t] == 0) # 其余时间不在家不充电

            # 电车 SOC 和充电量约束
            if t in ev_departure[household_id]: # 离开家那一刻的soc设定为目标值，从而推算这个时间点的充电量
                ev_constraints[household_id].append(ev_soc[household_id][t] == ev_params[household_id]["full_charge"])
                ev_constraints[household_id].append(ev_load[household_id][t] == (ev_soc[household_id][t] - ev_soc[household_id][t-1]) * 0.01 * ev_params[household_id]["full_capacity"])
            elif t == 0 or t in ev_arrival[household_id]: #到达那一刻的soc设定为初始值，这个时间点的充电量表示的是从上一个时间节点到这个时间节点之间充的电，那么回到家这一刻，充电量是0
                ev_constraints[household_id].append(ev_soc[household_id][t] == ev_params[household_id]["initial_charge"])
            else: # 其余时间，soc是从上一个时间节点到这个时间节点的充电量推算出来的
                ev_constraints[household_id].append(ev_soc[household_id][t] == ev_soc[household_id][t - 1] + ev_load[household_id][t] / ev_params[household_id]["full_capacity"] * 100)
            
            ev_constraints[household_id].append(ev_soc[household_id][t] >= 0)
            ev_constraints[household_id].append(ev_soc[household_id][t] <= 100)

        print(f"Household {household_id} EV Arrival: {ev_arrival}")
        print(f"Household {household_id} EV Departure: {ev_departure}")
print(ev_arrival)

# 定义优化变量，并添加非负约束
trade_prosumer_to_consumer = {
    (p, c): cp.Variable(data_length) for p in prosumer_household_config.keys() for c in consumer_household_config.keys()
}
trade_prosumer_to_grid = {
    p: cp.Variable(data_length) for p in prosumer_household_config.keys()
}
trade_consumer_to_grid = {
    c: cp.Variable(data_length) for c in consumer_household_config.keys()
}
Peak = {
    p: cp.Variable(data_length, nonneg=True) for p in prosumer_household_config.keys()
}
peak = {
    p: cp.Variable(data_length, nonneg=True) for p in prosumer_household_config.keys()
}
Peak2 = { 
    c : cp.Variable(data_length, nonneg=True) for c in consumer_household_config.keys()
}
peak2 = { 
    c : cp.Variable(data_length, nonneg=True) for c in consumer_household_config.keys()
}
print("finish initialization for optimization variables")

# 定义优化参数
#初始化家庭用电参数
consumption_param = cp.Parameter(data_length, nonneg=True)
solar_gen_param = cp.Parameter(data_length, nonneg=True)
# ADMM 参数
rho = 1.0
alpha = 1.0

# 初始化变量
z = np.zeros((len(prosumer_household_config), len(consumer_household_config), data_length))
u = np.zeros((len(prosumer_household_config), len(consumer_household_config), data_length))

# 更新 prosumer 的变量
constraints_prosumer = {}
prob_prosumer = {}

# 更新 consumer 的变量
constraints_consumer = {}
prob_consumer = {}

# ADMM 迭代
for _ in range(10):
    print("start optimization")
    # 更新 prosumer 的变量
    for p in prosumer_household_config.keys():
        constraints_prosumer[p] = [
            sum(trade_prosumer_to_consumer[(p, c)] for c in consumer_household_config.keys()) + 
            trade_prosumer_to_grid[p] + consumption_param + (ev_load[p] if p in ev_load else 0) 
            - solar_gen_param + (battery_charge[p] if p in battery_charge else 0) == 0
        ]
        if p in battery_constraints:
            constraints_prosumer[p] += battery_constraints[p]
        if p in ev_constraints:
            constraints_prosumer[p] += ev_constraints[p]
        #Peak = cp.max(Peak_buy_prosumer[p]) + cp.max(Peak_sell_prosumer[p])
        Peak[p] = cp.norm_inf(trade_prosumer_to_grid[p])
        print(type(Peak[p]))
        print(f"Type of constraints_prosumer[{p}]:", type(constraints_prosumer[p]))
        prob_prosumer[p] = cp.Problem(cp.Minimize(Peak[p] + (rho / 2) * cp.sum_squares(
                                                sum(trade_prosumer_to_consumer[(p, c)] for c in consumer_household_config.keys())
                                                - sum(z[list(prosumer_household_config.keys()).index(p), list(consumer_household_config.keys()).index(c)] for c in consumer_household_config.keys()) 
                                                + sum(u[list(prosumer_household_config.keys()).index(p), list(consumer_household_config.keys()).index(c)] for c in consumer_household_config.keys()))
                                            ), constraints_prosumer[p])
        print("finish prosumer", p,"setup for optimization constraints and objective function")
        
        consumption_param.value = all_consumption_data[p]
        solar_gen_param.value = all_solar_gen_data[p]
        #print(p, "solar_gen_param:", solar_gen_param.value)

        for pr in prob_prosumer[p].parameters():
            if pr.value is None or np.isnan(pr.value).any():
                print(f"Parameter {pr.name()} has invalid values: {pr.value}")

        try:
            prob_prosumer[p].solve(solver=cp.OSQP, eps_rel=1e-4)
        except Exception as e:
            print(p, "Optimization failed:", str(e))
        
        print(prob_prosumer[p].status)
        print(p, "finish prosumer optimization")
        # print("Prosumer", id(prob_prosumer[p]), " problem variables:")
        # for key in trade_prosumer_to_consumer.keys():
        #     print(f"!!!trade_prosumer_to_consumer[{key}]: {trade_prosumer_to_consumer[key].value}")
        # for var in prob_prosumer[p].variables():
        #     for key, value in trade_prosumer_to_consumer.items():
        #         if var is value:
        #             print(f"trade_prosumer_to_consumer[{key}]: {var.value}")
        #     for key, value in trade_prosumer_to_grid.items():
        #         if var is value:
        #             print(f"trade_prosumer_to_grid[{key}]: {var.value}")
        #     for key, value in battery_charge.items():
        #         if var is value:
        #             print(f"battery_charge[{key}]: {var.value}")
        #     for key, value in ev_load.items():
        #         if var is value:
        #             print(f"ev_load[{key}]: {var.value}")
        #     for key, value in ev_soc.items():
        #         if var is value: 
        #             print(f"ev_soc[{key}]: {var.value}")
        
    for c in consumer_household_config.keys():
        constraints_consumer[c] = [
            #Peak_buy_consumer[c] >= -trade_consumer_to_grid[c],  # Ensure Peak_buy_consumer is the largest negative part of trade_consumer_to_grid
            #Peak_sell_consumer[c] >= trade_consumer_to_grid[c],  # Ensure Peak_sell_consumer is the largest positive part of trade_consumer_to_grid
            sum(-trade_prosumer_to_consumer[(p, c)] for p in prosumer_household_config.keys()) + 
            trade_consumer_to_grid[c] + consumption_param + (ev_load[c] if c in ev_load else 0) == 0
        ]
        if c in ev_constraints:
            constraints_consumer[c] += ev_constraints[c]
        constraints_consumer[c] += [ peak2[c] >= -trade_consumer_to_grid[c], peak2[c] >= trade_consumer_to_grid[c] ]
        #Peak2 = cp.max(Peak_buy_consumer[c]) + cp.max(Peak_sell_consumer[c])
        Peak2[c] = cp.norm_inf(trade_consumer_to_grid[c])
        prob_consumer[c] = cp.Problem(cp.Minimize(cp.sum(peak2[c]) + (rho / 2) * cp.sum_squares(
                                sum(trade_prosumer_to_consumer[(p, c)] for p in prosumer_household_config.keys()) 
                                - sum(z[list(prosumer_household_config.keys()).index(p), list(consumer_household_config.keys()).index(c)] for p in prosumer_household_config.keys()) 
                                + sum(u[list(prosumer_household_config.keys()).index(p), list(consumer_household_config.keys()).index(c)] for p in prosumer_household_config.keys()))
                                ), constraints_consumer[c])
        print("finish consumer", c, "setup for optimization constraints and objective function")

        consumption_param.value = all_consumption_data[c]
        #print(c, "consumption_param:", consumption_param.value)
        for co in prob_consumer[c].parameters():
            if co.value is None or np.isnan(co.value).any():
                print(f"Parameter {co.name()} has invalid values: {co.value}")

        try:
            prob_consumer[c].solve(solver=cp.OSQP, eps_rel=1e-4)
        except Exception as e:
            print(c, "Optimization failed:", str(e))
        print(prob_consumer[c].status)
        print(c, "finish consumer optimization")


    # 更新 z 和 u
    z_old = z.copy()
    for p, prosumer in enumerate(prosumer_household_config.keys()):
        for c, consumer in enumerate(consumer_household_config.keys()):
            z[p, c] = alpha * trade_prosumer_to_consumer[(prosumer, consumer)].value + (1 - alpha) * z_old[p, c]
            u[p, c] = u[p, c] + trade_prosumer_to_consumer[(prosumer, consumer)].value - z[p, c]

for p in prosumer_household_config.keys():
    print("Problem 1 status:", prob_prosumer[p].status)
for c in consumer_household_config.keys():
    print("Problem 2 status:", prob_consumer[c].status)

# Plot the results
fig, axs = plt.subplots(len(prosumer_household_config) + len(consumer_household_config)+1, 2, figsize=(15, 20))

# Calculate price and cost
sell_to_grid_price = np.full(data_length, 0.1)
buy_from_grid_price = np.full(data_length, 0.5)

# Calculate total supply and demand
total_supply = np.sum([all_solar_gen_data[household_id] for household_id in prosumer_household_config.keys()], axis=0)
total_demand = np.sum([all_consumption_data[household_id] for household_id in prosumer_household_config.keys()], axis=0) + \
                np.sum([ev_load[household_id].value for household_id in ev_params.keys()], axis=0) + \
                np.sum([all_consumption_data[household_id] for household_id in consumer_household_config.keys()], axis=0)

SDR = total_supply / total_demand

# Calculate neighbor trading prices
sell_to_neighbor_price = np.where(
    SDR >= 1, sell_to_grid_price,
    np.where(
        SDR < 0.001, buy_from_grid_price,
        (buy_from_grid_price * sell_to_grid_price) / ((buy_from_grid_price - sell_to_grid_price) * SDR + sell_to_grid_price)
    )
)

buy_from_neighbor_price = np.where(
    SDR >= 1, sell_to_grid_price,
    np.where(
        SDR < 0.001, buy_from_grid_price,
        sell_to_grid_price * SDR + buy_from_grid_price * (1 - SDR)
    )
)

# Plot each prosumer household's energy distribution and calculate costs 
for i, household_id in enumerate(prosumer_household_config.keys()):
    sell_to_grid = np.where(trade_prosumer_to_grid[household_id].value > 0, trade_prosumer_to_grid[household_id].value, 0)
    buy_from_grid = np.where(trade_prosumer_to_grid[household_id].value <= 0, -trade_prosumer_to_grid[household_id].value, 0)
    
    charge = np.where(battery_charge[household_id].value > 0, battery_charge[household_id].value, 0) if household_id in battery_charge else 0
    discharge = np.where(battery_charge[household_id].value <= 0, -battery_charge[household_id].value, 0) if household_id in battery_charge else 0
    
    ev_value = ev_load[household_id].value if household_id in ev_load else 0

    sell_to_neighbor = np.zeros(data_length)
    buy_from_neighbor = np.zeros(data_length)
    for c in consumer_household_config.keys():
        sell_to_neighbor += np.where(trade_prosumer_to_consumer[(household_id, c)].value > 0, trade_prosumer_to_consumer[(household_id, c)].value, 0)
        buy_from_neighbor += np.where(trade_prosumer_to_consumer[(household_id, c)].value <= 0, -trade_prosumer_to_consumer[(household_id, c)].value, 0)
    sum_sell_to_neighbor = np.sum(sell_to_neighbor, axis=0)
    sum_buy_from_neighbor = np.sum(buy_from_neighbor, axis=0)
    
    cost_half_hour = buy_from_grid * buy_from_grid_price - sell_to_grid * sell_to_grid_price - sell_to_neighbor * sell_to_neighbor_price + buy_from_neighbor * buy_from_neighbor_price
    cumulative_cost = np.cumsum(cost_half_hour)
    print("---------prosumer cost----------")
    print("buy_from_neighbor*buy_from_neighbor_price:", buy_from_neighbor*buy_from_neighbor_price)
    print("sell_to_neighbor*sell_to_neighbor_price:", sell_to_neighbor*sell_to_neighbor_price)
    print("buy_from_grid*buy_from_grid_price:", buy_from_grid*buy_from_grid_price)
    print("sell_to_grid*sell_to_grid_price:", sell_to_grid*sell_to_grid_price)
    print("cost_half_hour:", cost_half_hour)
    
    # Convert energy to power
    power_sell_to_grid = sell_to_grid / 0.5
    power_buy_from_grid = buy_from_grid / 0.5
    power_charge = charge / 0.5
    power_discharge = discharge / 0.5
    power_sell_to_neighbor = sell_to_neighbor / 0.5
    power_buy_from_neighbor = buy_from_neighbor / 0.5
    power_all_solar_gen_data = all_solar_gen_data[household_id] / 0.5
    power_all_consumption_data = all_consumption_data[household_id] / 0.5
    #开始正半轴
    axs[i, 0].bar(range(data_length), sell_to_grid, label='Sold to Grid', color='purple')
    axs[i, 0].bar(range(data_length), all_consumption_data[household_id], bottom= sell_to_grid, label='Consumption', color='red')
    axs[i, 0].bar(range(data_length), ev_value, bottom= sell_to_grid + all_consumption_data[household_id], label='EV Load', color='orange')
    axs[i, 0].bar(range(data_length), charge, bottom= sell_to_grid + all_consumption_data[household_id] + ev_value, label='Battery Charging', color='green')
    axs[i, 0].bar(range(data_length), sell_to_neighbor, bottom= sell_to_grid + all_consumption_data[household_id] + ev_value + charge, label='Sell to other neighbors', color='cyan')
    #开始负半轴
    axs[i, 0].bar(range(data_length), -all_solar_gen_data[household_id], label='Solar Generation', color='yellow')
    axs[i, 0].bar(range(data_length), -buy_from_grid, bottom= -all_solar_gen_data[household_id], label='Bought from Grid', color='brown')
    axs[i, 0].bar(range(data_length), -discharge, bottom= -all_solar_gen_data[household_id] - buy_from_grid, label='Battery Discharge', color='blue')
    axs[i, 0].bar(range(data_length), -buy_from_neighbor, bottom= -all_solar_gen_data[household_id] - buy_from_grid - discharge, label='Buy from other neighbors', color='pink')
    #设置标题和图例
    axs[i, 0].set_title(f'Household {household_id} Energy Distribution')

    #画出成本
    axs[i, 1].plot(cost_half_hour, label=f'Household Cost per Half Hour') #{household_id}
    axs[i, 1].plot(cumulative_cost, label=f'Household Cumulative Cost')
    axs[i, 1].set_title(f'Household {household_id} Cost')
axs[0, 0].legend(loc='upper left', bbox_to_anchor=(1, 1))
axs[0, 1].legend()
    
# Plot each consumer household's energy distribution and calculate costs 
for i, household_id in enumerate(consumer_household_config.keys(), start=len(prosumer_household_config)):
    sell_to_grid = np.where(trade_consumer_to_grid[household_id].value > 0, trade_consumer_to_grid[household_id].value, 0) # 其实consumer不会卖电，但还是写上吧
    buy_from_grid = np.where(trade_consumer_to_grid[household_id].value <= 0, -trade_consumer_to_grid[household_id].value, 0)
    ev_value = ev_load[household_id].value if household_id in ev_load else 0

    sell_to_neighbor = np.zeros(data_length)
    buy_from_neighbor = np.zeros(data_length)
    for p in prosumer_household_config.keys():
        sell_to_neighbor += np.where(-trade_prosumer_to_consumer[(p, household_id)].value > 0, -trade_prosumer_to_consumer[(p, household_id)].value, 0)
        buy_from_neighbor += np.where(-trade_prosumer_to_consumer[(p, household_id)].value <= 0, trade_prosumer_to_consumer[(p, household_id)].value, 0)
    sum_sell_to_neighbor = np.sum(sell_to_neighbor, axis=0)
    sum_buy_from_neighbor = np.sum(buy_from_neighbor, axis=0)
            
    cost_half_hour = buy_from_grid * buy_from_grid_price - sell_to_grid * sell_to_grid_price - sell_to_neighbor * sell_to_neighbor_price + buy_from_neighbor * buy_from_neighbor_price
    print("---------consumer cost----------")
    print("buy_from_neighbor*buy_from_neighbor_price:", buy_from_neighbor*buy_from_neighbor_price)
    print("sell_to_neighbor*sell_to_neighbor_price:", sell_to_neighbor*sell_to_neighbor_price)
    print("buy_from_grid*buy_from_grid_price:", buy_from_grid*buy_from_grid_price)
    print("sell_to_grid*sell_to_grid_price:", sell_to_grid*sell_to_grid_price)
    print("cost_half_hour:", cost_half_hour)

    cumulative_cost = np.cumsum(cost_half_hour)
    #开始正半轴
    axs[i, 0].bar(range(data_length), sell_to_grid, label='Sold to Grid', color='purple')
    axs[i, 0].bar(range(data_length), all_consumption_data[household_id], bottom= sell_to_grid, label='Consumption', color='red')
    axs[i, 0].bar(range(data_length), ev_value, bottom= sell_to_grid + all_consumption_data[household_id], label='EV Load', color='orange')    
    axs[i, 0].bar(range(data_length), sell_to_neighbor, bottom= sell_to_grid + all_consumption_data[household_id] + ev_value, label='Total Sold to Neighbor', color='cyan')
    #开始负半轴
    axs[i, 0].bar(range(data_length), -buy_from_grid, label='Bought from Grid', color='brown')
    axs[i, 0].bar(range(data_length), -buy_from_neighbor, bottom= -buy_from_grid, label='Total Bought from Neighbor', color='pink')
    #设置标题和图例
    axs[i, 0].set_title(f'Household {household_id} Energy Distribution')
    
    #画出成本
    axs[i, 1].plot(cost_half_hour, label=f'Household {household_id} Cost per Half Hour')
    axs[i, 1].plot(cumulative_cost, label=f'Household {household_id} Cumulative Cost')
    axs[i, 1].set_title(f'Household {household_id} Cost')
axs[len(prosumer_household_config), 0].legend(loc='upper left', bbox_to_anchor=(1, 1))
#axs[len(prosumer_household_config), 1].legend()   

# Plot neighbor trading prices
axs[len(prosumer_household_config) + len(consumer_household_config), 0].plot(sell_to_neighbor_price, label='Sell to Neighbor Price', color='green')
axs[len(prosumer_household_config) + len(consumer_household_config), 0].plot(buy_from_neighbor_price, label='Buy from Neighbor Price', color='red')
axs[len(prosumer_household_config) + len(consumer_household_config), 0].set_title('Neighbor Trading Prices')
axs[len(prosumer_household_config) + len(consumer_household_config), 0].legend()

# for p in prosumer_household_config.keys():
#     for c in consumer_household_config.keys():
#         axs[len(prosumer_household_config) + len(consumer_household_config), 1].plot(trade_prosumer_to_consumer[(p, c)].value, label=f'Prosumer {p} sell to Consumer {c}')
#         axs[len(prosumer_household_config) + len(consumer_household_config), 1].set_title('Prosumer to Consumer Trading')
#         axs[len(prosumer_household_config) + len(consumer_household_config), 1].legend(loc='upper right', bbox_to_anchor=(-0.05, 1))

axs[len(prosumer_household_config) + len(consumer_household_config), 1].plot(trade_prosumer_to_consumer[(p, c)].value, label=f'Prosumer {p} sell to Consumer {c}')
plt.xticks(np.arange(0, data_length, 2))
plt.show()
plt.tight_layout()

# Print the results
for household_id in prosumer_household_config.keys():
    print(f"Prosumer {household_id} EV Load:", ev_value)
    print(f"Prosumer {household_id} Battery Charge:", battery_charge[household_id].value if household_id in battery_charge else 0)
