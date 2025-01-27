import pandas as pd
import numpy as np
import pyomo.environ as pyo
import matplotlib.pyplot as plt
from datetime import datetime

# 家庭资产配置表
household_config = {
    "MAC003252": {"solar": True, "battery": True, "ev": False, "demand": True},
    "MAC003305": {"solar": True, "battery": False, "ev": False, "demand": True},
    "MAC003394": {"solar": True, "battery": True, "ev": True, "demand": True},
    "MAC003428": {"solar": True, "battery": True, "ev": True, "demand": True},
    "MAC003863": {"solar": True, "battery": True, "ev": False, "demand": True},
    "MAC000450": {"solar": False, "battery": False, "ev": True, "demand": True},
    "MAC003281": {"solar": False, "battery": False, "ev": True, "demand": True},
    "MAC003348": {"solar": False, "battery": False, "ev": False, "demand": True},
    "MAC003553": {"solar": False, "battery": False, "ev": False, "demand": True},
    "MAC003874": {"solar": False, "battery": False, "ev": False, "demand": True},
}

# 时间范围设置
load_start_date = "2013-06-01"
load_end_date = "2013-06-05"
gen_start_date = "2019-06-01"
gen_end_date = "2019-06-05"

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
        return df
    except Exception as e:
        print(f"Error loading household data from {file_path}: {e}")
        return None

# 加载光伏发电数据
def load_solar_output_data(file_path, start_date, end_date):
    try:
        df = pd.read_csv(file_path, encoding='utf-8', skiprows=3)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)

        # 过滤时间范围
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
        df = df.set_index('time')

        # 调整为每半小时间隔
        solar_half_hour = df.resample('30min').pad()  # 使用整点值填充半小时数据
        return solar_half_hour
    except Exception as e:
        print(f"Error loading solar output data from {file_path}: {e}")
        return None


# 动态计算时间步数函数
def calculate_total_time_steps_and_ev_schedule(
    start_date, end_date, time_step_minutes=30, steps_per_day=48, arrival_step=38, departure_step=18
):
    # 计算总时间步数
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    num_days = (end - start).days + 1  # 包含结束日期
    total_time_steps = (num_days * 24 * 60) // time_step_minutes  # 总时间步数

    # 生成 EV 的到达和离开时间步
    ev_arrival = [arrival_step + i * steps_per_day for i in range(num_days)]
    ev_departure = [departure_step + i * steps_per_day for i in range(num_days)]

    return total_time_steps, ev_arrival, ev_departure


# 数据映射到模型, T is from calculate_total_time_steps
def map_data_to_model(household_df, solar_half_hour, config, T):
    households = config.keys()
    Base_Load = {h: {} for h in households}
    Gen = {h: {} for h in households}
    battery_capacity = {}
    charge_power_limit = {}
    discharge_power_limit = {}
    ev_max_soc = {}
    ev_initial_soc = {}

    for household in households:
        # 获取该家庭的数据
        household_data = household_df[household_df['lclid'] == household]
        household_half_hour = household_data['energykwhhh'].resample('30min').sum()

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
            ev_max_soc[household] = 5
            ev_initial_soc[household] = 2.5  # 假设初始电量为 50%
        else:
            ev_max_soc[household] = 0
            ev_initial_soc[household] = 0

    return Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_soc, ev_initial_soc

