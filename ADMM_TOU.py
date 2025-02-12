import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import cvxpy as cvx
from cvxpy import Minimize, Problem, Variable, norm, square
from datetime import datetime, timedelta
from multiprocessing import Pool

class HouseholdADMM_CVXPY:
    def __init__(self, total_time_steps, household_id, base_load, gen, battery_capacity, charge_power_limit, discharge_power_limit,
                 ev_max_capacity, ev_initial_soc, daily_prices, rho=0.1):
        self.T = total_time_steps #仿真的时间长度
        self.h = household_id #当前的家庭id
        self.base_load = base_load  # 家庭负载
        self.gen = gen  # 光伏发电
        self.battery_capacity = battery_capacity
        self.battery_soc_min = 20 if self.battery_capacity > 0 else 0
        self.battery_soc_max = 80 if self.battery_capacity > 0 else 0
        self.charge_power_limit = charge_power_limit
        self.discharge_power_limit = discharge_power_limit
        self.ev_max_capacity = ev_max_capacity
        self.ev_initial_soc = ev_initial_soc
        self.daily_prices = daily_prices
        self.penalty = 200
        self.time_step = 0.5
        self.rho = rho  # ADMM 罚因子

        self.H = len(self.base_load) #仿真的家庭数量
        # ADMM 变量
        # 卖出的电量 trade_out[h, h2, t]，存储家庭 h 在时间 t 向 h2 交易的电量
        self.trade_out = {(self.h, h2, t): 0.0 for h2 in households.keys() for t in range(self.T)}
        # 买入的电量 trade_in[h, h2, t]，存储家庭 h 在时间 t 从 h2 购买的电量
        self.trade_in = {(self.h, h2, t): 0.0 for h2 in households.keys() for t in range(self.T)}
        # 交易的拉格朗日乘子 lambda_trade[h, h2, t]，表示交易价格（对偶变量）
        self.lambda_trade = {(self.h, h2, t): 0.0 for h2 in households.keys() if h2 != self.h for t in range(self.T)}

    def solve_local_optimization(self):
        """
        解决本地 CVXPY 优化问题
        """
        M = 1000
        # **定义 CVXPY 变量**
        import_energy = cvx.Variable(self.T, nonneg=True)  # 从电网购电
        export_energy = cvx.Variable(self.T, nonneg=True)  # 向电网卖电
        battery_charge = cvx.Variable(self.T, nonneg=True)  # 电池充电
        battery_discharge = cvx.Variable(self.T, nonneg=True)  # 电池放电
        battery_soc = cvx.Variable(self.T, nonneg=True)  # 电池荷电状态
        ev_charge_power = cvx.Variable(self.T, nonneg=True)  # 电车充电速率
        ev_charge_load = cvx.Variable(self.T, nonneg=True)  # 电车充电能量
        ev_soc = cvx.Variable(self.T, nonneg=True)  # 电车荷电状态
        # 二进制变量（0 或 1）
        z_grid = cvx.Variable((self.H, self.T), boolean=True)        # 是否购电
        z_battery = cvx.Variable((self.H, self.T), boolean=True)     # 是否充电
        z_trade = {(self.h, h2, t): cvx.Variable(boolean=True)  
           for h2 in households.keys() for t in range(self.T)}    # 是否发生交易（家庭 h1 与 h2 在时间 t 交易）

        # 交易变量：家庭 h 在时间 t 向家庭 h2 交易的电量
        trade_out = {(self.h, h2, t): cvx.Variable(nonneg=True)  for h2 in households.keys() for t in range(self.T)}
        trade_in = {(self.h, h2, t): cvx.Variable(nonneg=True)  for h2 in households.keys() for t in range(self.T)}
        print("trade_in keys:", list(trade_in.keys()))
        # **目标函数：最小化购电成本**
        objective = cvx.Minimize(
            cvx.sum([import_energy[t] * cvx.Constant(self.daily_prices[t]['import_price']) for t in range(self.T)]) +
            cvx.sum([trade_in[(self.h, h2, t)] * self.lambda_trade for h2 in households.keys() for t in range(self.T)]) -  # 购买交易电的成本
            cvx.sum([export_energy[t] * cvx.Constant(self.daily_prices[t]['export_price']) for t in range(self.T)]) - 
            cvx.sum([trade_out[(self.h, h2, t)] * self.lambda_trade for h2 in households.keys() for t in range(self.T)]) +  # 卖电的收益
            cvx.sum([self.penalty * self.ev_max_capacity * (1 - ev_soc[t]) for t in range(self.T)])  # 确保常量部分使用 cvx.Constant
            )

        # **能量平衡约束**
        constraints = []
        for t in range(self.T):
            constraints.append(
                self.base_load[t] + battery_charge[t] + cvx.sum(trade_out[(self.h, h2, t)] for h2 in households.keys()) ==
                self.gen[t] + battery_discharge[t] + import_energy[t] + cvx.sum(trade_in[(self.h, h2, t)] for h2 in households.keys())
            )

        # **电池约束**
        constraints += [
            battery_charge <= self.charge_power_limit, 
            battery_discharge <= self.discharge_power_limit
        ]
        # **电动汽车充电约束**
        for t in range(self.T):
            for d in range(len(ev_arrival)):
                if d == 0: 
                    if 1 <= t < ev_departure[d]:
                        constraints.append(ev_charge_power[t] <= 7)  # 充电功率上限
                else:
                    if ev_arrival[d - 1] <= t < ev_departure[d]:
                        constraints.append(ev_charge_power[t] <= 7)
                if ev_departure[d] <= t < ev_arrival[d]:
                    constraints.append(ev_charge_power[t] == 0)  # 离开时间段不能充电

            # EV 负载与充电关系
            constraints.append(ev_charge_load[t] == ev_charge_power[t] * self.time_step)

        # **电池SOC和电车SOC动态约束**
        for t in range(1, self.T + 1):
            if t == 1:
                constraints.append(battery_soc[t] == self.battery_soc_min)
                constraints.append(ev_soc[t] == self.ev_initial_soc)
            else:
                if self.battery_capacity > 0:
                    constraints.append(
                        battery_soc[t] == battery_soc[t - 1] + (battery_charge[t] - battery_discharge[t]) / self.battery_capacity
                    )
                else:
                    constraints.append(battery_soc[t] == 0)
                
                if self.ev_max_capacity > 0:
                    constraints.append(
                        ev_soc[t] == ev_soc[t - 1] + ev_charge_load[t] / self.ev_max_capacity
                    )
                else:
                    constraints.append(ev_soc[t] == 0)

        # **禁止家庭与自己交易**
        for t in range(self.T):
            constraints.append(trade_out[self.h, self.h, t] == 0)

        # **家庭间交易平衡**
        for h2 in households.keys():
            for t in range(self.T):
                constraints.append(trade_out[(self.h, h2, t)] <= M * z_trade[self.h, h2, t])
                constraints.append(trade_in[(self.h, h2, t)] <= M * (1 - z_trade[self.h, h2, t]))

        # **不能同时买卖电，充放电**
        for t in range(self.T):
            constraints.append(import_energy[t] <= M * z_grid[h2, t])
            constraints.append(export_energy[t] <= M * (1 - z_grid[h2, t]))
            constraints.append(battery_charge[t] <= M * z_battery[h2, t])
            constraints.append(battery_discharge[t] <= M * (1 - z_battery[h2, t]))

        # **求解**
        problem = cvx.Problem(objective, constraints)
        problem.solve(solver=cvx.ECOS)

        # **更新 ADMM 变量**
        self.trade_out = {key: trade_out[key].value for key in trade_out}
        self.trade_in = {key: trade_in[key].value for key in trade_in}
        self.import_energy = import_energy.value

    def update_admm_variables(self, neighbor_trade):
        """
        用 ADMM 进行交易电量调整
        """
        for h2 in households.keys():  # 遍历所有可能的交易对手 h2
            if h2 == self.h:  
                continue  # 跳过自己和自己的交易
            
            for t in range(self.T):  # 遍历所有时间步
                # **ADMM 变量更新**
                # 取当前家庭 h 在时间 t 卖给 h2 的电量，与 h2 记录的交易电量取平均
                self.trade_out[(self.h, h2, t)] = (self.trade_out[(self.h, h2, t)] + neighbor_trade[(h2, self.h, t)]) / 2
                
                # **交易对等约束**
                # 家庭 h 在时间 t 向 h2 交易的电量，应该等于 h2 记录的交易电量
                self.trade_in[(self.h, h2, t)] = self.trade_out[(self.h, h2, t)]

                # **拉格朗日乘子（对偶变量）更新**
                self.lambda_trade[(self.h, h2, t)] += self.rho * (self.trade_out[(self.h, h2, t)] - neighbor_trade[(h2, self.h, t)])
