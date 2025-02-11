import pandas as pd 
import numpy as np
import pyomo.environ as pyo
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import itertools

# 家庭资产配置表
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

    for t in range(1, total_time_steps + 1):  # 直接用 1 到 T 作为 key
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

def plot_results(T, start_date, end_date, Base_Load, total_load, Gen, import_energy, export_energy, 
                 battery_charge, battery_discharge, trades, m, import_price, 
                 export_price,  peer_buy_price, peer_sell_price, ev_soc, battery_soc, penalty):
    print("T is :", T)
    time_index = pd.date_range(start=start_date, end=end_date, freq="30min", inclusive="left")[:T]
    print(time_index[:10])
    households = list(Base_Load.keys())

    for h_index, h in enumerate(households):  # 每个 household 画一张图
        fig, axes = plt.subplots(3, 2, figsize=(15, 15), sharex=True)

        # **1. Base Load & EV Load**
        base_load_values = [float(Base_Load[h][t]) for t in range(1, T + 1)]
        ev_load_values = [float(pyo.value(m.ev_load[h_index + 1, t])) for t in range(1, T + 1)]
        total_load_values = [float(pyo.value(m.ev_load[h_index + 1, t])) + float(Base_Load[h][t])for t in range(1, T + 1)]
        
        axes[0, 0].plot(time_index, base_load_values, label="Base Load", linestyle="--", color="blue")
        axes[0, 0].fill_between(time_index, base_load_values, total_load_values, color="purple", alpha=0.6, label="EV Load")
        axes[0, 0].set_title(f"{h} - Base Load & EV Load (kWh)")
        axes[0, 0].legend()
        axes[0, 0].grid(True)

        # **2. Generation**
        if household_config[h]["solar"]:
            gen_values = [Gen[h][t] for t in range(1, T + 1)]
            axes[1, 0].plot(time_index, gen_values, label="Generation", color="orange")
        else:
            axes[1, 0].plot(time_index, [0] * T, label="No Generation", color="gray")
        axes[1, 0].set_title(f"{h} - Generation")
        axes[1, 0].legend()
        axes[1, 0].grid(True)

        # **3. Import, Export, Trading**
        import_values = [import_energy[h_index + 1][t] for t in range(1, T + 1)]
        export_values = [-export_energy[h_index + 1][t] for t in range(1, T + 1)]
        axes[2, 0].plot(time_index, import_values, label="Import Energy", alpha=0.5, color="red")
        axes[2, 0].plot(time_index, export_values, label="Export Energy", alpha=0.5, color="green")
        axes[2, 0].set_title(f"{h} - Import, Export Energy (kWh) ")
        axes[2, 0].legend()
        axes[2, 0].grid(True)

        # **4. Battery SOC & EV SOC**
        ev_soc_values = [ev_soc[h_index + 1][t] for t in range(1, T + 1)]
        battery_soc_values = [battery_soc[h_index + 1][t] for t in range(1, T + 1)]
        axes[0, 1].plot(time_index, ev_soc_values, label="EV SOC (%)", linestyle="-", color="blue")
        axes[0, 1].plot(time_index, battery_soc_values, label="Battery SOC (%)", linestyle=":", color="orange")
        axes[0, 1].set_title(f"{h} - Battery & EV SOC")
        axes[0, 1].legend()
        axes[0, 1].grid(True)

        axes[1, 1].plot(time_index, import_price, label="Electricity Price", color="blue", linewidth=2)
        axes[1, 1].plot(time_index, peer_buy_price, label="Peer Buy Price", linestyle=":", color="green")
        axes[1, 1].plot(time_index, peer_sell_price, label="Peer Sell Price", linestyle="-.", color="red")
        axes[1, 1].set_title(f"{h} - Price (£/kWh)")
        axes[1, 1].legend()
        axes[1, 1].grid(True)

        penalty_values = [penalty[h_index + 1][t] for t in range(1, T + 1)]
        axes[2, 1].plot(time_index, penalty_values, label="Penalty", color="blue", linewidth=2)
        if trades:
            for h2 in trades[h_index + 1]:
                trade_values = [trades[h_index + 1][h2][t] for t in range(1, T + 1)]
                axes[2, 1].plot(time_index, trade_values, label=f"Sold to {household_index_map[h2]}", linestyle=":")

            for h2 in trades:  # h2 卖给 h_index + 1
                if (h_index + 1) in trades[h2]:  
                    trade_values = -[trades[h2][h_index + 1][t] for t in range(1, T + 1)]
                    axes[2, 1].plot(time_index, trade_values, label=f"Bought from {household_index_map[h2]}", linestyle="--")

        axes[2, 1].set_title(f"{h} - Trading Energy (kWh) & Penalty (£)")
        axes[2, 1].legend()
        axes[2, 1].grid(True)
        
        # 格式化 X 轴
        for ax in axes.ravel():
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
            ax.tick_params(axis="x", rotation=75)

        plt.tight_layout()
        plt.show()