# 绘图函数
def plot_results(T, Base_Load, total_load,  Gen, import_energy, export_energy, 
battery_charge, battery_discharge, trades, m, price, export_price, peer_buy_price, peer_sell_price, 
net_energy, cost_h, cost_penalty_h1):
    time = list(range(1, T + 1))

    fig, axes = plt.subplots(len(Base_Load) + 2, 1,  sharex=True)
    

    for h, ax in enumerate(axes[:-2], start=1):
        # 确保 Base_Load 和 total_load 是数值类型
        base_load_values = [float(Base_Load[h][t]) for t in time]
        total_load_values = [float(pyo.value(m.ev_load[h, t])) + float(Base_Load[h][t]) for t in time]  # 使用 pyo.value() 获取 ev_load 的值
        ev_load_values = [float(pyo.value(m.ev_load[h, t])) for t in time]
        ev_soc_values = [float(pyo.value(m.ev_soc[h, t])) for t in time]
        soc_values = [float(pyo.value(m.soc[h, t])) for t in time]

        ax.plot(time, [Base_Load[h][t] for t in time], label=f"Base Load {h}", linestyle="--")
        ax.fill_between(time, base_load_values, total_load_values, color="purple", alpha=0.6, label="EV Load (Added)")
        ax.plot(time, ev_load_values, label="EV Load", linestyle="-.", color="black")
        ax.plot(time, ev_soc_values, label="EV SOC", linestyle="-", color="green")
        ax.plot(time, soc_values, label="Battery SOC", linestyle=":", color="blue")

        # 如果家庭有太阳能生产，则绘制太阳能生产
        if h != 2:
            ax.plot(time, [Gen[h][t] for t in time], label=f"Generation {h}", color="orange")

        # 绘制电网买卖电量
        ax.bar(time, [import_energy[h][t] for t in time], label="Import Energy", alpha=0.5)
        ax.bar(time, [-export_energy[h][t] for t in time], label="Export Energy", alpha=0.5)

        # 绘制电池充放电
        ax.bar(time, [battery_charge[h][t] for t in time], label=f"Battery Charge {h}", alpha=0.3)
        ax.bar(time, [-battery_discharge[h][t] for t in time], label=f"Battery Discharge {h}", alpha=0.3)
        
        # 绘制家庭间交易量
        if trades:
            for h2 in trades[h]:
                ax.plot(time, [trades[h][h2][t] for t in time], label=f"Trade with {h2} (to H{h})")

        ax.set_title(f"Household {h} Power Flow")
        time_labels = [f"{hour:02}:{minute:02}" for hour in range(24) for minute in [0, 30]]
        plt.xticks(ticks=range(1, T + 1), labels=time_labels, rotation=45, fontsize=8)
        ax.legend(bbox_to_anchor=(1.1, 1), loc="upper right", fontsize=7)
        plt.grid(True)

    # 绘制价格比较图
    ax = axes[-2]
    time = np.array(range(1, T + 1))  
    price_values = [price[t] for t in range(1, T + 1)]
    export_price_values = [export_price[t] for t in range(1, T + 1)]
    peer_buy_price_values = [peer_buy_price[t] for t in range(1, T + 1)]
    peer_sell_price_values = [peer_sell_price[t] for t in range(1, T + 1)]

    ax.plot(time, price_values, label="Electricity Price (Buy)", color="blue", linewidth=2)
    ax.plot(time, export_price_values, label="Export Price (Sell to Grid)", color="orange", linestyle="--")
    ax.plot(time, peer_buy_price_values, label="Peer Buy Price", color="green", linestyle=":")
    ax.plot(time, peer_sell_price_values, label="Peer Sell Price", color="red", linestyle="-.")
    #ax.plot(time, [Gen[1][t] for t in time], label=f"Generation {h}", color="orange")
    ax.set_title("Price Comparison")
    ax.legend(bbox_to_anchor=(1.1, 1), loc="upper right", fontsize=7)
    plt.grid(True)

    # 绘制社区总净能量和成本图
    ax = axes[-1]
    ax.plot(time, [net_energy[t] for t in time], label="Net Energy", color="purple", linestyle="--")
    for h in range(1, len(cost_h) + 1):  # 假设 cost_h 的键是家庭的索引 (1, 2, ...)
        ax.plot(time, cost_h[h], label=f"Household {h} Cost", color=f"C{h+1}")  # 使用 f-string 动态生成标签和颜色

    ax.plot(time, cost_penalty_h1, label="Household 1 Penalty", color="red", linestyle=":")
    ax.set_title("Community Net Energy and Cost Analysis")
    ax.legend(bbox_to_anchor=(1.1, 1), loc="upper right", fontsize=7)
    plt.grid(True)
    
    plt.show()