def solve_optimization(h):
    h.solve_local_optimization()
    print(f"Household {h.h} results: trade_out={h.trade_out}, trade_in={h.trade_in}")
    return h.trade_out, h.trade_in, h.import_energy
    
def run_admm(households, num_iterations=20):
    with Pool(processes=10) as pool:  # 使用10个进程并行处理
        for i in range(num_iterations):
            # **1. 每个家庭独立优化**
            pool.map(solve_optimization, households.values())

            # **2. 交换交易信息**
            neighbor_trades = {h: { (h, h2, t): households[h].trade_out[(h, h2, t)] 
                                    for h2 in households.keys() if (h, h2, t) in households[h].trade_out
                                    for t in range(households[h].T) }
                               for h in households}

            # **3. ADMM 更新**
            def update_wrapper(h):
                return h.update_admm_variables(neighbor_trades[h])
            pool.map(update_wrapper, households.values())

            # **4. 计算收敛误差**
            max_gap = max(abs(households[h].trade_out[(h, h2, t)] - households[h2].trade_in[(h, h2, t)]) 
                          for h in households 
                          for h2 in households 
                          for t in range(households[h].T) 
                          if (h, h2, t) in households[h].trade_out and (h, h2, t) in households[h2].trade_in)
            print(f"Iteration {i+1}, Max Gap: {max_gap}")
            if max_gap < 1e-3:
                print("ADMM 收敛！")
                break