# 优化模型和绘图
def optimize_and_plot(time_step, start_date, end_date, Base_Load, Gen, battery_capacity, 
                      charge_power_limit, discharge_power_limit, ev_max_capacity, ev_initial_soc, daily_prices):
    """
    优化模型并绘制结果。
    """
    T = time_step #len(next(iter(Base_Load.values())))  # 时间步数
    H = len(Base_Load)  # 家庭数量
    time_step = 0.5  # 每个时间步的小时数
    penalty = 200
    global household_index_map
    households = list(Base_Load.keys())


    # 设置电池的上下限
    battery_soc_min = {h: 20 if battery_capacity[h] > 0 else 0 for h in battery_capacity}
    battery_soc_max = {h: 80 if battery_capacity[h] > 0 else 0 for h in battery_capacity}
    battery_soc_initial = {h: 40 if battery_capacity[h] > 0 else 0 for h in battery_capacity}

    # 创建家庭索引到 ID 的映射
    household_ids = list(Base_Load.keys())
    household_index_map = {i + 1: household_ids[i] for i in range(len(household_ids))}
    
    # 创建优化模型
    m = pyo.ConcreteModel()

    # 时间集和家庭集
    m.T = pyo.RangeSet(1, T)
    m.H = pyo.RangeSet(1, H)

    # 决策变量
    m.import_energy = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.export_energy = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.charge_battery = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (0, charge_power_limit[household_index_map[h]]))
    m.discharge_battery = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (0, discharge_power_limit[household_index_map[h]]))
    m.battery_soc = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (battery_soc_min[household_index_map[h]], battery_soc_max[household_index_map[h]]))
    m.ev_charge = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=(0, 7))  # EV 每小时充电速率最多 7kWh
    m.ev_load = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.ev_soc = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (0, 100) )
    m.trade = pyo.Var(m.H, m.H, m.T, domain=pyo.NonNegativeReals)

    # 约束
    m.constraints = pyo.ConstraintList()
    M = 1000  # 较大的常数用于启发式约束
    epsilon = 1e-6
    m.z_grid = pyo.Var(m.H, m.T, domain=pyo.Binary)  # 0-1 二进制变量
    m.z_battery = pyo.Var(m.H, m.T, domain=pyo.Binary)  # 0-1 二进制变量
    m.z_trade = pyo.Var(m.H, m.H, m.T, domain=pyo.Binary)  # 0-1 二进制变量
    

    # 添加约束
    for h in m.H:
        for t in m.T:
            # 电动汽车充电时间段的约束
            for d in range(len(ev_arrival)):
                if d == 0: 
                    # 第一天下午 arrival 到 00:00 不存在，允许 00:00 - departure 充电
                    if 1 <= t < ev_departure[d]:
                        m.constraints.add(m.ev_charge[h, t] <= 7)
                else:
                    # 从 arrival 到第二天 departure 允许充电
                    if ev_arrival[d - 1] <= t < ev_departure[d]:
                        m.constraints.add(m.ev_charge[h, t] <= 7)
                if ev_departure[d] <= t < ev_arrival[d]:
                    m.constraints.add(m.ev_charge[h, t] == 0)

            # EV 负载与充电关系
            m.constraints.add(m.ev_load[h, t] == m.ev_charge[h, t] * time_step)

            # 电池动态约束
            if t == 1:
                m.constraints.add(m.battery_soc[h, t] == battery_soc_initial[household_index_map[h]])
                m.constraints.add(m.ev_soc[h, t] == ev_initial_soc[household_index_map[h]])
            else:
                if battery_capacity[household_index_map[h]] > 0:
                    m.constraints.add(
                    m.battery_soc[h, t] == m.battery_soc[h, t - 1] + (( m.charge_battery[h, t] - m.discharge_battery[h, t] ) / battery_capacity[household_index_map[h]]) * 100
                )
                else:
                    m.constraints.add( m.battery_soc[h, t] == 0)
                
                if ev_max_capacity[household_index_map[h]] > 0:
                    if t in ev_arrival:
                        m.constraints.add(m.ev_soc[h, t] == 85)
                    else:
                        m.constraints.add(
                        m.ev_soc[h, t] == m.ev_soc[h, t - 1] + (m.ev_load[h, t] / ev_max_capacity[household_index_map[h]]) * 100
                        )
                else:
                    m.constraints.add(m.ev_soc[h, t] == 0)

            # 禁止家庭与自己交易
            m.constraints.add(m.trade[h, h, t] == 0) 

            # 约束：家庭间交易平衡 
            for h1, h2 in itertools.combinations(m.H, 2):  # 生成所有家庭对的组合
                m.constraints.add(m.trade[h1, h2, t] <= M * m.z_trade[h1, h2, t])
                m.constraints.add(m.trade[h2, h1, t] <= M * (1 - m.z_trade[h1, h2, t]))
      
            # 不能同时买卖电,充放电 if z[t]=1, M>buy>0, sell=0; if z[t]=0, M>sell>0, buy=0
            m.constraints.add(m.import_energy[h, t] <= M * m.z_grid[h, t])
            m.constraints.add(m.export_energy[h, t] <= M * (1 - m.z_grid[h, t]))
            m.constraints.add(m.charge_battery[h, t] <= M * m.z_battery[h, t])
            m.constraints.add(m.discharge_battery[h, t] <= M * (1 - m.z_battery[h, t]))

            # 能量平衡约束
            m.constraints.add(
                float(Base_Load[household_index_map[h]][t]) + m.ev_load[h, t] + m.charge_battery[h, t] +
                m.export_energy[h, t] + sum(m.trade[h, h2, t] for h2 in m.H if h2 != h) ==
                float(Gen[household_index_map[h]][t]) + m.discharge_battery[h, t] + m.import_energy[h, t] +
                sum(m.trade[h2, h, t] for h2 in m.H if h2 != h)
            )
    


    # 目标函数：最小化电费和负载转移成本
    m.cost = pyo.Objective(
        expr=sum(
            daily_prices[t]['import_price'] * m.import_energy[h, t] - daily_prices[t]['export_price'] * m.export_energy[h, t]
            for h in m.H for t in m.T 
        ) + sum(
            daily_prices[t]['peer_buy_price'] * m.trade[h2, h, t] - daily_prices[t]['peer_sell_price'] * m.trade[h, h2, t]
            for h in m.H for t in m.T for h2 in m.H if h2 != h
        )  + sum(
            penalty * (ev_max_capacity[household_index_map[h]] * ( 1 - m.ev_soc[h, T] )) 
            for h in m.H for t in ev_departure  # everyday 8:30
        ),
        sense=pyo.minimize
    )

    # 求解
    solver = pyo.SolverFactory('cbc')
    result = solver.solve(m, tee=True, timelimit=300)  # 设置时间限制为300秒
    if result.solver.termination_condition != pyo.TerminationCondition.optimal:
        print("Solver did not find an optimal solution.")
        
        print(f"Solver Status: {result.solver.status}")
        print(f"Termination Condition: {result.solver.termination_condition}")
        # 这里可以根据需求做进一步的处理，比如重新求解或者返回默认解
        return
    else: 
        print("Optimal solution found.")

    # 提取结果
    import_energy_h = {h: {t: m.import_energy[h, t].value for t in m.T} for h in m.H}
    export_energy_h = {h: {t: m.export_energy[h, t].value for t in m.T} for h in m.H}
    battery_charge_h = {h: {t: m.charge_battery[h, t].value for t in m.T} for h in m.H}
    battery_discharge_h = {h: {t: m.discharge_battery[h, t].value for t in m.T} for h in m.H}
    total_load = {h: {t: float(Base_Load[household_index_map[h]][t]) + m.ev_load[h, t].value for t in m.T} for h in m.H}
    trades = {
    h: {h2: {t: m.trade[h, h2, t].value for t in m.T} for h2 in m.H if h2 != h} for h in m.H
}
    penalty_h = {h: {t: penalty * (ev_max_capacity[household_index_map[h]] * ( 1 - m.ev_soc[h, T].value )) for t in m.T} for h in m.H}
    ev_soc_h = {h: {t: m.ev_soc[h, t].value for t in m.T} for h in m.H}
    battery_soc_h = {h: {t: m.battery_soc[h, t].value for t in m.T} for h in m.H}

    
    # 调用绘图函数
    plot_results(
        T, start_date, end_date, Base_Load, total_load, Gen, import_energy_h, export_energy_h,
        battery_charge_h, battery_discharge_h, trades, m, [daily_prices[t]['import_price'] for t in range(1, T + 1)],  
        [daily_prices[t]['export_price'] for t in range(1, T + 1)],
        [daily_prices[t]['peer_buy_price'] for t in range(1, T + 1)],  
        [daily_prices[t]['peer_sell_price'] for t in range(1, T + 1)],  ev_soc_h, battery_soc_h, penalty_h
    ) 

# 主函数
if __name__ == "__main__":
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
    total_steps, ev_arrival, ev_departure, daily_prices = calculate_total_time_steps_and_prices(
    start_date, end_date, time_step_minutes, steps_per_day, arrival_step, departure_step
)

    # 映射数据
    Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_capacity, ev_initial_soc = map_data_to_model(
        household_df, solar_half_hour, household_config, total_steps
    )

    # 打印检查数据
    print("Base_Load:", Base_Load)
    print("Gen:", Gen)
    print("Battery Capacity:", battery_capacity)
    print("EV Max capacity:", ev_max_capacity)

    # 优化与绘图
    optimize_and_plot(total_steps, start_date, end_date, Base_Load, Gen, battery_capacity, charge_power_limit, 
                      discharge_power_limit, ev_max_capacity, ev_initial_soc, daily_prices)