# 优化模型和绘图
def optimize_and_plot(Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_soc, ev_initial_soc):
    """
    优化模型并绘制结果。
    """
    T = len(next(iter(Base_Load.values())))  # 时间步数
    H = len(Base_Load)  # 家庭数量
    time_step = 0.5  # 每个时间步的小时数
    penalty = 2000

    # 设置价格
    price = {t: 10 if (11 * 2 <= t < 13 * 2) or (17 * 2 <= t < 20 * 2) else 5 for t in range(1, T + 1)}
    peer_buy_price = {t: 0.8 * price[t] for t in price}
    peer_sell_price = {t: 0.7 * price[t] for t in price}
    export_price = {t: 0 * price[t] for t in price}

    # 设置电池的上下限
    soc_min = {h: 0.2 * battery_capacity[h] for h in battery_capacity}
    soc_max = {h: 0.8 * battery_capacity[h] for h in battery_capacity}

    # 创建优化模型
    m = pyo.ConcreteModel()

    # 时间集和家庭集
    m.T = pyo.RangeSet(1, T)
    m.H = pyo.RangeSet(1, H)

    # 决策变量
    m.import_energy = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.export_energy = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.charge_battery = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (0, charge_power_limit[h]))
    m.discharge_battery = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (0, discharge_power_limit[h]))
    m.soc = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=lambda m, h, t: (soc_min[h], soc_max[h]))
    m.ev_charge = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals, bounds=(0, 1))  # EV 每小时充电速率最多 1kWh
    m.ev_load = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.ev_soc = pyo.Var(m.H, m.T, domain=pyo.NonNegativeReals)
    m.trade = pyo.Var(m.H, m.H, m.T, domain=pyo.NonNegativeReals)

    # 目标函数：最小化电费和负载转移成本
    m.cost = pyo.Objective(
        expr=sum(
            price[t] * m.import_energy[h, t] - export_price[t] * m.export_energy[h, t]
            for h in m.H for t in m.T
        ) + sum(
            peer_buy_price[t] * m.trade[h2, h, t] - peer_sell_price[t] * m.trade[h, h2, t]
            for h in m.H for t in m.T for h2 in m.H if h2 != h
        ) + sum(
            penalty * (ev_max_soc[h] - m.ev_soc[h, T]) for h in m.H
        ),
        sense=pyo.minimize
    )

    # 约束
    m.constraints = pyo.ConstraintList()
    M = 1000  # 较大的常数用于启发式约束

    # 添加约束
    for t in m.T:
        for h in m.H:
            # 电动汽车充电约束
            if t in ev_arrival:
                m.constraints.add(m.ev_charge[h, t] <= 5)
            elif t in ev_departure:
                m.constraints.add(m.ev_charge[h, t] == 0)

            # EV 负载与充电关系
            m.constraints.add(m.ev_load[h, t] == m.ev_charge[h, t] * time_step)

            # 电池动态约束
            if t == 1:
                m.constraints.add(m.soc[h, t] == soc_min[h])
                m.constraints.add(m.ev_soc[h, t] == ev_initial_soc[h])
            else:
                m.constraints.add(
                    m.soc[h, t] == m.soc[h, t - 1] + m.charge_battery[h, t] - m.discharge_battery[h, t]
                )
                m.constraints.add(
                    m.ev_soc[h, t] == m.ev_soc[h, t - 1] + m.ev_load[h, t]
                )

            # 禁止家庭与自己交易
            m.constraints.add(m.trade[h, h, t] == 0) 

            # 能量平衡约束
            m.constraints.add(
                Base_Load[h][t] + m.ev_load[h, t] + m.charge_battery[h, t] +
                m.export_energy[h, t] + sum(m.trade[h, h2, t] for h2 in m.H if h2 != h) ==
                Gen[h][t] + m.discharge_battery[h, t] + m.import_energy[h, t] +
                sum(m.trade[h2, h, t] for h2 in m.H if h2 != h)
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
    total_load = {h: {t: Base_Load[h][t] + m.ev_load[h, t].value for t in m.T} for h in m.H}
    trades = {
    h: {h2: {t: m.trade[h, h2, t].value for t in m.T} for h2 in m.H if h2 != h} for h in m.H
}
    
    # 调用绘图函数
    plot_results(
        T, Base_Load, total_load, Gen, import_energy_h, export_energy_h,
        battery_charge_h, battery_discharge_h, trades, m, price, export_price,
        peer_buy_price, peer_sell_price, None, None, None
    )

# 主函数
if __name__ == "__main__":
    # 家庭 ID 列表
    household_ids = list(household_config.keys())

    # 文件路径
    household_file = "/home/pi/block_0.csv"
    solar_file = "/home/pi/SolarOutput.csv"

    start_date = "2013-06-01"
    end_date = "2013-06-03"
    gen_start_date = "2019-06-01"
    gen_end_date = "2019-06-03"
    time_step_minutes = 30  # 每个时间步 30 分钟
    steps_per_day = 48      # 每天 48 个时间步
    arrival_step = 38       # 每天的到达时间步（18:30）
    departure_step = 18     # 每天的离开时间步（8:30）

    # 加载数据
    household_df = load_household_data(household_file, household_ids, start_date, end_date)
    solar_half_hour = load_solar_output_data(solar_file, gen_start_date, gen_end_date)


    # 调用函数
    total_steps, ev_arrival, ev_departure = calculate_total_time_steps_and_ev_schedule(
        start_date, end_date, time_step_minutes, steps_per_day, arrival_step, departure_step
    )

    # 映射数据
    Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_soc, ev_initial_soc = map_data_to_model(
        household_df, solar_half_hour, household_config, total_steps
    )

    # 打印检查数据
    print("Base_Load:", Base_Load)
    print("Gen:", Gen)
    print("Battery Capacity:", battery_capacity)
    print("EV Max SOC:", ev_max_soc)

    # 优化与绘图
    optimize_and_plot(Base_Load, Gen, battery_capacity, charge_power_limit, discharge_power_limit, ev_max_soc, ev_initial_soc)