# 加载家庭负载数据
def load_household_data(file_path, household_ids, start_date, end_date):
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)

        # 检查必要的列是否存在
        required_columns = {'lclid', 'tstp', 'energykwhhh'}
        if not required_columns.issubset(set(df.columns)):
            raise ValueError(f"Missing required columns: {required_columns - set(df.columns)}")

        # 过滤特定家庭和时间范围
        df = df[df['lclid'].isin(household_ids)]
        df['tstp'] = pd.to_datetime(df['tstp'], errors='coerce')
        df = df[(df['tstp'] >= start_date) & (df['tstp'] <= end_date)]
        df = df.set_index('tstp')

        for h in household_ids:
            household_data = df[df['lclid'] == h]
            print(f"Household {h} data range:", household_data.index.min(), "->", household_data.index.max(), "Total:", len(household_data))

        return df
    except Exception as e:
        print(f"Error loading household data from {file_path}: {e}")
        return None

# 加载光伏发电数据
def load_solar_output_data(file_path, start_date, end_date):
    try:
        df = pd.read_csv(file_path, encoding='utf-8', skiprows=3)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)
        
        if 'time' not in df.columns:
            raise ValueError("Missing required 'time' column in the solar output data.")
        # 过滤时间范围
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        if df['time'].isnull().any():
            print("Warning: Some time values could not be converted to datetime.")
                    
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
        df = df.set_index('time')
        if df.empty:
            raise ValueError("No data available in the specified time range.")

        # 调整为每半小时间隔
        solar_half_hour = df.resample('30min').fillna(method='ffill')  # 使用整点值填充半小时数据
        print("Solar Data Time Steps:", len(solar_half_hour))
        print(solar_half_hour.index[:10])  # 打印前 10 个时间步
        print(solar_half_hour.index[-10:]) # 打印最后 10 个时间步
        return solar_half_hour
    except Exception as e:
        print(f"Error loading solar output data from {file_path}: {e}")
        return None


def calculate_total_time_steps_and_prices(
    start_date, end_date, time_step_minutes=30, steps_per_day=48, arrival_step=38, departure_step=18
):
    # 计算日期范围
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    num_days = (end - start).days

    # 计算总时间步数
    total_time_steps = num_days * steps_per_day  # 例如 3 天就是 3 * 48 = 144 个时间步

    # 初始化字典存储价格
    daily_prices = {}

    # 生成 EV 的到达和离开时间步
    ev_arrival = [arrival_step + i * steps_per_day for i in range(num_days)]
    ev_departure = [departure_step + i * steps_per_day for i in range(num_days)]

    for t in range(0, total_time_steps):  # 直接用 0 到 T 作为 key
        # 计算当前时间
        current_time = start + timedelta(minutes=(t - 1) * time_step_minutes)

        # 价格计算逻辑
        if (11 * 60 <= current_time.hour * 60 + current_time.minute < 13 * 60) or \
           (17 * 60 <= current_time.hour * 60 + current_time.minute < 20 * 60):
            import_price = 0.5
        else:
            import_price = 0.1

        # 计算其他价格
        peer_buy_price = 0.8 * import_price
        peer_sell_price = 0.7 * import_price
        export_price = 0.4 * import_price

        # 将每个时间步的价格存储到字典中
        daily_prices[t] = {
            'import_price': import_price,
             'peer_buy_price': peer_buy_price,
             'peer_sell_price': peer_sell_price,
             'export_price': export_price
           }
    print("daily_prices keys:", list(daily_prices.keys())[:10])  # 只打印前10个键看看是否从 1 开始
    print("daily_prices Range:", min(daily_prices.keys()), "->", max(daily_prices.keys()))
    print("total_time_steps:", total_time_steps)
    return total_time_steps, ev_arrival, ev_departure, daily_prices


# 数据映射到模型, T is from calculate_total_time_steps
def map_data_to_model(household_df, solar_half_hour, config, T):
    households = config.keys()
    Base_Load = {h: {} for h in households}
    Gen = {h: {} for h in households}
    battery_capacity = {}
    charge_power_limit = {}
    discharge_power_limit = {}
    ev_max_capacity = {}
    ev_initial_soc = {}

    for household in households:
        # 获取该家庭的数据
        household_data = household_df[household_df['lclid'] == household].copy()

        # Ensure energykwhhh column contains valid numeric data
        household_data["energykwhhh"] = pd.to_numeric(household_data["energykwhhh"], errors="coerce")
        household_data = household_data.dropna(subset=["energykwhhh"])
        household_data = household_data.set_index(household_data.index)  # Ensure proper index
        household_half_hour = household_data['energykwhhh'].resample('30min').sum().asfreq("30min")

        # 配置 Base_Load
        for t, energy in enumerate(household_half_hour.values[:T], start=1):
            Base_Load[household][t] = energy if config[household]["demand"] else 0

        # 配置发电量
        if config[household]["solar"]:
            for t, gen in enumerate(solar_half_hour['electricity'].values[:T], start=1):
                Gen[household][t] = gen
        else:
            for t in range(1, T + 1):
                Gen[household][t] = 0

        # 配置电池
        if config[household]["battery"]:
            battery_capacity[household] = 5
            charge_power_limit[household] = 1
            discharge_power_limit[household] = 1
        else:
            battery_capacity[household] = 0
            charge_power_limit[household] = 0
            discharge_power_limit[household] = 0

        # 配置电动车
        if config[household]["ev"]:
            ev_max_capacity[household] = 75 # Tesla Model Y about 75 kWh
            ev_initial_soc[household] = 85  # Assume coming back home with 85%
        else:
            ev_max_capacity[household] = 0
            ev_initial_soc[household] = 0
    print("Household Data Time Range:", household_df.index.min(), "->", household_df.index.max())
    print("Solar Data Time Range:", solar_half_hour.index.min(), "->", solar_half_hour.index.max())


    return Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_capacity, ev_initial_soc


if __name__ == "__main__":
    household_config = {
    "MAC003252": {"solar": True, "battery": True, "ev": False, "demand": True},
    "MAC003305": {"solar": True, "battery": False, "ev": False, "demand": True},
    "MAC003394": {"solar": True, "battery": True, "ev": True, "demand": True},
    "MAC003428": {"solar": True, "battery": True, "ev": True, "demand": True},
    "MAC003863": {"solar": True, "battery": True, "ev": False, "demand": True},
    "MAC003223": {"solar": False, "battery": False, "ev": True, "demand": True},
    "MAC003281": {"solar": False, "battery": False, "ev": True, "demand": True},
    "MAC003348": {"solar": False, "battery": False, "ev": False, "demand": True},
    "MAC003553": {"solar": False, "battery": False, "ev": False, "demand": True},
    "MAC003874": {"solar": False, "battery": False, "ev": False, "demand": True},
    }
    # 家庭 ID 列表
    household_ids = list(household_config.keys())

    # 文件路径
    household_file = "/home/pi/block_0.csv"
    solar_file = "/home/pi/SolarOutput.csv"

    start_date = "2013-06-01"
    end_date = "2013-06-04"
    gen_start_date = "2019-06-01"
    gen_end_date = "2019-06-04"
    time_step_minutes = 30  # 每个时间步 30 分钟
    steps_per_day = 48      # 每天 48 个时间步
    arrival_step = 38       # 每天的到达时间步（18:30）
    departure_step = 18     # 每天的离开时间步（8:30）

    # 加载数据
    household_df = load_household_data(household_file, household_ids, start_date, end_date)
    solar_half_hour = load_solar_output_data(solar_file, gen_start_date, gen_end_date)


    # 调用函数
    total_time_steps, ev_arrival, ev_departure, daily_prices = calculate_total_time_steps_and_prices(
    start_date, end_date, time_step_minutes, steps_per_day, arrival_step, departure_step
    )

    # 映射数据
    Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_capacity, ev_initial_soc = map_data_to_model(
        household_df, solar_half_hour, household_config, total_time_steps
    )

    # 创建所有家庭的 ADMM 实例
    households = {}
    for h in household_config.keys():
        households[h] = HouseholdADMM_CVXPY(
            total_time_steps, h, Base_Load[h], Gen[h], battery_capacity[h], charge_power_limit[h], discharge_power_limit[h], ev_max_capacity, 
            ev_initial_soc, daily_prices
        )

    run_admm(households)


